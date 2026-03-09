"""
Use an LLM to explain Monte Carlo simulation results and suggest bottlenecks/insights.
"""

import json
import os
from typing import Any, Dict, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def explain_simulation_results(
    layout_summary: str,
    results: Dict[str, Any],
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Ask the LLM to explain the simulation statistics and provide bottlenecks + operational insights.

    Args:
        layout_summary: Short description of the layout (node types and flow).
        results: Monte Carlo output (throughput_mean, cycle_time_mean, etc.).
        api_key: OpenAI API key; if None, uses OPENAI_API_KEY env.
        model: Model name.

    Returns:
        Plain-text explanation (a few paragraphs).
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        return "OpenAI API key not set. Set OPENAI_API_KEY in .env to get AI-generated insights."
    if OpenAI is None:
        return "Install openai: pip install openai"

    client = OpenAI(api_key=key)
    stats = {
        "n_replications": results.get("n_replications"),
        "duration_per_run": results.get("duration_per_run"),
        "throughput": {
            "mean": results.get("throughput_mean"),
            "std": results.get("throughput_std"),
            "5th_pct": results.get("throughput_5pct"),
            "50th_pct": results.get("throughput_50pct"),
            "95th_pct": results.get("throughput_95pct"),
        },
        "cycle_time": {
            "mean": results.get("cycle_time_mean"),
            "std": results.get("cycle_time_std"),
            "5th_pct": results.get("cycle_time_5pct"),
            "50th_pct": results.get("cycle_time_50pct"),
            "95th_pct": results.get("cycle_time_95pct"),
        },
        "total_completed": {
            "mean": results.get("total_completed_mean"),
            "std": results.get("total_completed_std"),
        },
    }
    prompt = f"""You are an expert in manufacturing and factory simulation. Below are the layout summary and Monte Carlo simulation statistics for a production layout.

**Layout summary:**
{layout_summary}

**Simulation results (N replications, duration per run):**
{json.dumps(stats, indent=2)}

Write a short, clear explanation (3–5 paragraphs) that:
1. Interprets the key statistics (throughput, cycle time, variability).
2. Identifies likely bottlenecks or constraints in this layout.
3. Suggests 1–3 operational insights or improvements (e.g. buffer sizing, parallel capacity, rework impact).

Use plain language. No bullet lists unless brief. Output only the explanation text, no headings or markdown."""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800,
    )
    text = (response.choices[0].message.content or "").strip()
    return text if text else "No explanation generated."
