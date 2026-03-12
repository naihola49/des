"""
Sample from layout params (exponential, gamma, weibull) for DES.
Expects a numpy RNG (e.g. np.random.default_rng(seed)) for reproducibility.
"""
from typing import Any, Dict

import numpy as np


def sample_time(params: Dict[str, Any], rng: np.random.Generator) -> float:
    """
    Sample a positive time from the distribution described in params.

    Supported:
    - exponential: params["mean"]
    - gamma:       params["mean"], params["cv"] (coefficient of variation)
    - weibull:     params["shape"], params["scale"]

    Returns a positive float (clamped to a small epsilon if needed).
    """
    if not params:
        return 0.0

    dist = (params.get("distribution") or "exponential").lower()
    mean = float(params.get("mean", 1.0))
    if mean <= 0:
        mean = 1.0

    if dist == "exponential":
        t = rng.exponential(mean)
        return max(1e-6, float(t))

    if dist == "gamma":
        cv = float(params.get("cv", 0.5))
        if cv <= 0:
            return max(1e-6, mean)
        shape = 1.0 / (cv * cv)
        scale = mean / shape
        t = rng.gamma(shape, scale)
        return max(1e-6, float(t))

    if dist == "weibull":
        shape = float(params.get("shape", 1.5))
        scale = float(params.get("scale", mean))
        if shape <= 0 or scale <= 0:
            # Fallback to an exponential with the given mean if parameters are invalid.
            t = rng.exponential(mean)
            return max(1e-6, float(t))
        # numpy's weibull draws with scale=1; multiply by scale.
        t = rng.weibull(shape) * scale
        return max(1e-6, float(t))

    # Default: exponential as a safe fallback.
    t = rng.exponential(mean)
    return max(1e-6, float(t))


def sample_manual_weibull_time(
    params: Dict[str, Any],
    hours_since_last_break: float,
    rng: np.random.Generator,
) -> float:
    """
    Specialized sampler for manual-processing nodes.

    The processing time follows a Weibull distribution whose scale parameter
    grows with hours_since_last_break to capture operator fatigue.

    Expected params:
      - shape:        Weibull shape parameter (k > 0)
      - base_scale:   Baseline scale when hours_since_last_break == 0
      - fatigue_rate: Linear growth per hour since last break (>= 0).

    scale = base_scale * (1 + fatigue_rate * hours_since_last_break)
    """
    shape = float(params.get("shape", 1.5))
    base_scale = float(params.get("base_scale", 1.0))
    fatigue_rate = float(params.get("fatigue_rate", 0.0))

    if shape <= 0 or base_scale <= 0:
        # Degenerate configuration; fall back to an exponential with mean 1.
        t = rng.exponential(1.0)
        return max(1e-6, float(t))

    h = max(0.0, float(hours_since_last_break))
    scale = base_scale * (1.0 + fatigue_rate * h)
    if scale <= 0:
        scale = 1e-6

    t = rng.weibull(shape) * scale
    return max(1e-6, float(t))
