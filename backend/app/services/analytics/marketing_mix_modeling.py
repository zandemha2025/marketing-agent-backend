"""
Marketing Mix Modeling Service.

Implements Marketing Mix Modeling (MMM) with adstock and saturation effects
to measure the impact of marketing activities on business outcomes.

Uses statistical modeling techniques including:
- Ridge regression for regularization
- Adstock transformation for carryover effects
- Hill saturation for diminishing returns
- Time-series decomposition for seasonality/trend
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date, timedelta
import json

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_percentage_error
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from ...models.marketing_mix_model import (
    MarketingMixModel, MMMChannel, MMMChannelDaily, MMMPrediction,
    MMMBudgetOptimizer, MMMModelStatus, MMMChannelType
)

logger = logging.getLogger(__name__)


@dataclass
class MMMTrainingResult:
    """Result of MMM training."""
    model_id: str
    r_squared: float
    adjusted_r_squared: float
    mape: float
    rmse: float
    coefficients: Dict[str, Any]
    feature_importance: Dict[str, float]


class MarketingMixModelingService:
    """
    Marketing Mix Modeling Service.

    Provides capabilities for:
    - Training MMM models with adstock and saturation
    - Making predictions and forecasts
    - Optimizing budget allocation
    - Analyzing channel effectiveness
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the MMM Service.

        Args:
            db: SQLAlchemy async session for database operations.
        """
        self.db = db

    # ============== Adstock and Saturation Transformations ==============

    def apply_adstock(
        self,
        spend: np.ndarray,
        decay: float,
        peak_delay: int = 0
    ) -> np.ndarray:
        """
        Apply adstock transformation to spend data.

        Adstock models the carryover effect of advertising where
        the impact of spend persists over time.

        Args:
            spend: Array of spend values.
            decay: Decay rate (0-1), higher = longer carryover.
            peak_delay: Days to peak effect (0 = immediate).

        Returns:
            Adstocked spend array.
        """
        adstocked = np.zeros_like(spend)

        for i in range(len(spend)):
            if i == 0:
                adstocked[i] = spend[i]
            else:
                # Geometric decay with optional peak delay
                if peak_delay == 0:
                    adstocked[i] = spend[i] + decay * adstocked[i - 1]
                else:
                    # Delayed peak using gamma-like distribution
                    adstocked[i] = spend[i]
                    for j in range(1, min(peak_delay + 1, i + 1)):
                        weight = ((j / peak_delay) ** peak_delay) * np.exp(peak_delay - j)
                        adstocked[i] += decay * weight * spend[i - j]

        return adstocked

    def apply_saturation(
        self,
        adstocked_spend: np.ndarray,
        shape: str = "hill",
        k: float = 2.0,
        half_spend: float = None
    ) -> np.ndarray:
        """
        Apply saturation transformation.

        Models diminishing returns where additional spend has
        decreasing marginal impact.

        Args:
            adstocked_spend: Array of adstocked spend values.
            shape: Saturation curve shape ("hill", "logistic", "linear").
            k: Shape parameter for Hill function.
            half_spend: Spend level at 50% saturation.

        Returns:
            Saturated spend array.
        """
        if half_spend is None:
            half_spend = np.median(adstocked_spend) if len(adstocked_spend) > 0 else 1.0

        if shape == "hill":
            # Hill function: S = x^k / (x^k + half^k)
            return adstocked_spend ** k / (adstocked_spend ** k + half_spend ** k)

        elif shape == "logistic":
            # Logistic function
            return 1 / (1 + np.exp(-k * (adstocked_spend - half_spend) / half_spend))

        elif shape == "linear":
            # Linear with ceiling
            return np.minimum(adstocked_spend / (adstocked_spend + half_spend), 1.0)

        else:
            # Default to Hill
            return adstocked_spend ** k / (adstocked_spend ** k + half_spend ** k)

    def transform_features(
        self,
        df: pd.DataFrame,
        channel_cols: List[str],
        adstock_params: Dict[str, Dict[str, float]],
        saturation_params: Dict[str, Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Apply adstock and saturation transformations to all channels.

        Args:
            df: DataFrame with raw spend data.
            channel_cols: List of channel column names.
            adstock_params: Adstock parameters per channel.
            saturation_params: Saturation parameters per channel.

        Returns:
            DataFrame with transformed features.
        """
        df_transformed = df.copy()

        for channel in channel_cols:
            if channel not in df.columns:
                continue

            # Get parameters
            adstock = adstock_params.get(channel, {})
            saturation = saturation_params.get(channel, {})

            decay = adstock.get("decay", 0.3)
            peak_delay = adstock.get("peak_delay", 0)

            shape = saturation.get("shape", "hill")
            k = saturation.get("k", 2.0)
            half_spend = saturation.get("half_spend", None)

            # Apply transformations
            spend = df[channel].values
            adstocked = self.apply_adstock(spend, decay, peak_delay)
            saturated = self.apply_saturation(adstocked, shape, k, half_spend)

            df_transformed[f"{channel}_adstocked"] = adstocked
            df_transformed[f"{channel}_saturated"] = saturated

        return df_transformed

    # ============== Model Training ==============

    async def train_model(
        self,
        model_id: str,
        training_data: pd.DataFrame = None
    ) -> MMMTrainingResult:
        """
        Train a Marketing Mix Model.

        Args:
            model_id: ID of the model to train.
            training_data: Optional pre-loaded training data.

        Returns:
            Training result with metrics and coefficients.
        """
        # Load model
        query = select(MarketingMixModel).where(MarketingMixModel.id == model_id)
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"Model {model_id} not found")

        model.status = MMMModelStatus.TRAINING
        await self.db.commit()

        try:
            start_time = datetime.utcnow()

            # Load or prepare training data
            if training_data is None:
                df = await self._load_training_data(model)
            else:
                df = training_data

            # Get channel columns
            channel_cols = [ch.channel_name for ch in model.channels]

            # Apply transformations
            df_transformed = self.transform_features(
                df,
                channel_cols,
                model.adstock_params,
                model.saturation_params
            )

            # Prepare features
            feature_cols = [f"{ch}_saturated" for ch in channel_cols]

            # Add control variables
            if model.model_config.get("include_seasonality", True):
                df_transformed["seasonality"] = self._calculate_seasonality(df_transformed)
                feature_cols.append("seasonality")

            if model.model_config.get("include_trend", True):
                df_transformed["trend"] = np.arange(len(df_transformed))
                feature_cols.append("trend")

            # Prepare X and y
            X = df_transformed[feature_cols].fillna(0)
            y = df_transformed[model.target_variable].values

            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Train Ridge regression
            alpha = model.model_config.get("regularization", 1.0)
            ridge = Ridge(alpha=alpha, fit_intercept=True)
            ridge.fit(X_scaled, y)

            # Predictions
            y_pred = ridge.predict(X_scaled)

            # Calculate metrics
            r2 = r2_score(y, y_pred)
            n = len(y)
            p = len(feature_cols)
            adjusted_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1)
            mape = mean_absolute_percentage_error(y, y_pred)
            rmse = np.sqrt(np.mean((y - y_pred) ** 2))
            mae = np.mean(np.abs(y - y_pred))

            # Calculate feature importance
            importance = np.abs(ridge.coef_)
            importance = importance / importance.sum()
            feature_importance = dict(zip(feature_cols, importance.tolist()))

            # Calculate channel contributions
            contributions = self._calculate_contributions(
                X_scaled, ridge.coef_, ridge.intercept_, y
            )

            # Calculate ROIs
            channel_rois = await self._calculate_channel_rois(
                model, df, contributions, channel_cols
            )

            # Update model
            model.performance_metrics = {
                "r_squared": float(r2),
                "adjusted_r_squared": float(adjusted_r2),
                "mape": float(mape),
                "rmse": float(rmse),
                "mae": float(mae),
            }

            model.model_coefficients = {
                "intercept": float(ridge.intercept_),
                "channels": channel_rois,
                "control_variables": {
                    col: {"coefficient": float(coef)}
                    for col, coef in zip(feature_cols[len(channel_cols):], ridge.coef_[len(channel_cols):])
                }
            }

            model.feature_importance = feature_importance
            model.status = MMMModelStatus.TRAINED
            model.trained_at = datetime.utcnow()
            model.training_duration_seconds = int(
                (datetime.utcnow() - start_time).total_seconds()
            )

            await self.db.commit()

            return MMMTrainingResult(
                model_id=model_id,
                r_squared=float(r2),
                adjusted_r_squared=float(adjusted_r2),
                mape=float(mape),
                rmse=float(rmse),
                coefficients=model.model_coefficients,
                feature_importance=feature_importance
            )

        except Exception as e:
            logger.error(f"Error training model {model_id}: {e}")
            model.status = MMMModelStatus.ERROR
            await self.db.commit()
            raise

    async def _load_training_data(
        self,
        model: MarketingMixModel
    ) -> pd.DataFrame:
        """Load training data from database."""
        # Query daily data for all channels
        query = select(MMMChannelDaily).where(
            MMMChannelDaily.model_id == model.id
        ).order_by(MMMChannelDaily.date)

        result = await self.db.execute(query)
        daily_data = result.scalars().all()

        if not daily_data:
            raise ValueError(f"No training data found for model {model.id}")

        # Convert to DataFrame
        df = pd.DataFrame([d.to_dict() for d in daily_data])
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        return df

    def _calculate_seasonality(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate seasonality features."""
        if "date" not in df.columns:
            return np.zeros(len(df))

        dates = pd.to_datetime(df["date"])
        day_of_year = dates.dt.dayofyear

        # Sine and cosine for yearly seasonality
        seasonality = np.sin(2 * np.pi * day_of_year / 365.25)
        return seasonality

    def _calculate_contributions(
        self,
        X: np.ndarray,
        coefficients: np.ndarray,
        intercept: float,
        y: np.ndarray
    ) -> Dict[str, float]:
        """Calculate contribution of each feature."""
        contributions = {}
        total_pred = np.full_like(y, intercept)

        for i, coef in enumerate(coefficients):
            feature_contribution = X[:, i] * coef
            contributions[f"feature_{i}"] = np.sum(feature_contribution)
            total_pred += feature_contribution

        # Normalize to percentages
        total = np.sum(list(contributions.values())) + intercept * len(y)
        for key in contributions:
            contributions[key] = contributions[key] / total if total > 0 else 0

        return contributions

    async def _calculate_channel_rois(
        self,
        model: MarketingMixModel,
        df: pd.DataFrame,
        contributions: Dict[str, float],
        channel_cols: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate ROI for each channel."""
        channel_rois = {}

        for i, channel in enumerate(channel_cols):
            if channel not in df.columns:
                continue

            total_spend = df[channel].sum()
            attributed_revenue = contributions.get(f"feature_{i}", 0) * df[model.target_variable].sum()

            roi = (attributed_revenue - total_spend) / total_spend if total_spend > 0 else 0

            channel_rois[channel] = {
                "coefficient": float(model.model_coefficients.get("channels", {}).get(channel, {}).get("coefficient", 0)),
                "roi": float(roi),
                "mroi": float(roi),  # Simplified, should calculate marginal
                "contribution_pct": float(contributions.get(f"feature_{i}", 0))
            }

        return channel_rois

    # ============== Prediction ==============

    async def predict(
        self,
        model_id: str,
        future_spend: pd.DataFrame,
        start_date: date,
        end_date: date
    ) -> MMMPrediction:
        """
        Make predictions using a trained MMM.

        Args:
            model_id: ID of the trained model.
            future_spend: DataFrame with future spend by channel.
            start_date: Prediction start date.
            end_date: Prediction end date.

        Returns:
            Prediction result.
        """
        query = select(MarketingMixModel).where(MarketingMixModel.id == model_id)
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if not model or not model.is_ready_for_prediction():
            raise ValueError(f"Model {model_id} is not ready for prediction")

        # Apply transformations
        channel_cols = [ch.channel_name for ch in model.channels]
        df_transformed = self.transform_features(
            future_spend,
            channel_cols,
            model.adstock_params,
            model.saturation_params
        )

        # Prepare features
        feature_cols = [f"{ch}_saturated" for ch in channel_cols]

        if model.model_config.get("include_seasonality", True):
            df_transformed["seasonality"] = self._calculate_seasonality(df_transformed)
            feature_cols.append("seasonality")

        if model.model_config.get("include_trend", True):
            # Extend trend from training
            last_trend = len(await self._load_training_data(model))
            df_transformed["trend"] = np.arange(last_trend, last_trend + len(df_transformed))
            feature_cols.append("trend")

        X = df_transformed[feature_cols].fillna(0)

        # Load model coefficients
        coefficients = model.model_coefficients
        intercept = coefficients.get("intercept", 0)
        channel_coefs = [
            coefficients["channels"].get(ch, {}).get("coefficient", 0)
            for ch in channel_cols
        ]

        # Make predictions (simplified - in production would use saved model)
        predictions = np.full(len(X), intercept)
        for i, coef in enumerate(channel_coefs):
            predictions += X.iloc[:, i].values * coef

        # Channel breakdown
        channel_predictions = {}
        for i, ch in enumerate(channel_cols):
            ch_pred = X.iloc[:, i].values * channel_coefs[i]
            channel_predictions[ch] = {
                "predicted": float(np.sum(ch_pred)),
                "contribution_pct": float(np.sum(ch_pred) / np.sum(predictions)) if np.sum(predictions) > 0 else 0
            }

        # Create prediction record
        prediction = MMMPrediction(
            model_id=model_id,
            organization_id=model.organization_id,
            start_date=start_date,
            end_date=end_date,
            prediction_type="forecast",
            predicted_total=float(np.sum(predictions)),
            prediction_interval_lower=float(np.sum(predictions) * 0.9),
            prediction_interval_upper=float(np.sum(predictions) * 1.1),
            channel_predictions=channel_predictions
        )

        self.db.add(prediction)
        await self.db.commit()

        return prediction

    # ============== Budget Optimization ==============

    async def optimize_budget(
        self,
        model_id: str,
        total_budget: float,
        constraints: Dict[str, Any] = None
    ) -> MMMBudgetOptimizer:
        """
        Optimize budget allocation across channels.

        Args:
            model_id: ID of the trained model.
            total_budget: Total budget to allocate.
            constraints: Optional constraints on allocation.

        Returns:
            Budget optimization result.
        """
        query = select(MarketingMixModel).where(MarketingMixModel.id == model_id)
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if not model or not model.is_ready_for_prediction():
            raise ValueError(f"Model {model_id} is not ready for optimization")

        # Get channel data
        channels = model.channels
        n_channels = len(channels)

        if n_channels == 0:
            raise ValueError("No channels configured for model")

        # Current allocation (from recent data)
        current_allocation = await self._get_current_allocation(model)

        # Get ROI estimates
        roi_estimates = {
            ch.channel_name: ch.roi or 1.0
            for ch in channels
        }

        # Define optimization objective
        def objective(x):
            # Negative expected return (for minimization)
            total_return = 0
            for i, ch in enumerate(channels):
                # Diminishing returns based on saturation
                spend = x[i]
                roi = roi_estimates[ch.channel_name]
                # Simplified saturation: sqrt scaling
                total_return += np.sqrt(spend) * roi * 10
            return -total_return

        # Constraints
        constraints_list = [{"type": "eq", "fun": lambda x: np.sum(x) - total_budget}]

        # Bounds
        min_spend = constraints.get("min_spend_per_channel", {}) if constraints else {}
        max_spend = constraints.get("max_spend_per_channel", {}) if constraints else {}

        bounds = []
        for ch in channels:
            min_val = min_spend.get(ch.channel_name, 0)
            max_val = max_spend.get(ch.channel_name, total_budget)
            bounds.append((min_val, max_val))

        # Initial guess (proportional to current)
        total_current = sum(current_allocation.values())
        if total_current > 0:
            x0 = [
                (current_allocation.get(ch.channel_name, 0) / total_current) * total_budget
                for ch in channels
            ]
        else:
            x0 = [total_budget / n_channels] * n_channels

        # Optimize
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints_list,
            options={"maxiter": 1000, "ftol": 1e-6}
        )

        if not result.success:
            logger.warning(f"Optimization did not converge: {result.message}")

        # Build optimized allocation
        optimized_allocation = {}
        for i, ch in enumerate(channels):
            spend = result.x[i]
            roi = roi_estimates[ch.channel_name]
            predicted_return = np.sqrt(spend) * roi * 10 if spend > 0 else 0

            optimized_allocation[ch.channel_name] = {
                "spend": float(spend),
                "predicted_return": float(predicted_return),
                "marginal_roi": float(roi)
            }

        # Calculate totals
        current_total = sum(
            current_allocation.get(ch, {}).get("predicted_return", 0)
            for ch in current_allocation
        )
        optimized_total = sum(
            opt.get("predicted_return", 0)
            for opt in optimized_allocation.values()
        )

        improvement_pct = (
            (optimized_total - current_total) / current_total * 100
            if current_total > 0 else 0
        )

        # Create optimizer result
        optimizer_result = MMMBudgetOptimizer(
            model_id=model_id,
            organization_id=model.organization_id,
            total_budget=total_budget,
            budget_currency="USD",
            optimization_period_days=30,
            constraints=constraints or {},
            current_allocation=current_allocation,
            optimized_allocation=optimized_allocation,
            current_predicted_total=float(current_total),
            optimized_predicted_total=float(optimized_total),
            improvement_pct=float(improvement_pct),
            improvement_absolute=float(optimized_total - current_total),
            status="completed",
            completed_at=datetime.utcnow()
        )

        self.db.add(optimizer_result)
        await self.db.commit()

        return optimizer_result

    async def _get_current_allocation(
        self,
        model: MarketingMixModel
    ) -> Dict[str, Dict[str, float]]:
        """Get current budget allocation from recent data."""
        query = select(MMMChannelDaily).where(
            MMMChannelDaily.model_id == model.id
        ).order_by(desc(MMMChannelDaily.date)).limit(30)

        result = await self.db.execute(query)
        recent_data = result.scalars().all()

        allocation = {}
        for day in recent_data:
            channel_name = None
            for ch in model.channels:
                if ch.id == day.channel_id:
                    channel_name = ch.channel_name
                    break

            if channel_name:
                if channel_name not in allocation:
                    allocation[channel_name] = {"spend": 0, "predicted_return": 0}
                allocation[channel_name]["spend"] += day.spend or 0

        # Calculate predicted returns
        for ch_name, data in allocation.items():
            ch = next((c for c in model.channels if c.channel_name == ch_name), None)
            if ch and ch.roi:
                data["predicted_return"] = data["spend"] * (1 + ch.roi)

        return allocation

    # ============== Reporting ==============

    async def get_model_summary(
        self,
        model_id: str
    ) -> Dict[str, Any]:
        """Get summary of model performance and insights."""
        query = select(MarketingMixModel).where(MarketingMixModel.id == model_id)
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            return {}

        return {
            "model_id": model.id,
            "name": model.name,
            "status": model.status.value if model.status else None,
            "performance_metrics": model.performance_metrics,
            "channel_rois": {
                ch.channel_name: {"roi": ch.roi, "mroi": ch.marginal_roi}
                for ch in model.channels
            },
            "feature_importance": model.feature_importance,
            "total_contribution": model.get_total_contribution_pct(),
            "trained_at": model.trained_at.isoformat() if model.trained_at else None
        }
