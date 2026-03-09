"""
Layout-driven simulation engine: DES + Monte Carlo.

- LayoutSimulator: one replication on a FactoryLayout.
- run_monte_carlo: N replications with aggregated metrics.
- sample_time: sample from layout params (exponential, gamma).
"""

from .layout_des import LayoutSimulator
from .monte_carlo import run_monte_carlo
from .distributions import sample_time

__all__ = [
    "LayoutSimulator",
    "run_monte_carlo",
    "sample_time",
]
