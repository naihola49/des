"""
Factory Layout API: generate layout from text, run Monte Carlo simulation, LLM explain.
"""
import logging
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

_root = Path(__file__).resolve().parent.parent.parent
_sim_tool = _root / "simulation_tool"
for p in (_root, _sim_tool):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
except ImportError:
    pass

from llm_layout_generator import generate_layout_from_description
from llm_simulation_explain import explain_simulation_results

try:
    from layout.model import FactoryLayout
except ImportError:
    from simulation_tool.layout.model import FactoryLayout

from simulation_engine import run_monte_carlo

logger = logging.getLogger(__name__)

_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app = FastAPI(title="Factory Layout API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


class GenerateRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)


class RunSimulationRequest(BaseModel):
    layout: dict = Field(..., description="Layout JSON: nodes and edges")
    n_trials: int = Field(30, ge=1, le=500, description="Number of Monte Carlo replications")
    duration: float = Field(100.0, gt=0, le=10000, description="Simulation time per run")
    explain: bool = Field(True, description="Whether to get LLM explanation of results")


def _layout_summary(layout: FactoryLayout) -> str:
    parts = []
    for n in layout.nodes:
        parts.append(f"- {n.id} ({n.type.value}): {n.label}")
    parts.append("Edges: " + ", ".join(f"{e.from_id}→{e.to_id}" for e in layout.edges))
    return "\n".join(parts)


@app.post("/api/generate-layout")
def api_generate_layout(body: GenerateRequest):
    text = (body.description or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="description is required")
    try:
        layout = generate_layout_from_description(text)
        return layout.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Layout generation failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/run-simulation")
def api_run_simulation(body: RunSimulationRequest):
    """Run Monte Carlo on the layout, optionally get LLM explanation of stats and bottlenecks."""
    try:
        layout = FactoryLayout.from_dict(body.layout)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid layout: {e}")

    if not layout.nodes or not layout.source_ids():
        raise HTTPException(status_code=400, detail="Layout must have at least one source")

    try:
        results = run_monte_carlo(
            layout,
            duration=body.duration,
            n_replications=body.n_trials,
            seed=42,
        )
    except Exception as e:
        logger.exception("Simulation failed")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")

    out = {
        "results": {
            "n_replications": results["n_replications"],
            "duration_per_run": results["duration_per_run"],
            "throughput_mean": results["throughput_mean"],
            "throughput_std": results["throughput_std"],
            "throughput_5pct": results["throughput_5pct"],
            "throughput_50pct": results["throughput_50pct"],
            "throughput_95pct": results["throughput_95pct"],
            "cycle_time_mean": results["cycle_time_mean"],
            "cycle_time_std": results["cycle_time_std"],
            "cycle_time_5pct": results["cycle_time_5pct"],
            "cycle_time_50pct": results["cycle_time_50pct"],
            "cycle_time_95pct": results["cycle_time_95pct"],
            "total_completed_mean": results["total_completed_mean"],
            "total_completed_std": results["total_completed_std"],
        },
        "explanation": None,
    }

    if body.explain:
        try:
            summary = _layout_summary(layout)
            out["explanation"] = explain_simulation_results(summary, results)
        except Exception as e:
            logger.warning("LLM explain failed: %s", e)
            out["explanation"] = f"Could not generate insights: {e}"

    return out


@app.get("/api/health")
def health():
    return {"status": "ok"}
