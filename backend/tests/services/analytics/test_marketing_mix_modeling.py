"""
Tests for Marketing Mix Modeling Service.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.analytics.marketing_mix_modeling import (
    MarketingMixModelingService, MMMTrainingResult
)
from app.models.marketing_mix_model import (
    MarketingMixModel, MMMChannel, MMMChannelDaily, MMMModelStatus
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mmm_service(mock_db):
    """Create a MarketingMixModelingService instance."""
    return MarketingMixModelingService(mock_db)


@pytest.fixture
def sample_training_data():
    """Create sample training data for MMM."""
    np.random.seed(42)
    n_days = 90

    dates = pd.date_range(start="2024-01-01", periods=n_days, freq="D")

    # Create spend data with some correlation to revenue
    paid_search_spend = np.random.uniform(1000, 5000, n_days)
    paid_social_spend = np.random.uniform(500, 3000, n_days)
    display_spend = np.random.uniform(200, 1500, n_days)

    # Create target variable (revenue) with some relationship to spend
    base_revenue = 10000
    revenue = (
        base_revenue
        + paid_search_spend * 2.5  # ROI of 2.5
        + paid_social_spend * 2.0  # ROI of 2.0
        + display_spend * 1.5      # ROI of 1.5
        + np.random.normal(0, 1000, n_days)  # Noise
    )

    df = pd.DataFrame({
        "date": dates,
        "paid_search": paid_search_spend,
        "paid_social": paid_social_spend,
        "display": display_spend,
        "revenue": revenue
    })

    return df


@pytest.fixture
def sample_model():
    """Create a sample MarketingMixModel."""
    model = MarketingMixModel(
        id="model1",
        organization_id="org1",
        name="Test MMM",
        target_variable="revenue",
        target_unit="usd",
        status=MMMModelStatus.DRAFT,
        model_config={
            "include_seasonality": True,
            "include_trend": True,
            "regularization": 1.0
        },
        adstock_params={
            "paid_search": {"decay": 0.3, "peak_delay": 0},
            "paid_social": {"decay": 0.4, "peak_delay": 0},
            "display": {"decay": 0.5, "peak_delay": 1}
        },
        saturation_params={
            "paid_search": {"shape": "hill", "k": 2.0},
            "paid_social": {"shape": "hill", "k": 2.0},
            "display": {"shape": "hill", "k": 1.5}
        }
    )

    # Add channels
    model.channels = [
        MMMChannel(
            id="ch1",
            model_id="model1",
            channel_type="paid_search",
            channel_name="paid_search",
            display_name="Paid Search"
        ),
        MMMChannel(
            id="ch2",
            model_id="model1",
            channel_type="paid_social",
            channel_name="paid_social",
            display_name="Paid Social"
        ),
        MMMChannel(
            id="ch3",
            model_id="model1",
            channel_type="display",
            channel_name="display",
            display_name="Display Ads"
        )
    ]

    return model


class TestAdstockTransformation:
    """Tests for adstock transformation."""

    def test_adstock_no_decay(self, mmm_service):
        """Test adstock with no decay."""
        spend = np.array([100, 0, 0, 0, 0])
        adstocked = mmm_service.apply_adstock(spend, decay=0.0)

        # With no decay, output should equal input
        np.testing.assert_array_almost_equal(adstocked, spend)

    def test_adstock_with_decay(self, mmm_service):
        """Test adstock with decay."""
        spend = np.array([100, 0, 0, 0, 0])
        adstocked = mmm_service.apply_adstock(spend, decay=0.5)

        # Check that carryover effect exists
        assert adstocked[0] == 100
        assert adstocked[1] == 50  # 100 * 0.5
        assert adstocked[2] == 25  # 50 * 0.5

    def test_adstock_with_peak_delay(self, mmm_service):
        """Test adstock with peak delay."""
        spend = np.array([100, 0, 0, 0, 0, 0, 0])
        adstocked = mmm_service.apply_adstock(spend, decay=0.5, peak_delay=2)

        # Effect should be delayed
        assert adstocked[0] == 100
        # Peak should be around day 2
        peak_idx = np.argmax(adstocked)
        assert peak_idx >= 1


class TestSaturationTransformation:
    """Tests for saturation transformation."""

    def test_saturation_hill_function(self, mmm_service):
        """Test Hill saturation function."""
        spend = np.array([0, 50, 100, 200, 500])
        saturated = mmm_service.apply_saturation(
            spend, shape="hill", k=2.0, half_spend=100
        )

        # Check properties
        assert saturated[0] == 0  # Zero input -> zero output
        assert saturated[2] == 0.5  # At half_spend -> 0.5
        assert all(np.diff(saturated) >= 0)  # Monotonically increasing
        assert saturated[-1] < 1.0  # Approaches but doesn't reach 1

    def test_saturation_logistic(self, mmm_service):
        """Test logistic saturation function."""
        spend = np.array([0, 50, 100, 200])
        saturated = mmm_service.apply_saturation(
            spend, shape="logistic", k=1.0, half_spend=100
        )

        assert all(saturated >= 0)
        assert all(saturated <= 1)
        assert saturated[2] == pytest.approx(0.5, abs=0.1)

    def test_saturation_linear(self, mmm_service):
        """Test linear saturation function."""
        spend = np.array([0, 50, 100, 200])
        saturated = mmm_service.apply_saturation(
            spend, shape="linear", half_spend=100
        )

        assert saturated[0] == 0
        assert saturated[2] == pytest.approx(0.5, abs=0.01)


class TestFeatureTransformation:
    """Tests for feature transformation pipeline."""

    def test_transform_features(self, mmm_service, sample_training_data):
        """Test complete feature transformation pipeline."""
        channel_cols = ["paid_search", "paid_social", "display"]
        adstock_params = {
            "paid_search": {"decay": 0.3},
            "paid_social": {"decay": 0.4},
            "display": {"decay": 0.5}
        }
        saturation_params = {
            "paid_search": {"shape": "hill", "k": 2.0},
            "paid_social": {"shape": "hill", "k": 2.0},
            "display": {"shape": "hill", "k": 1.5}
        }

        df_transformed = mmm_service.transform_features(
            sample_training_data,
            channel_cols,
            adstock_params,
            saturation_params
        )

        # Check that transformed columns exist
        assert "paid_search_adstocked" in df_transformed.columns
        assert "paid_search_saturated" in df_transformed.columns
        assert "paid_social_adstocked" in df_transformed.columns
        assert "paid_social_saturated" in df_transformed.columns

        # Check that values are reasonable
        assert all(df_transformed["paid_search_saturated"] >= 0)
        assert all(df_transformed["paid_search_saturated"] <= 1)


class TestModelTraining:
    """Tests for model training."""

    @pytest.mark.asyncio
    async def test_train_model_success(self, mmm_service, sample_model, sample_training_data, mock_db):
        """Test successful model training."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_model
        mock_db.execute.return_value = mock_result

        # Mock training data loading
        with patch.object(mmm_service, '_load_training_data', return_value=sample_training_data):
            result = await mmm_service.train_model("model1")

        assert result is not None
        assert result.model_id == "model1"
        assert result.r_squared > 0
        assert result.r_squared <= 1.0
        assert result.mape >= 0
        assert "channels" in result.coefficients

    @pytest.mark.asyncio
    async def test_train_model_not_found(self, mmm_service, mock_db):
        """Test training with non-existent model."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Model .* not found"):
            await mmm_service.train_model("nonexistent")

    def test_calculate_seasonality(self, mmm_service):
        """Test seasonality calculation."""
        df = pd.DataFrame({
            "date": pd.date_range(start="2024-01-01", periods=365, freq="D")
        })

        seasonality = mmm_service._calculate_seasonality(df)

        assert len(seasonality) == 365
        assert all(seasonality >= -1)
        assert all(seasonality <= 1)

    def test_calculate_contributions(self, mmm_service):
        """Test contribution calculation."""
        X = np.array([
            [1, 2, 3],
            [2, 3, 4],
            [3, 4, 5]
        ])
        coefficients = np.array([0.5, 0.3, 0.2])
        intercept = 1.0
        y = np.array([10, 15, 20])

        contributions = mmm_service._calculate_contributions(X, coefficients, intercept, y)

        assert "feature_0" in contributions
        assert "feature_1" in contributions
        assert "feature_2" in contributions
        # Contributions should sum to approximately 1 (excluding intercept)
        total = sum(v for k, v in contributions.items() if k.startswith("feature_"))
        assert total == pytest.approx(1.0, abs=0.01)


class TestPrediction:
    """Tests for prediction functionality."""

    @pytest.mark.asyncio
    async def test_predict_success(self, mmm_service, sample_model, mock_db):
        """Test successful prediction."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_model
        mock_db.execute.return_value = mock_result

        # Create future spend data
        future_spend = pd.DataFrame({
            "paid_search": [2000, 2500, 3000],
            "paid_social": [1500, 1800, 2000],
            "display": [800, 1000, 1200]
        })

        with patch.object(mmm_service, '_load_training_data', return_value=future_spend):
            prediction = await mmm_service.predict(
                model_id="model1",
                future_spend=future_spend,
                start_date=date(2024, 4, 1),
                end_date=date(2024, 4, 3)
            )

        assert prediction is not None
        assert prediction.model_id == "model1"
        assert prediction.predicted_total > 0
        assert "paid_search" in prediction.channel_predictions

    @pytest.mark.asyncio
    async def test_predict_model_not_ready(self, mmm_service, mock_db):
        """Test prediction with model not ready."""
        model = MarketingMixModel(
            id="model1",
            organization_id="org1",
            name="Test MMM",
            target_variable="revenue",
            status=MMMModelStatus.DRAFT  # Not trained
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not ready for prediction"):
            await mmm_service.predict(
                model_id="model1",
                future_spend=pd.DataFrame(),
                start_date=date(2024, 4, 1),
                end_date=date(2024, 4, 3)
            )


class TestBudgetOptimization:
    """Tests for budget optimization."""

    @pytest.mark.asyncio
    async def test_optimize_budget(self, mmm_service, sample_model, mock_db):
        """Test budget optimization."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_model
        mock_db.execute.return_value = mock_result

        # Mock current allocation
        with patch.object(mmm_service, '_get_current_allocation', return_value={
            "paid_search": {"spend": 50000, "predicted_return": 125000},
            "paid_social": {"spend": 30000, "predicted_return": 60000},
            "display": {"spend": 20000, "predicted_return": 35000}
        }):
            result = await mmm_service.optimize_budget(
                model_id="model1",
                total_budget=100000
            )

        assert result is not None
        assert result.model_id == "model1"
        assert result.total_budget == 100000
        assert result.improvement_pct >= 0
        assert "paid_search" in result.optimized_allocation
        assert "paid_social" in result.optimized_allocation

    @pytest.mark.asyncio
    async def test_optimize_budget_with_constraints(self, mmm_service, sample_model, mock_db):
        """Test budget optimization with constraints."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_model
        mock_db.execute.return_value = mock_result

        constraints = {
            "min_spend_per_channel": {"paid_search": 20000},
            "max_spend_per_channel": {"paid_search": 60000}
        }

        with patch.object(mmm_service, '_get_current_allocation', return_value={
            "paid_search": {"spend": 40000, "predicted_return": 100000}
        }):
            result = await mmm_service.optimize_budget(
                model_id="model1",
                total_budget=100000,
                constraints=constraints
            )

        assert result is not None
        # Check that constraints are respected
        paid_search_spend = result.optimized_allocation["paid_search"]["spend"]
        assert paid_search_spend >= 20000
        assert paid_search_spend <= 60000


class TestReporting:
    """Tests for reporting functionality."""

    @pytest.mark.asyncio
    async def test_get_model_summary(self, mmm_service, sample_model, mock_db):
        """Test getting model summary."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_model
        mock_db.execute.return_value = mock_result

        summary = await mmm_service.get_model_summary("model1")

        assert summary is not None
        assert summary["model_id"] == "model1"
        assert summary["name"] == "Test MMM"
        assert "channel_rois" in summary

    @pytest.mark.asyncio
    async def test_get_model_summary_not_found(self, mmm_service, mock_db):
        """Test getting summary for non-existent model."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        summary = await mmm_service.get_model_summary("nonexistent")

        assert summary == {}


class TestModelHelpers:
    """Tests for model helper methods."""

    def test_model_is_ready_for_prediction(self, sample_model):
        """Test model readiness check."""
        sample_model.status = MMMModelStatus.TRAINED
        assert sample_model.is_ready_for_prediction() is True

        sample_model.status = MMMModelStatus.DRAFT
        assert sample_model.is_ready_for_prediction() is False

    def test_model_get_channel_roi(self, sample_model):
        """Test getting channel ROI."""
        sample_model.model_coefficients = {
            "channels": {
                "paid_search": {"roi": 3.5}
            }
        }

        roi = sample_model.get_channel_roi("paid_search")
        assert roi == 3.5

        roi = sample_model.get_channel_roi("nonexistent")
        assert roi is None

    def test_model_get_total_contribution_pct(self, sample_model):
        """Test getting total contribution percentages."""
        sample_model.model_coefficients = {
            "channels": {
                "paid_search": {"contribution_pct": 0.4},
                "paid_social": {"contribution_pct": 0.3}
            },
            "baseline": {"contribution_pct": 0.3}
        }

        contributions = sample_model.get_total_contribution_pct()

        assert contributions["paid_search"] == 0.4
        assert contributions["paid_social"] == 0.3
        assert contributions["baseline"] == 0.3


class TestBudgetOptimizerHelpers:
    """Tests for budget optimizer helper methods."""

    def test_get_reallocation_recommendations():
        """Test getting reallocation recommendations."""
        from app.models.marketing_mix_model import MMMBudgetOptimizer

        optimizer = MMMBudgetOptimizer(
            model_id="model1",
            organization_id="org1",
            total_budget=100000,
            current_allocation={
                "paid_search": {"spend": 50000},
                "paid_social": {"spend": 30000},
                "display": {"spend": 20000}
            },
            optimized_allocation={
                "paid_search": {"spend": 60000, "predicted_return": 150000, "marginal_roi": 2.5},
                "paid_social": {"spend": 25000, "predicted_return": 55000, "marginal_roi": 2.2},
                "display": {"spend": 15000, "predicted_return": 28000, "marginal_roi": 1.9}
            },
            current_predicted_total=125000,
            optimized_predicted_total=150000,
            improvement_pct=20.0,
            improvement_absolute=25000
        )

        recommendations = optimizer.get_reallocation_recommendations()

        assert len(recommendations) == 3
        # Should be sorted by absolute change percentage
        assert recommendations[0]["channel"] in ["paid_search", "paid_social", "display"]
        assert "change_pct" in recommendations[0]
        assert "priority" in recommendations[0]
