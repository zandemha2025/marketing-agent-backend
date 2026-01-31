"""
Multi-Armed Bandit Engine.

Implements various bandit algorithms for continuous optimization:
- Thompson Sampling (Bayesian approach)
- Upper Confidence Bound (UCB1)
- Epsilon-Greedy

Bandits balance exploration vs exploitation for optimal performance.
"""
import logging
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from scipy import stats
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ...models.experiment import Experiment, ExperimentStatus, ExperimentType
from ...models.experiment_variant import ExperimentVariant

logger = logging.getLogger(__name__)


@dataclass
class BanditVariant:
    """Bandit variant state."""
    variant_id: str
    name: str
    successes: int
    failures: int
    pulls: int
    traffic_percentage: float


@dataclass
class BanditRecommendation:
    """Recommendation result from bandit."""
    variant_id: str
    variant_name: str
    algorithm: str
    confidence: float
    estimated_conversion_rate: float


class BanditEngine:
    """
    Multi-armed bandit engine for continuous optimization.
    
    Unlike traditional A/B tests that run for a fixed period,
    bandits continuously learn and adapt, sending more traffic
    to better-performing variants while still exploring alternatives.
    """
    
    def __init__(self, db_session: AsyncSession):
        """Initialize with database session."""
        self.db = db_session
    
    # === Bandit Algorithms ===
    
    def thompson_sampling(
        self,
        variants: List[BanditVariant]
    ) -> str:
        """
        Thompson Sampling algorithm.
        
        Samples from Beta distribution for each variant.
        Returns variant with highest sample.
        
        This is a Bayesian approach that naturally balances
        exploration (uncertain variants) vs exploitation
        (high-performing variants).
        
        Args:
            variants: List of bandit variants with success/failure counts
            
        Returns:
            Selected variant_id
        """
        samples = []
        
        for variant in variants:
            # Beta distribution parameters
            alpha = variant.successes + 1  # Add 1 for uniform prior
            beta = variant.failures + 1
            
            # Sample from Beta distribution
            sample = np.random.beta(alpha, beta)
            samples.append((variant.variant_id, sample))
            
            logger.debug(f"Thompson sample for {variant.name}: {sample:.4f}")
        
        # Select variant with highest sample
        selected = max(samples, key=lambda x: x[1])
        
        logger.info(f"Thompson Sampling selected variant {selected[0]} (sample: {selected[1]:.4f})")
        return selected[0]
    
    def upper_confidence_bound(
        self,
        variants: List[BanditVariant],
        total_pulls: int
    ) -> str:
        """
        UCB1 algorithm.
        
        Balances exploration vs exploitation using confidence bounds.
        Selects variant with highest upper confidence bound.
        
        Formula: mean + sqrt(2 * ln(total_pulls) / pulls)
        
        Args:
            variants: List of bandit variants
            total_pulls: Total number of pulls across all variants
            
        Returns:
            Selected variant_id
        """
        ucb_scores = []
        
        for variant in variants:
            if variant.pulls == 0:
                # Always try unexplored variants first
                ucb = float('inf')
            else:
                # Calculate mean reward
                mean_reward = variant.successes / variant.pulls
                
                # Calculate confidence interval
                confidence = np.sqrt(2 * np.log(total_pulls) / variant.pulls)
                
                # UCB score
                ucb = mean_reward + confidence
            
            ucb_scores.append((variant.variant_id, ucb))
            
            logger.debug(f"UCB score for {variant.name}: {ucb:.4f}")
        
        # Select variant with highest UCB
        selected = max(ucb_scores, key=lambda x: x[1])
        
        logger.info(f"UCB selected variant {selected[0]} (score: {selected[1]:.4f})")
        return selected[0]
    
    def epsilon_greedy(
        self,
        variants: List[BanditVariant],
        epsilon: float = 0.1
    ) -> str:
        """
        Epsilon-greedy algorithm.
        
        Explores with probability epsilon, exploits otherwise.
        
        Args:
            variants: List of bandit variants
            epsilon: Exploration probability (0.0 to 1.0)
            
        Returns:
            Selected variant_id
        """
        if random.random() < epsilon:
            # Explore: random selection
            selected = random.choice(variants)
            logger.info(f"Epsilon-greedy exploring: selected {selected.variant_id}")
            return selected.variant_id
        else:
            # Exploit: select best performing
            best = max(variants, key=lambda v: v.successes / v.pulls if v.pulls > 0 else 0)
            logger.info(f"Epsilon-greedy exploiting: selected {best.variant_id}")
            return best.variant_id
    
    def softmax(
        self,
        variants: List[BanditVariant],
        temperature: float = 0.1
    ) -> str:
        """
        Softmax (Boltzmann) selection.
        
        Selects variants probabilistically based on their estimated value.
        Higher temperature = more exploration.
        
        Args:
            variants: List of bandit variants
            temperature: Exploration temperature (higher = more random)
            
        Returns:
            Selected variant_id
        """
        # Calculate estimated values
        values = []
        for variant in variants:
            if variant.pulls == 0:
                value = 0.5  # Prior belief
            else:
                value = variant.successes / variant.pulls
            values.append(value)
        
        # Softmax probabilities
        exp_values = np.exp(np.array(values) / temperature)
        probabilities = exp_values / np.sum(exp_values)
        
        # Select based on probabilities
        selected_idx = np.random.choice(len(variants), p=probabilities)
        selected = variants[selected_idx]
        
        logger.info(f"Softmax selected variant {selected.variant_id} (prob: {probabilities[selected_idx]:.4f})")
        return selected.variant_id
    
    # === Database Integration ===
    
    async def get_recommendation(
        self,
        experiment_id: str,
        algorithm: str = "thompson_sampling",
        epsilon: float = 0.1,
        temperature: float = 0.1
    ) -> BanditRecommendation:
        """
        Get recommended variant for next user.
        
        Args:
            experiment_id: Bandit experiment ID
            algorithm: Algorithm to use (thompson_sampling, ucb, epsilon_greedy, softmax)
            epsilon: For epsilon-greedy algorithm
            temperature: For softmax algorithm
            
        Returns:
            BanditRecommendation with selected variant
        """
        # Get experiment
        result = await self.db.execute(
            select(Experiment).where(
                and_(
                    Experiment.id == experiment_id,
                    Experiment.experiment_type == ExperimentType.BANDIT,
                    Experiment.status == ExperimentStatus.RUNNING
                )
            )
        )
        experiment = result.scalar_one_or_none()
        
        if not experiment:
            raise ValueError(f"Bandit experiment {experiment_id} not found or not running")
        
        # Get variants
        result = await self.db.execute(
            select(ExperimentVariant).where(
                ExperimentVariant.experiment_id == experiment_id
            )
        )
        db_variants = result.scalars().all()
        
        if not db_variants:
            raise ValueError(f"No variants found for experiment {experiment_id}")
        
        # Convert to bandit variants
        variants = [
            BanditVariant(
                variant_id=v.id,
                name=v.name,
                successes=v.bandit_successes,
                failures=v.bandit_failures,
                pulls=v.bandit_pulls,
                traffic_percentage=v.traffic_percentage
            )
            for v in db_variants
        ]
        
        # Calculate total pulls
        total_pulls = sum(v.pulls for v in variants)
        
        # Select algorithm
        if algorithm == "thompson_sampling":
            selected_id = self.thompson_sampling(variants)
        elif algorithm == "ucb":
            selected_id = self.upper_confidence_bound(variants, total_pulls)
        elif algorithm == "epsilon_greedy":
            selected_id = self.epsilon_greedy(variants, epsilon)
        elif algorithm == "softmax":
            selected_id = self.softmax(variants, temperature)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        # Get selected variant details
        selected_variant = next(v for v in db_variants if v.id == selected_id)
        
        # Update pull count
        selected_variant.bandit_pulls += 1
        await self.db.commit()
        
        # Calculate confidence
        if selected_variant.bandit_pulls > 0:
            estimated_rate = selected_variant.bandit_successes / selected_variant.bandit_pulls
            # Confidence based on number of samples (more samples = higher confidence)
            confidence = min(selected_variant.bandit_pulls / 1000, 1.0)
        else:
            estimated_rate = 0.5
            confidence = 0.0
        
        return BanditRecommendation(
            variant_id=selected_id,
            variant_name=selected_variant.name,
            algorithm=algorithm,
            confidence=confidence,
            estimated_conversion_rate=estimated_rate
        )
    
    async def update_variant_performance(
        self,
        variant_id: str,
        reward: float
    ) -> ExperimentVariant:
        """
        Update bandit with new observation.
        
        Args:
            variant_id: Variant ID
            reward: Reward value (0.0 to 1.0, or binary 0/1)
            
        Returns:
            Updated variant
        """
        variant = await self.db.get(ExperimentVariant, variant_id)
        
        if not variant:
            raise ValueError(f"Variant {variant_id} not found")
        
        # Update bandit parameters
        if reward > 0:
            variant.bandit_successes += 1
        else:
            variant.bandit_failures += 1
        
        await self.db.commit()
        await self.db.refresh(variant)
        
        logger.info(f"Updated variant {variant_id}: reward={reward}, "
                   f"successes={variant.bandit_successes}, failures={variant.bandit_failures}")
        
        return variant
    
    async def batch_update_performance(
        self,
        updates: List[Dict[str, Any]]
    ) -> List[ExperimentVariant]:
        """
        Batch update multiple variants.
        
        Args:
            updates: List of dicts with 'variant_id' and 'reward'
            
        Returns:
            List of updated variants
        """
        updated = []
        
        for update in updates:
            variant = await self.update_variant_performance(
                update['variant_id'],
                update['reward']
            )
            updated.append(variant)
        
        return updated
    
    # === Utility Methods ===
    
    async def get_variant_stats(
        self,
        experiment_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all variants in a bandit experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Dict mapping variant_id to statistics
        """
        result = await self.db.execute(
            select(ExperimentVariant).where(
                ExperimentVariant.experiment_id == experiment_id
            )
        )
        variants = result.scalars().all()
        
        stats = {}
        for variant in variants:
            total = variant.bandit_successes + variant.bandit_failures
            conversion_rate = variant.bandit_successes / total if total > 0 else 0.0
            
            # Calculate confidence interval for conversion rate
            if total > 0:
                p = conversion_rate
                z = 1.96  # 95% confidence
                se = np.sqrt(p * (1 - p) / total)
                ci_lower = max(0, p - z * se)
                ci_upper = min(1, p + z * se)
            else:
                ci_lower = ci_upper = 0.0
            
            stats[variant.id] = {
                "name": variant.name,
                "successes": variant.bandit_successes,
                "failures": variant.bandit_failures,
                "pulls": variant.bandit_pulls,
                "conversion_rate": conversion_rate,
                "confidence_interval": (ci_lower, ci_upper),
                "is_control": variant.is_control,
                "traffic_percentage": variant.traffic_percentage
            }
        
        return stats
    
    async def reset_bandit(
        self,
        experiment_id: str
    ) -> List[ExperimentVariant]:
        """
        Reset bandit to initial state (clear all observations).
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            List of reset variants
        """
        result = await self.db.execute(
            select(ExperimentVariant).where(
                ExperimentVariant.experiment_id == experiment_id
            )
        )
        variants = result.scalars().all()
        
        for variant in variants:
            variant.bandit_successes = 0
            variant.bandit_failures = 0
            variant.bandit_pulls = 0
        
        await self.db.commit()
        
        logger.info(f"Reset bandit experiment {experiment_id}")
        return variants
    
    def calculate_regret(
        self,
        variants: List[BanditVariant],
        selected_variant_id: str
    ) -> float:
        """
        Calculate regret for a selection.
        
        Regret is the difference between the best possible reward
        and the actual reward received.
        
        Args:
            variants: All variants
            selected_variant_id: The variant that was selected
            
        Returns:
            Regret value (0 = no regret, higher = more regret)
        """
        # Find best empirical mean
        best_mean = max(
            v.successes / v.pulls if v.pulls > 0 else 0
            for v in variants
        )
        
        # Get selected variant mean
        selected = next(v for v in variants if v.variant_id == selected_variant_id)
        selected_mean = selected.successes / selected.pulls if selected.pulls > 0 else 0
        
        regret = best_mean - selected_mean
        
        return max(0, regret)