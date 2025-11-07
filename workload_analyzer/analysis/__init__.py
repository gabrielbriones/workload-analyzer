"""Analysis modules for workload intelligence."""

from .custom_analyzer import *
from .job_insights import *
from .performance_analyzer import *
from .platform_optimizer import *
from .trend_analyzer import *

__all__ = [
    # Performance analysis
    "PerformanceAnalyzer",
    "PerformanceMetrics",
    # Platform optimization
    "PlatformOptimizer",
    "OptimizationRecommendation",
    # Job insights
    "JobInsightsAnalyzer",
    "JobInsight",
    # Trend analysis
    "TrendAnalyzer",
    "TrendData",
    # Custom analysis
    "CustomAnalyzer",
    "AnalysisQuery",
]
