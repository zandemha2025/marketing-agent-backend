"""
Background tasks for the Marketing Agent Platform.

This module contains Celery tasks for:
- Campaign execution
- Optimization and A/B testing
- Analytics and reporting
- Data processing
- Scheduled maintenance
"""

# Import tasks to register them with Celery
try:
    from .optimization_tasks import (
        run_experiment_analysis,
        check_experiment_winner,
        run_campaign_optimization,
        retrain_predictive_models,
        optimize_budget_allocations,
    )
    OPTIMIZATION_TASKS_AVAILABLE = True
except ImportError:
    OPTIMIZATION_TASKS_AVAILABLE = False

# Import campaign tasks
try:
    from .campaign_tasks import (
        execute_campaign_task,
        get_campaign_progress,
        generate_copy_task,
        generate_image_task,
    )
    CAMPAIGN_TASKS_AVAILABLE = True
except ImportError:
    CAMPAIGN_TASKS_AVAILABLE = False

__all__ = []

if OPTIMIZATION_TASKS_AVAILABLE:
    __all__.extend([
        "run_experiment_analysis",
        "check_experiment_winner",
        "run_campaign_optimization",
        "retrain_predictive_models",
        "optimize_budget_allocations",
    ])

if CAMPAIGN_TASKS_AVAILABLE:
    __all__.extend([
        "execute_campaign_task",
        "get_campaign_progress",
        "generate_copy_task",
        "generate_image_task",
    ])