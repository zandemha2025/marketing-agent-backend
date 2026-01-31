"""
Self-Optimizing Campaign Engine.

Provides automatic campaign optimization including:
- Budget allocation across channels/audiences
- Creative rotation and optimization
- Audience targeting optimization
- Bid optimization for paid campaigns
- Continuous optimization loop
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ...models.campaign import Campaign, CampaignStatus
from ...models.customer_segment import CustomerSegment
from ...models.asset import Asset

logger = logging.getLogger(__name__)


class OptimizationStrategy(str, Enum):
    """Optimization strategies."""
    BALANCED = "balanced"           # Balance exploration and exploitation
    AGGRESSIVE = "aggressive"       # Quickly shift to best performers
    CONSERVATIVE = "conservative"   # Slow, cautious changes


class CreativeRotationStrategy(str, Enum):
    """Creative rotation strategies."""
    EVEN = "even"                           # Equal distribution
    PERFORMANCE_WEIGHTED = "performance_weighted"  # Based on performance
    WINNER_TAKE_ALL = "winner_take_all"     # Only best performer
    THOMPSON_SAMPLING = "thompson_sampling" # Bayesian approach


@dataclass
class ChannelPerformance:
    """Performance metrics for a channel."""
    channel_id: str
    channel_name: str
    spend: float
    impressions: int
    clicks: int
    conversions: int
    revenue: float
    
    @property
    def ctr(self) -> float:
        """Click-through rate."""
        return self.clicks / self.impressions if self.impressions > 0 else 0.0
    
    @property
    def cvr(self) -> float:
        """Conversion rate."""
        return self.conversions / self.clicks if self.clicks > 0 else 0.0
    
    @property
    def cpc(self) -> float:
        """Cost per click."""
        return self.spend / self.clicks if self.clicks > 0 else 0.0
    
    @property
    def cpa(self) -> float:
        """Cost per acquisition."""
        return self.spend / self.conversions if self.conversions > 0 else float('inf')
    
    @property
    def roas(self) -> float:
        """Return on ad spend."""
        return self.revenue / self.spend if self.spend > 0 else 0.0


@dataclass
class CreativePerformance:
    """Performance metrics for a creative."""
    creative_id: str
    creative_name: str
    asset_id: str
    impressions: int
    clicks: int
    conversions: int
    revenue: float
    
    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions if self.impressions > 0 else 0.0
    
    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.clicks if self.clicks > 0 else 0.0


@dataclass
class SegmentPerformance:
    """Performance metrics for an audience segment."""
    segment_id: str
    segment_name: str
    audience_size: int
    conversions: int
    revenue: float
    engagement_score: float
    
    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.audience_size if self.audience_size > 0 else 0.0


@dataclass
class BudgetAllocation:
    """Budget allocation result."""
    channel_allocations: Dict[str, float]  # channel_id -> budget amount
    total_budget: float
    expected_roas: float
    confidence: float


@dataclass
class BudgetReallocation:
    """Budget reallocation changes."""
    changes: Dict[str, float]  # channel_id -> delta (positive or negative)
    reason: str
    expected_improvement: float


@dataclass
class CreativeOptimization:
    """Creative optimization result."""
    rotation_weights: Dict[str, float]  # creative_id -> weight (0-1)
    recommendations: List[str]  # Text recommendations
    expected_ctr_improvement: float


@dataclass
class AudienceOptimization:
    """Audience optimization result."""
    expand_segments: List[str]  # segment_ids to expand
    reduce_segments: List[str]  # segment_ids to reduce
    new_segments: List[Dict[str, Any]]  # Suggested new segments
    expected_conversion_lift: float


@dataclass
class BidOptimization:
    """Bid optimization result."""
    bid_adjustments: Dict[str, float]  # channel_id -> multiplier
    target_cpa: Optional[float]
    target_roas: Optional[float]
    confidence: float


@dataclass
class OptimizationLog:
    """Log of optimization actions."""
    timestamp: datetime
    action_type: str
    description: str
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    expected_impact: float
    actual_impact: Optional[float] = None


class CampaignOptimizer:
    """
    Self-optimizing campaign engine.
    
    Automatically optimizes campaigns by:
    1. Analyzing performance data
    2. Making optimization decisions
    3. Applying changes
    4. Learning from results
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ):
        """Initialize optimizer."""
        self.db = db_session
        self.strategy = strategy
        self.optimization_logs: List[OptimizationLog] = []
    
    # === Budget Optimization ===
    
    async def optimize_budget_allocation(
        self,
        campaign_id: str,
        total_budget: float,
        channel_performance: List[ChannelPerformance],
        constraints: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> BudgetAllocation:
        """
        Optimize budget allocation across channels.
        
        Uses performance data to allocate budget to highest-performing channels
        while maintaining minimum spend on all channels for learning.
        
        Args:
            campaign_id: Campaign ID
            total_budget: Total budget to allocate
            channel_performance: Performance data for each channel
            constraints: Optional min/max constraints per channel
            
        Returns:
            BudgetAllocation with optimized allocations
        """
        if not channel_performance:
            raise ValueError("No channel performance data provided")
        
        # Calculate ROAS for each channel
        roas_scores = {}
        for channel in channel_performance:
            # Use ROAS as primary metric, fallback to inverse CPA
            if channel.roas > 0:
                score = channel.roas
            elif channel.cpa > 0 and channel.cpa != float('inf'):
                score = 1.0 / channel.cpa
            else:
                score = 0.0
            roas_scores[channel.channel_id] = score
        
        # Apply strategy
        if self.strategy == OptimizationStrategy.AGGRESSIVE:
            # Allocate 70% to top performer, distribute rest
            allocations = self._aggressive_allocation(roas_scores, total_budget)
        elif self.strategy == OptimizationStrategy.CONSERVATIVE:
            # More even distribution with slight bias to top performers
            allocations = self._conservative_allocation(roas_scores, total_budget)
        else:  # BALANCED
            allocations = self._balanced_allocation(roas_scores, total_budget)
        
        # Apply constraints
        if constraints:
            allocations = self._apply_constraints(allocations, constraints, total_budget)
        
        # Calculate expected ROAS
        expected_roas = self._calculate_expected_roas(allocations, channel_performance)
        
        logger.info(f"Optimized budget allocation for campaign {campaign_id}: {allocations}")
        
        return BudgetAllocation(
            channel_allocations=allocations,
            total_budget=total_budget,
            expected_roas=expected_roas,
            confidence=0.8  # Could be calculated based on data volume
        )
    
    def _aggressive_allocation(
        self,
        scores: Dict[str, float],
        total_budget: float,
        top_allocation: float = 0.7
    ) -> Dict[str, float]:
        """Aggressive allocation favoring top performer."""
        if not scores:
            return {}
        
        sorted_channels = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        allocations = {}
        
        # Top performer gets 70%
        top_channel, top_score = sorted_channels[0]
        allocations[top_channel] = total_budget * top_allocation
        
        # Rest distributed by relative performance
        remaining_budget = total_budget * (1 - top_allocation)
        remaining_score = sum(score for _, score in sorted_channels[1:])
        
        for channel_id, score in sorted_channels[1:]:
            if remaining_score > 0:
                allocations[channel_id] = remaining_budget * (score / remaining_score)
            else:
                allocations[channel_id] = remaining_budget / (len(sorted_channels) - 1)
        
        return allocations
    
    def _conservative_allocation(
        self,
        scores: Dict[str, float],
        total_budget: float,
        min_allocation: float = 0.1
    ) -> Dict[str, float]:
        """Conservative allocation with minimums for all channels."""
        n_channels = len(scores)
        allocations = {}
        
        # Minimum 10% to each channel
        min_amount = total_budget * min_allocation
        for channel_id in scores:
            allocations[channel_id] = min_amount
        
        # Distribute remaining by performance
        remaining = total_budget - (min_amount * n_channels)
        total_score = sum(scores.values())
        
        if total_score > 0:
            for channel_id, score in scores.items():
                allocations[channel_id] += remaining * (score / total_score)
        else:
            # Equal distribution if no scores
            for channel_id in scores:
                allocations[channel_id] += remaining / n_channels
        
        return allocations
    
    def _balanced_allocation(
        self,
        scores: Dict[str, float],
        total_budget: float
    ) -> Dict[str, float]:
        """Balanced allocation using softmax."""
        if not scores:
            return {}
        
        # Softmax to get probabilities
        exp_scores = np.exp(np.array(list(scores.values())))
        probabilities = exp_scores / np.sum(exp_scores)
        
        allocations = {}
        for (channel_id, _), prob in zip(scores.items(), probabilities):
            allocations[channel_id] = total_budget * prob
        
        return allocations
    
    def _apply_constraints(
        self,
        allocations: Dict[str, float],
        constraints: Dict[str, Tuple[float, float]],
        total_budget: float
    ) -> Dict[str, float]:
        """Apply min/max constraints to allocations."""
        adjusted = allocations.copy()
        
        # Apply constraints
        for channel_id, (min_pct, max_pct) in constraints.items():
            if channel_id in adjusted:
                min_amount = total_budget * min_pct
                max_amount = total_budget * max_pct
                adjusted[channel_id] = max(min_amount, min(adjusted[channel_id], max_amount))
        
        # Normalize to ensure total equals budget
        current_total = sum(adjusted.values())
        if current_total > 0:
            scale = total_budget / current_total
            adjusted = {k: v * scale for k, v in adjusted.items()}
        
        return adjusted
    
    def _calculate_expected_roas(
        self,
        allocations: Dict[str, float],
        performance: List[ChannelPerformance]
    ) -> float:
        """Calculate expected ROAS from allocations."""
        total_budget = sum(allocations.values())
        if total_budget == 0:
            return 0.0
        
        weighted_roas = 0.0
        perf_map = {p.channel_id: p for p in performance}
        
        for channel_id, budget in allocations.items():
            if channel_id in perf_map:
                weighted_roas += (budget / total_budget) * perf_map[channel_id].roas
        
        return weighted_roas
    
    async def reallocate_budget(
        self,
        campaign_id: str,
        performance_data: List[ChannelPerformance],
        max_shift_percentage: float = 0.2
    ) -> BudgetReallocation:
        """
        Real-time budget reallocation based on performance.
        
        Moves budget from underperforming to overperforming channels.
        
        Args:
            campaign_id: Campaign ID
            performance_data: Current performance by channel
            max_shift_percentage: Maximum % of budget to shift
            
        Returns:
            BudgetReallocation with changes
        """
        # Calculate performance scores
        scores = {}
        for channel in performance_data:
            # Composite score: ROAS weighted by conversion volume
            score = channel.roas * np.log1p(channel.conversions)
            scores[channel.channel_id] = score
        
        # Identify winners and losers
        avg_score = np.mean(list(scores.values()))
        winners = [c for c, s in scores.items() if s > avg_score * 1.2]
        losers = [c for c, s in scores.items() if s < avg_score * 0.8]
        
        # Calculate shifts
        changes = {}
        total_shift = 0.0
        
        for channel in performance_data:
            current_spend = channel.spend
            
            if channel.channel_id in losers:
                # Reduce budget
                reduction = current_spend * max_shift_percentage
                changes[channel.channel_id] = -reduction
                total_shift += reduction
            elif channel.channel_id in winners:
                # Will receive more budget
                changes[channel.channel_id] = 0.0
        
        # Distribute to winners
        if winners and total_shift > 0:
            winner_scores = {c: scores[c] for c in winners}
            total_winner_score = sum(winner_scores.values())
            
            for winner_id in winners:
                share = winner_scores[winner_id] / total_winner_score
                changes[winner_id] = total_shift * share
        
        # Calculate expected improvement
        expected_improvement = self._estimate_improvement(changes, performance_data)
        
        logger.info(f"Budget reallocation for campaign {campaign_id}: {changes}")
        
        return BudgetReallocation(
            changes=changes,
            reason=f"Shift from {len(losers)} underperforming to {len(winners)} overperforming channels",
            expected_improvement=expected_improvement
        )
    
    def _estimate_improvement(
        self,
        changes: Dict[str, float],
        performance: List[ChannelPerformance]
    ) -> float:
        """Estimate performance improvement from changes."""
        perf_map = {p.channel_id: p for p in performance}
        
        current_revenue = sum(p.revenue for p in performance)
        current_spend = sum(p.spend for p in performance)
        
        if current_spend == 0:
            return 0.0
        
        # Estimate new revenue based on shifts
        estimated_new_revenue = current_revenue
        for channel_id, delta in changes.items():
            if channel_id in perf_map:
                channel = perf_map[channel_id]
                if channel.spend > 0:
                    roas = channel.revenue / channel.spend
                    estimated_new_revenue += delta * roas
        
        current_roas = current_revenue / current_spend
        new_roas = estimated_new_revenue / current_spend if current_spend > 0 else 0
        
        return (new_roas - current_roas) / current_roas if current_roas > 0 else 0.0
    
    # === Creative Optimization ===
    
    async def optimize_creatives(
        self,
        campaign_id: str,
        creative_performance: List[CreativePerformance],
        rotation_strategy: CreativeRotationStrategy = CreativeRotationStrategy.PERFORMANCE_WEIGHTED
    ) -> CreativeOptimization:
        """
        Optimize creative rotation based on performance.
        
        Args:
            campaign_id: Campaign ID
            creative_performance: Performance data for each creative
            rotation_strategy: Strategy for rotation
            
        Returns:
            CreativeOptimization with rotation weights
        """
        if not creative_performance:
            raise ValueError("No creative performance data")
        
        weights = {}
        
        if rotation_strategy == CreativeRotationStrategy.EVEN:
            # Equal weights
            n = len(creative_performance)
            weights = {c.creative_id: 1.0 / n for c in creative_performance}
            
        elif rotation_strategy == CreativeRotationStrategy.WINNER_TAKE_ALL:
            # All weight to best performer
            best = max(creative_performance, key=lambda c: c.ctr)
            weights = {c.creative_id: 0.0 for c in creative_performance}
            weights[best.creative_id] = 1.0
            
        elif rotation_strategy == CreativeRotationStrategy.PERFORMANCE_WEIGHTED:
            # Weight proportional to CTR
            total_ctr = sum(c.ctr for c in creative_performance)
            if total_ctr > 0:
                weights = {c.creative_id: c.ctr / total_ctr for c in creative_performance}
            else:
                n = len(creative_performance)
                weights = {c.creative_id: 1.0 / n for c in creative_performance}
                
        elif rotation_strategy == CreativeRotationStrategy.THOMPSON_SAMPLING:
            # Bayesian approach: weight by probability of being best
            weights = self._thompson_creative_weights(creative_performance)
        
        # Generate recommendations
        recommendations = self._generate_creative_recommendations(
            creative_performance, weights
        )
        
        # Estimate improvement
        best_ctr = max(c.ctr for c in creative_performance)
        avg_ctr = np.mean([c.ctr for c in creative_performance])
        expected_improvement = (best_ctr - avg_ctr) / avg_ctr if avg_ctr > 0 else 0.0
        
        logger.info(f"Optimized creatives for campaign {campaign_id}: {weights}")
        
        return CreativeOptimization(
            rotation_weights=weights,
            recommendations=recommendations,
            expected_ctr_improvement=expected_improvement
        )
    
    def _thompson_creative_weights(
        self,
        performance: List[CreativePerformance]
    ) -> Dict[str, float]:
        """Calculate weights using Thompson Sampling."""
        weights = {}
        
        # Sample from Beta distribution for each creative
        samples = []
        for creative in performance:
            # Beta parameters
            successes = creative.clicks
            failures = creative.impressions - creative.clicks
            
            # Sample
            sample = np.random.beta(successes + 1, failures + 1)
            samples.append((creative.creative_id, sample))
        
        # Normalize samples to get weights
        total = sum(s for _, s in samples)
        if total > 0:
            weights = {cid: s / total for cid, s in samples}
        else:
            n = len(performance)
            weights = {c.creative_id: 1.0 / n for c in performance}
        
        return weights
    
    def _generate_creative_recommendations(
        self,
        performance: List[CreativePerformance],
        weights: Dict[str, float]
    ) -> List[str]:
        """Generate text recommendations based on creative performance."""
        recommendations = []
        
        # Sort by CTR
        sorted_perf = sorted(performance, key=lambda c: c.ctr, reverse=True)
        
        if sorted_perf:
            best = sorted_perf[0]
            worst = sorted_perf[-1]
            
            if best.ctr > worst.ctr * 2:
                recommendations.append(
                    f"Creative '{best.creative_name}' is significantly outperforming others. "
                    f"Consider using similar elements in future creatives."
                )
            
            low_performers = [c for c in sorted_perf if weights.get(c.creative_id, 0) < 0.1]
            if low_performers:
                recommendations.append(
                    f"Consider pausing {len(low_performers)} underperforming creative(s)."
                )
        
        return recommendations
    
    async def auto_rotate_creatives(
        self,
        campaign_id: str,
        rotation_strategy: CreativeRotationStrategy = CreativeRotationStrategy.PERFORMANCE_WEIGHTED,
        min_impressions: int = 1000
    ) -> CreativeOptimization:
        """
        Automatically rotate creatives based on performance.
        
        Args:
            campaign_id: Campaign ID
            rotation_strategy: Rotation strategy
            min_impressions: Minimum impressions before optimization
            
        Returns:
            CreativeOptimization result
        """
        # This would fetch actual performance data in production
        # For now, return a placeholder
        logger.info(f"Auto-rotating creatives for campaign {campaign_id}")
        
        return CreativeOptimization(
            rotation_weights={},
            recommendations=["Auto-rotation enabled"],
            expected_ctr_improvement=0.0
        )
    
    # === Audience Optimization ===
    
    async def optimize_audiences(
        self,
        campaign_id: str,
        segment_performance: List[SegmentPerformance]
    ) -> AudienceOptimization:
        """
        Optimize audience targeting based on performance.
        
        Args:
            campaign_id: Campaign ID
            segment_performance: Performance by segment
            
        Returns:
            AudienceOptimization with recommendations
        """
        if not segment_performance:
            raise ValueError("No segment performance data")
        
        # Calculate conversion rates
        rates = {s.segment_id: s.conversion_rate for s in segment_performance}
        avg_rate = np.mean(list(rates.values()))
        
        # Identify segments to expand/reduce
        expand = []
        reduce = []
        
        for segment in segment_performance:
            if segment.conversion_rate > avg_rate * 1.3:
                expand.append(segment.segment_id)
            elif segment.conversion_rate < avg_rate * 0.5:
                reduce.append(segment.segment_id)
        
        # Calculate expected lift
        if expand:
            expand_rates = [rates[s] for s in expand]
            expected_lift = (np.mean(expand_rates) - avg_rate) / avg_rate if avg_rate > 0 else 0.0
        else:
            expected_lift = 0.0
        
        logger.info(f"Audience optimization for campaign {campaign_id}: "
                   f"expand={expand}, reduce={reduce}")
        
        return AudienceOptimization(
            expand_segments=expand,
            reduce_segments=reduce,
            new_segments=[],  # Would be populated by ML model
            expected_conversion_lift=expected_lift
        )
    
    async def discover_high_value_segments(
        self,
        campaign_id: str,
        conversion_threshold: float = 0.05
    ) -> List[CustomerSegment]:
        """
        Use ML to discover high-value audience segments.
        
        Analyzes converting customers to find patterns.
        
        Args:
            campaign_id: Campaign ID
            conversion_threshold: Minimum conversion rate threshold
            
        Returns:
            List of high-value segments
        """
        # This would use actual ML in production
        # For now, return placeholder logic
        logger.info(f"Discovering high-value segments for campaign {campaign_id}")
        
        # Query existing segments with high conversion rates
        result = await self.db.execute(
            select(CustomerSegment).where(
                CustomerSegment.conversion_rate >= conversion_threshold
            )
        )
        
        return result.scalars().all()
    
    # === Bid Optimization ===
    
    async def optimize_bids(
        self,
        campaign_id: str,
        channel_performance: List[ChannelPerformance],
        target_cpa: Optional[float] = None,
        target_roas: Optional[float] = None
    ) -> BidOptimization:
        """
        Optimize bids for paid campaigns.
        
        Adjusts bids to hit target CPA or ROAS.
        
        Args:
            campaign_id: Campaign ID
            channel_performance: Performance by channel
            target_cpa: Target cost per acquisition
            target_roas: Target return on ad spend
            
        Returns:
            BidOptimization with adjustments
        """
        adjustments = {}
        
        for channel in channel_performance:
            current_cpa = channel.cpa
            current_roas = channel.roas
            
            if target_cpa and current_cpa > 0 and current_cpa != float('inf'):
                # Adjust to hit CPA target
                ratio = target_cpa / current_cpa
                # Limit adjustment to +/- 30%
                adjustment = max(0.7, min(1.3, ratio))
                adjustments[channel.channel_id] = adjustment
                
            elif target_roas and current_roas > 0:
                # Adjust to hit ROAS target
                ratio = current_roas / target_roas
                # Inverse: if ROAS is high, we can increase bids
                adjustment = max(0.7, min(1.3, ratio))
                adjustments[channel.channel_id] = adjustment
            else:
                # No adjustment
                adjustments[channel.channel_id] = 1.0
        
        confidence = 0.7 if (target_cpa or target_roas) else 0.5
        
        logger.info(f"Bid optimization for campaign {campaign_id}: {adjustments}")
        
        return BidOptimization(
            bid_adjustments=adjustments,
            target_cpa=target_cpa,
            target_roas=target_roas,
            confidence=confidence
        )
    
    # === Auto-Optimization Loop ===
    
    async def run_optimization_loop(
        self,
        campaign_id: str,
        interval_minutes: int = 60
    ):
        """
        Continuous optimization loop.
        
        Runs every interval to optimize campaign.
        
        Args:
            campaign_id: Campaign ID
            interval_minutes: Minutes between optimization runs
        """
        logger.info(f"Starting optimization loop for campaign {campaign_id} "
                   f"(interval: {interval_minutes} minutes)")
        
        while True:
            try:
                await self._optimization_iteration(campaign_id)
                await asyncio.sleep(interval_minutes * 60)
            except Exception as e:
                logger.error(f"Optimization iteration failed: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _optimization_iteration(self, campaign_id: str):
        """Single optimization iteration."""
        logger.info(f"Running optimization iteration for campaign {campaign_id}")
        
        # 1. Collect performance data
        # This would fetch from analytics/attribution systems
        
        # 2. Analyze trends
        
        # 3. Make optimization decisions
        
        # 4. Apply changes
        
        # 5. Log optimization actions
        log = OptimizationLog(
            timestamp=datetime.utcnow(),
            action_type="optimization_iteration",
            description=f"Optimization run for campaign {campaign_id}",
            before_state={},
            after_state={},
            expected_impact=0.0
        )
        self.optimization_logs.append(log)
        
        logger.info(f"Completed optimization iteration for campaign {campaign_id}")
    
    async def get_optimization_history(
        self,
        campaign_id: str,
        limit: int = 100
    ) -> List[OptimizationLog]:
        """Get optimization history for a campaign."""
        return self.optimization_logs[-limit:]
    
    async def enable_auto_optimization(
        self,
        campaign_id: str,
        settings: Dict[str, Any]
    ) -> Campaign:
        """Enable auto-optimization for a campaign."""
        campaign = await self.db.get(Campaign, campaign_id)
        
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        # Store settings in campaign config
        if not campaign.config:
            campaign.config = {}
        
        campaign.config['auto_optimization'] = {
            'enabled': True,
            'settings': settings,
            'enabled_at': datetime.utcnow().isoformat()
        }
        
        await self.db.commit()
        await self.db.refresh(campaign)
        
        logger.info(f"Enabled auto-optimization for campaign {campaign_id}")
        return campaign
    
    async def disable_auto_optimization(
        self,
        campaign_id: str,
        reason: Optional[str] = None
    ) -> Campaign:
        """Disable auto-optimization for a campaign."""
        campaign = await self.db.get(Campaign, campaign_id)
        
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        if campaign.config and 'auto_optimization' in campaign.config:
            campaign.config['auto_optimization']['enabled'] = False
            campaign.config['auto_optimization']['disabled_at'] = datetime.utcnow().isoformat()
            campaign.config['auto_optimization']['disabled_reason'] = reason
        
        await self.db.commit()
        await self.db.refresh(campaign)
        
        logger.info(f"Disabled auto-optimization for campaign {campaign_id}: {reason}")
        return campaign


# Import asyncio for the optimization loop
import asyncio