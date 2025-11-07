"""
Workload Analyzer - Intel Simulation Service Analysis Platform

An intelligent workload analysis platform that integrates with Intel Simulation Service (ISS)
to provide AI-powered insights for workload optimization, compilation improvements,
and simulation configuration tuning.
"""

__version__ = "0.1.0"
__author__ = "Gabriel Briones"
__email__ = "gabrielbriones@intel.com"
__description__ = "Intel Simulation Service Workload Analysis Platform"

from workload_analyzer.config import settings
from workload_analyzer.main import app

__all__ = ["app", "settings", "__version__"]
