"""
A/B Testing Engine.

Provides comprehensive A/B testing capabilities including:
- Experiment creation and management
- User assignment with consistent hashing
- Statistical significance testing
- Auto-winner selection
"""
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from scipy import stats
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ...models.experiment import Experiment, ExperimentStatus, ExperimentType
from ...models.experiment_variant import ExperimentVariant
from ...models.experiment_assignment import ExperimentAssignment
from ...models.experiment_result import ExperimentResult

logger = logging.getLogger(__name__)


@dataclass
class VariantConfig:
    """Configuration for creating a variant."""
    name: str
    traffic_percentage: float
    configuration: Dict[str, Any]
    is_control: bool = False
    description: Optional[str] = None


@dataclass
class AssignmentResult:
    """Result of user assignment."""
    variant_id: str
    variant_name: str
    is_control: bool
    configuration: Dict[str, Any]
    assignment_id: str


class ABTestingEngine:
    """
    A/B testing engine for running controlled experiments.
    
    Features:
    - Consistent user assignment (same user always sees same variant)
    - Statistical significance testing (chi-square, t-test)
    - Sample size calculation
    - Auto-winner detection
    """
    
    def __init__(self, db_session: AsyncSession):
        """Initialize with database session."""
        self.db = db_session
    
    # === Experiment Management ===
    
    async def create_experiment(
        self,
        organization_id: str,
        name: str,
        hypothesis: str,
        primary_metric: str,
        variants: List[VariantConfig],
        experiment_type: ExperimentType = ExperimentType.AB_TEST,
        traffic_allocation: float = 1.0,
        min_sample_size: int = 100,
        confidence_level: float = 0.95,
        statistical_power: float = 0.8,
        minimum_detectable_effect: float = 0.05,
        campaign_id: Optional[str] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
        secondary_metrics: Optional[List[str]] = None,
        auto_winner_selection: bool = False,
    ) -> Experiment:
        """
        Create a new A/B test experiment.
        
        Args:
            organization_id: Organization owning the experiment
            name: Experiment name
            hypothesis: What we're testing
            primary_metric: Main metric to measure (e.g., "conversion_rate")
            variants: List of variant configurations
            experiment_type: Type of experiment
            traffic_allocation: % of traffic to include (0.0 to 1.0)
            min_sample_size: Minimum samples before analysis
            confidence_level: Statistical confidence (e.g., 0.95 for 95%)
            statistical_power: Power to detect effect (usually 0.8)
            minimum_detectable_effect: Minimum lift to detect
            campaign_id: Optional associated campaign
            created_by: User creating the experiment
            description: Optional description
            secondary_metrics: Additional metrics to track
            auto_winner_selection: Auto-select winner when significant
            
        Returns:
            Created Experiment instance
        """
        # Validate traffic percentages sum to 100
        total_traffic = sum(v.traffic_percentage for v in variants)
        if abs(total_traffic - 100.0) > 0.01:
            raise ValueError(f"Traffic percentages must sum to 100%, got {total_traffic}%")
        
        # Validate at least one control variant
        if not any(v.is_control for v in variants):
            raise ValueError("At least one variant must be marked as control")
        
        # Calculate target sample size
        control_variant = next(v for v in variants if v.is_control)
        target_sample = self._calculate_sample_size(
            baseline_rate=0.1,  # Assume 10% baseline, can be adjusted
            minimum_detectable_effect=minimum_detectable_effect,
            power=statistical_power,
            alpha=1 - confidence_level
        )
        
        # Create experiment
        experiment = Experiment(
            organization_id=organization_id,
            name=name,
            description=description,
            experiment_type=experiment_type,
            status=ExperimentStatus.DRAFT,
            hypothesis=hypothesis,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics or [],
            traffic_allocation=traffic_allocation,
            min_sample_size=min_sample_size,
            target_sample_size=target_sample,
            confidence_level=confidence_level,
            statistical_power=statistical_power,
            minimum_detectable_effect=minimum_detectable_effect,
            campaign_id=campaign_id,
            created_by=created_by,
            auto_winner_selection=auto_winner_selection,
        )
        
        self.db.add(experiment)
        await self.db.flush()  # Get experiment ID
        
        # Create variants
        for variant_config in variants:
            variant = ExperimentVariant(
                experiment_id=experiment.id,
                name=variant_config.name,
                description=variant_config.description,
                traffic_percentage=variant_config.traffic_percentage,
                configuration=variant_config.configuration,
                is_control=variant_config.is_control,
            )
            self.db.add(variant)
        
        await self.db.commit()
        await self.db.refresh(experiment)
        
        logger.info(f"Created experiment {experiment.id}: {name}")
        return experiment
    
    async def start_experiment(self, experiment_id: str) -> Experiment:
        """
        Start running an experiment.
        
        Args:
            experiment_id: ID of experiment to start
            
        Returns:
            Updated Experiment instance
        """
        result = await self.db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if experiment.status != ExperimentStatus.DRAFT:
            raise ValueError(f"Cannot start experiment with status {experiment.status}")
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.start_date = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(experiment)
        
        logger.info(f"Started experiment {experiment_id}")
        return experiment
    
    async def stop_experiment(
        self,
        experiment_id: str,
        winner_variant_id: Optional[str] = None,
        stopped_by: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Experiment:
        """
        Stop an experiment and optionally declare a winner.
        
        Args:
            experiment_id: ID of experiment to stop
            winner_variant_id: Optional winning variant ID
            stopped_by: User stopping the experiment
            reason: Reason for stopping
            
        Returns:
            Updated Experiment instance
        """
        result = await self.db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if experiment.status not in [ExperimentStatus.RUNNING, ExperimentStatus.PAUSED]:
            raise ValueError(f"Cannot stop experiment with status {experiment.status}")
        
        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_date = datetime.utcnow()
        experiment.stopped_by = stopped_by
        experiment.stopped_reason = reason
        
        if winner_variant_id:
            experiment.winner_variant_id = winner_variant_id
            experiment.winner_declared_at = datetime.utcnow()
            experiment.winner_reason = reason or "Manually selected"
        
        await self.db.commit()
        await self.db.refresh(experiment)
        
        logger.info(f"Stopped experiment {experiment_id}, winner: {winner_variant_id}")
        return experiment
    
    async def pause_experiment(self, experiment_id: str) -> Experiment:
        """Pause a running experiment."""
        result = await self.db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if experiment.status != ExperimentStatus.RUNNING:
            raise ValueError(f"Cannot pause experiment with status {experiment.status}")
        
        experiment.status = ExperimentStatus.PAUSED
        
        await self.db.commit()
        await self.db.refresh(experiment)
        
        logger.info(f"Paused experiment {experiment_id}")
        return experiment
    
    # === User Assignment ===
    
    async def assign_user(
        self,
        experiment_id: str,
        user_id: Optional[str] = None,
        anonymous_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> AssignmentResult:
        """
        Assign a user to a variant using consistent hashing.
        
        Returns the same variant if user already assigned.
        
        Args:
            experiment_id: Experiment ID
            user_id: Logged-in user ID (optional)
            anonymous_id: Anonymous visitor ID (optional)
            context: Assignment context (device, location, etc.)
            
        Returns:
            AssignmentResult with variant details
        """
        if not user_id and not anonymous_id:
            raise ValueError("Either user_id or anonymous_id must be provided")
        
        # Check for existing assignment
        existing = await self._get_existing_assignment(
            experiment_id, user_id, anonymous_id
        )
        
        if existing:
            variant = await self.db.get(ExperimentVariant, existing.variant_id)
            return AssignmentResult(
                variant_id=variant.id,
                variant_name=variant.name,
                is_control=variant.is_control,
                configuration=variant.configuration,
                assignment_id=existing.id
            )
        
        # Get experiment and variants
        result = await self.db.execute(
            select(Experiment).where(
                and_(
                    Experiment.id == experiment_id,
                    Experiment.status == ExperimentStatus.RUNNING
                )
            )
        )
        experiment = result.scalar_one_or_none()
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found or not running")
        
        # Get variants
        result = await self.db.execute(
            select(ExperimentVariant)
            .where(ExperimentVariant.experiment_id == experiment_id)
            .order_by(ExperimentVariant.traffic_percentage.desc())
        )
        variants = result.scalars().all()
        
        if not variants:
            raise ValueError(f"No variants found for experiment {experiment_id}")
        
        # Use consistent hashing to assign
        assignment_key = user_id or anonymous_id
        variant = self._consistent_hash_assignment(assignment_key, experiment_id, variants)
        
        # Create assignment record
        assignment = ExperimentAssignment(
            experiment_id=experiment_id,
            variant_id=variant.id,
            user_id=user_id,
            anonymous_id=anonymous_id,
            context=context or {},
            first_exposed_at=datetime.utcnow()
        )
        
        self.db.add(assignment)
        
        # Update variant stats
        variant.total_assignments += 1
        
        await self.db.commit()
        await self.db.refresh(assignment)
        
        return AssignmentResult(
            variant_id=variant.id,
            variant_name=variant.name,
            is_control=variant.is_control,
            configuration=variant.configuration,
            assignment_id=assignment.id
        )
    
    async def _get_existing_assignment(
        self,
        experiment_id: str,
        user_id: Optional[str],
        anonymous_id: Optional[str]
    ) -> Optional[ExperimentAssignment]:
        """Check if user already has an assignment."""
        if user_id:
            result = await self.db.execute(
                select(ExperimentAssignment).where(
                    and_(
                        ExperimentAssignment.experiment_id == experiment_id,
                        ExperimentAssignment.user_id == user_id
                    )
                )
            )
        else:
            result = await self.db.execute(
                select(ExperimentAssignment).where(
                    and_(
                        ExperimentAssignment.experiment_id == experiment_id,
                        ExperimentAssignment.anonymous_id == anonymous_id
                    )
                )
            )
        
        return result.scalar_one_or_none()
    
    def _consistent_hash_assignment(
        self,
        user_id: str,
        experiment_id: str,
        variants: List[ExperimentVariant]
    ) -> ExperimentVariant:
        """
        Deterministic assignment using consistent hashing.
        
        This ensures the same user always gets the same variant
        for a given experiment.
        """
        # Create hash from user_id + experiment_id
        hash_input = f"{user_id}:{experiment_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # Map hash to variant based on traffic percentages
        hash_normalized = (hash_value % 10000) / 100.0  # 0.0 to 100.0
        
        cumulative = 0.0
        for variant in variants:
            cumulative += variant.traffic_percentage
            if hash_normalized <= cumulative:
                return variant
        
        # Fallback to last variant (shouldn't happen with proper percentages)
        return variants[-1]
    
    # === Traffic Allocation ===
    
    async def allocate_traffic(
        self,
        experiment_id: str,
        allocations: Dict[str, float]
    ) -> List[ExperimentVariant]:
        """
        Adjust traffic allocation between variants.
        
        Args:
            experiment_id: Experiment ID
            allocations: Dict mapping variant_id -> percentage
            
        Returns:
            Updated list of variants
        """
        # Validate allocations sum to 100
        total = sum(allocations.values())
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Allocations must sum to 100%, got {total}%")
        
        result = await self.db.execute(
            select(ExperimentVariant).where(
                ExperimentVariant.experiment_id == experiment_id
            )
        )
        variants = result.scalars().all()
        
        variant_map = {v.id: v for v in variants}
        
        for variant_id, percentage in allocations.items():
            if variant_id not in variant_map:
                raise ValueError(f"Variant {variant_id} not found in experiment")
            
            variant_map[variant_id].traffic_percentage = percentage
        
        await self.db.commit()
        
        for variant in variants:
            await self.db.refresh(variant)
        
        logger.info(f"Updated traffic allocation for experiment {experiment_id}")
        return variants
    
    # === Statistical Analysis ===
    
    async def calculate_results(
        self,
        experiment_id: str,
        metric_name: Optional[str] = None
    ) -> Dict[str, ExperimentResult]:
        """
        Calculate statistical results for all variants.
        
        Uses chi-square test for conversion rates,
        t-test for continuous metrics.
        
        Args:
            experiment_id: Experiment ID
            metric_name: Specific metric to calculate (default: experiment's primary_metric)
            
        Returns:
            Dict mapping variant_id -> ExperimentResult
        """
        # Get experiment
        result = await self.db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        metric = metric_name or experiment.primary_metric
        
        # Get control variant
        result = await self.db.execute(
            select(ExperimentVariant).where(
                and_(
                    ExperimentVariant.experiment_id == experiment_id,
                    ExperimentVariant.is_control == True
                )
            )
        )
        control = result.scalar_one_or_none()
        
        if not control:
            raise ValueError("No control variant found")
        
        # Get all variants with assignment counts
        result = await self.db.execute(
            select(ExperimentVariant).where(
                ExperimentVariant.experiment_id == experiment_id
            )
        )
        variants = result.scalars().all()
        
        # Calculate metrics for each variant
        results = {}
        
        for variant in variants:
            # Get assignment stats
            stats_result = await self.db.execute(
                select(
                    func.count(ExperimentAssignment.id).label('total'),
                    func.sum(func.cast(ExperimentAssignment.converted_at.isnot(None), Integer)).label('conversions')
                ).where(ExperimentAssignment.variant_id == variant.id)
            )
            row = stats_result.one()
            total = row.total or 0
            conversions = row.conversions or 0
            
            conversion_rate = conversions / total if total > 0 else 0.0
            
            # Create or update result
            result = ExperimentResult(
                experiment_id=experiment_id,
                variant_id=variant.id,
                metric_name=metric,
                sample_size=total,
                conversions=conversions,
                metric_value=conversion_rate,
                calculated_at=datetime.utcnow()
            )
            
            self.db.add(result)
            results[variant.id] = result
        
        await self.db.flush()
        
        # Calculate comparisons to control
        control_result = results.get(control.id)
        if control_result and control_result.sample_size > 0:
            control_rate = control_result.metric_value
            
            for variant_id, result in results.items():
                if variant_id == control.id:
                    result.lift_percentage = 0.0
                    result.lift_absolute = 0.0
                    continue
                
                if result.sample_size > 0:
                    variant_rate = result.metric_value
                    result.lift_absolute = variant_rate - control_rate
                    result.lift_percentage = (variant_rate - control_rate) / control_rate if control_rate > 0 else 0.0
                    
                    # Calculate statistical significance
                    is_sig, p_value, ci = self._check_statistical_significance(
                        control_result.conversions,
                        control_result.sample_size,
                        result.conversions,
                        result.sample_size,
                        experiment.confidence_level
                    )
                    
                    result.p_value = p_value
                    result.is_statistically_significant = is_sig
                    result.confidence_interval_lower = ci[0] if ci else None
                    result.confidence_interval_upper = ci[1] if ci else None
                    result.statistical_test = "chi_square"
        
        await self.db.commit()
        
        logger.info(f"Calculated results for experiment {experiment_id}")
        return results
    
    def _calculate_sample_size(
        self,
        baseline_rate: float,
        minimum_detectable_effect: float,
        power: float = 0.8,
        alpha: float = 0.05
    ) -> int:
        """
        Calculate required sample size for statistical significance.
        
        Uses the formula for two-proportion z-test.
        
        Args:
            baseline_rate: Baseline conversion rate (e.g., 0.10 for 10%)
            minimum_detectable_effect: Minimum relative lift to detect (e.g., 0.15 for 15%)
            power: Statistical power (1 - beta)
            alpha: Significance level
            
        Returns:
            Required sample size per variant
        """
        # Variant rate with MDE
        variant_rate = baseline_rate * (1 + minimum_detectable_effect)
        
        # Z-scores
        z_alpha = stats.norm.ppf(1 - alpha / 2)  # Two-tailed
        z_beta = stats.norm.ppf(power)
        
        # Pooled proportion
        p_pooled = (baseline_rate + variant_rate) / 2
        
        # Sample size formula
        numerator = (z_alpha * np.sqrt(2 * p_pooled * (1 - p_pooled)) + 
                     z_beta * np.sqrt(baseline_rate * (1 - baseline_rate) + 
                                     variant_rate * (1 - variant_rate))) ** 2
        denominator = (variant_rate - baseline_rate) ** 2
        
        sample_size = int(np.ceil(numerator / denominator))
        
        return max(sample_size, 100)  # Minimum 100 samples
    
    def _check_statistical_significance(
        self,
        control_conversions: int,
        control_sample: int,
        variant_conversions: int,
        variant_sample: int,
        confidence_level: float = 0.95
    ) -> Tuple[bool, float, Optional[Tuple[float, float]]]:
        """
        Check if difference is statistically significant.
        
        Uses chi-square test for conversion rates.
        
        Args:
            control_conversions: Conversions in control
            control_sample: Total samples in control
            variant_conversions: Conversions in variant
            variant_sample: Total samples in variant
            confidence_level: Confidence level (e.g., 0.95)
            
        Returns:
            Tuple of (is_significant, p_value, confidence_interval)
        """
        alpha = 1 - confidence_level
        
        # Create contingency table
        control_non_conversions = control_sample - control_conversions
        variant_non_conversions = variant_sample - variant_conversions
        
        table = np.array([
            [control_conversions, control_non_conversions],
            [variant_conversions, variant_non_conversions]
        ])
        
        # Chi-square test
        chi2, p_value, dof, expected = stats.chi2_contingency(table)
        
        is_significant = p_value < alpha
        
        # Calculate confidence interval for difference in proportions
        p1 = control_conversions / control_sample if control_sample > 0 else 0
        p2 = variant_conversions / variant_sample if variant_sample > 0 else 0
        
        se = np.sqrt(p1 * (1 - p1) / control_sample + p2 * (1 - p2) / variant_sample)
        z = stats.norm.ppf(1 - alpha / 2)
        
        diff = p2 - p1
        ci_lower = diff - z * se
        ci_upper = diff + z * se
        
        return is_significant, p_value, (ci_lower, ci_upper)
    
    # === Auto-Winner Selection ===
    
    async def check_auto_winner(
        self,
        experiment_id: str,
        min_confidence: float = 0.95,
        min_lift: float = 0.05
    ) -> Optional[ExperimentVariant]:
        """
        Automatically check if a winner can be declared.
        
        Args:
            experiment_id: Experiment ID
            min_confidence: Minimum confidence level
            min_lift: Minimum lift to declare winner
            
        Returns:
            Winning variant or None if no winner yet
        """
        # Get experiment
        result = await self.db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # Calculate latest results
        results = await self.calculate_results(experiment_id)
        
        # Get control
        result = await self.db.execute(
            select(ExperimentVariant).where(
                and_(
                    ExperimentVariant.experiment_id == experiment_id,
                    ExperimentVariant.is_control == True
                )
            )
        )
        control = result.scalar_one_or_none()
        
        if not control:
            return None
        
        control_result = results.get(control.id)
        if not control_result:
            return None
        
        # Check each variant
        for variant_id, result in results.items():
            if variant_id == control.id:
                continue
            
            # Check criteria
            if (result.is_statistically_significant and 
                result.p_value is not None and 
                result.p_value <= (1 - min_confidence) and
                result.lift_percentage is not None and
                result.lift_percentage >= min_lift):
                
                # Winner found
                variant = await self.db.get(ExperimentVariant, variant_id)
                
                # Auto-stop if enabled
                if experiment.auto_winner_selection:
                    await self.stop_experiment(
                        experiment_id=experiment_id,
                        winner_variant_id=variant_id,
                        reason=f"Auto-selected: {result.lift_percentage*100:.2f}% lift, p={result.p_value:.4f}"
                    )
                
                return variant
        
        return None
    
    async def track_conversion(
        self,
        experiment_id: str,
        user_id: Optional[str] = None,
        anonymous_id: Optional[str] = None,
        conversion_value: Optional[Dict] = None
    ) -> bool:
        """
        Track a conversion for a user in an experiment.
        
        Args:
            experiment_id: Experiment ID
            user_id: User ID (if logged in)
            anonymous_id: Anonymous ID (if not logged in)
            conversion_value: Optional conversion details
            
        Returns:
            True if conversion was tracked, False if no assignment found
        """
        assignment = await self._get_existing_assignment(
            experiment_id, user_id, anonymous_id
        )
        
        if not assignment:
            return False
        
        if assignment.converted_at:
            # Already converted
            return True
        
        assignment.mark_converted(conversion_value)
        
        # Update variant stats
        variant = await self.db.get(ExperimentVariant, assignment.variant_id)
        if variant:
            variant.total_conversions += 1
            variant.update_conversion_rate()
        
        await self.db.commit()
        
        logger.info(f"Tracked conversion for assignment {assignment.id}")
        return True