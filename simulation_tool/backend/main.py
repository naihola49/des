"""
Minimal API for the factory layout designer frontend.
- POST /api/generate-layout: generate layout from natural language (uses OPENAI_API_KEY from .env).
Secrets stay server-side only; never accept API keys from the client.
"""
import logging
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add repo root and simulation_tool so we can import layout and llm_layout_generator
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

logger = logging.getLogger(__name__)

# CORS: restrict to known origins. In production set CORS_ORIGINS env (comma-separated).
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
    """Request body for layout generation. Description is length-limited to avoid abuse."""
    description: str = Field(..., min_length=1, max_length=2000)


@app.post("/api/generate-layout")
def api_generate_layout(body: GenerateRequest):
    """Generate a factory layout from a natural-language description. API key is server-side only."""
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


@app.get("/api/health")
def health():
    return {"status": "ok"}
