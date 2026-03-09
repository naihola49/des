"""
Monte Carlo runner for the layout-based DES.

Runs N independent replications of the layout simulation with different seeds,
then aggregates results (mean, std, percentiles) for throughput and cycle time.
"""

from typing import Any, Dict, List, Optional

import numpy as np

from .layout_des import LayoutSimulator

try:
    from layout.model import FactoryLayout
except ImportError:
    from simulation_tool.layout.model import FactoryLayout


def run_monte_carlo(
    layout: FactoryLayout,
    duration: float,
    n_replications: int = 100,
    warmup: float = 0.0,
    seed: Optional[int] = None,
    percentiles: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Run N replications of the layout DES with seeds 0..N-1 (or derived from seed),
    then aggregate metrics.

    Args:
        layout: Factory layout (graph) to simulate.
        duration: Simulation time per replication.
        n_replications: Number of independent runs.
        warmup: Warmup period to exclude per run (future use).
        seed: Base seed; replication i uses seed + i (or None for no fixed seed).
        percentiles: List of percentiles to compute (e.g. [5, 50, 95]). Default [5, 50, 95].

    Returns:
        Dict with:
          - throughput_mean, throughput_std, throughput_5pct, throughput_50pct, throughput_95pct
          - cycle_time_mean, cycle_time_std, cycle_time_5pct, cycle_time_50pct, cycle_time_95pct
          - total_completed_mean, total_completed_std
          - replications: list of per-run results (optional, for debugging)
    """
    if percentiles is None:
        percentiles = [5.0, 50.0, 95.0]

    throughputs: List[float] = []
    cycle_times: List[float] = []
    totals: List[int] = []
    per_run: List[Dict[str, Any]] = []

    for i in range(n_replications):
        rep_seed = (seed + i) if seed is not None else None
        sim = LayoutSimulator(layout)
        res = sim.run(duration=duration, seed=rep_seed, warmup=warmup)
        throughputs.append(res["throughput"])
        cycle_times.append(res["avg_cycle_time"])
        totals.append(res["total_completed"])
        per_run.append(res)

    throughputs_arr = np.array(throughputs)
    cycle_arr = np.array(cycle_times)
    totals_arr = np.array(totals, dtype=float)

    out: Dict[str, Any] = {
        "n_replications": n_replications,
        "duration_per_run": duration,
        "throughput_mean": float(np.mean(throughputs_arr)),
        "throughput_std": float(np.std(throughputs_arr)) if n_replications > 1 else 0.0,
        "cycle_time_mean": float(np.mean(cycle_arr)),
        "cycle_time_std": float(np.std(cycle_arr)) if n_replications > 1 else 0.0,
        "total_completed_mean": float(np.mean(totals_arr)),
        "total_completed_std": float(np.std(totals_arr)) if n_replications > 1 else 0.0,
    }

    for p in percentiles:
        out[f"throughput_{int(p)}pct"] = float(np.percentile(throughputs_arr, p))
        out[f"cycle_time_{int(p)}pct"] = float(np.percentile(cycle_arr, p))

    out["replications"] = per_run
    return out
