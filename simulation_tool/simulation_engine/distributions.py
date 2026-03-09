"""
Sample from layout params (exponential, gamma) for DES.
Expects a numpy RNG (e.g. np.random.default_rng(seed)) for reproducibility.
"""
from typing import Any, Dict

import numpy as np


def sample_time(params: Dict[str, Any], rng: np.random.Generator) -> float:
    """
    Sample a positive time from the distribution described in params.
    - exponential: params["mean"]
    - gamma: params["mean"], params["cv"] (coefficient of variation)
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

    t = rng.exponential(mean)
    return max(1e-6, float(t))
