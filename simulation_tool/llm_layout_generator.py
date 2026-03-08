"""
Generate a factory layout from a natural-language description using an LLM.

The LLM is prompted with the layout schema and an example, and returns JSON
that we parse into a FactoryLayout. Requires OPENAI_API_KEY (env or passed in).
"""

import json
import os
import re
from typing import Optional

try:
    from layout.model import FactoryLayout, NodeType
except ImportError:
    from simulation_tool.layout.model import FactoryLayout, NodeType


EXAMPLE_LAYOUT = {
    "nodes": [
        {"id": "source_1", "type": "source", "label": "Raw material", "params": {"distribution": "exponential", "mean": 2.0}, "x": 50, "y": 100},
        {"id": "station_1", "type": "station", "label": "Assembly", "params": {"distribution": "gamma", "mean": 5.0, "cv": 0.5}, "x": 200, "y": 100},
        {"id": "buffer_1", "type": "buffer", "label": "WIP buffer", "params": {"capacity": 10}, "x": 350, "y": 100},
        {"id": "station_2", "type": "station", "label": "Test", "params": {"distribution": "gamma", "mean": 3.0, "cv": 0.5}, "x": 500, "y": 100},
        {"id": "rework_1", "type": "rework", "label": "Rework", "params": {"delay": 1.0}, "x": 500, "y": 220},
        {"id": "sink_1", "type": "sink", "label": "Finished good", "params": {}, "x": 650, "y": 100},
    ],
    "edges": [
        {"from": "source_1", "to": "station_1"},
        {"from": "station_1", "to": "buffer_1"},
        {"from": "buffer_1", "to": "station_2"},
        {"from": "station_2", "to": "sink_1", "probability": 0.9},
        {"from": "station_2", "to": "rework_1", "probability": 0.1},
        {"from": "rework_1", "to": "station_1"},
    ],
}

SYSTEM_PROMPT = """You are a factory layout assistant. Given a short description of a factory or production line, you output a single JSON object that represents the layout.

The JSON must have exactly two keys: "nodes" and "edges".

**Nodes** is an array of objects. Each node has:
- "id": unique string (e.g. "source_1", "station_1", "rework_1", "sink_1"). Use lowercase and underscores.
- "type": one of "source", "station", "buffer", "sink", "rework"
  - source: where jobs/parts arrive (e.g. raw material). No incoming edges.
  - station: a processing step (e.g. assembly, machining, test).
  - buffer: a queue between steps (optional capacity in params).
  - sink: where finished jobs leave. No outgoing edges.
  - rework: receives failed/rework jobs from stations (via probabilistic edges) and feeds them back into a station. Use when the user mentions rework, defects, or "send back". params: {} or {"delay": number} for mean delay before sending back.
- "label": short human-readable name (e.g. "Assembly", "Rework")
- "params": object. For source/station use {"distribution": "exponential" or "gamma", "mean": number, "cv": number for gamma}. For buffer use {"capacity": number} or {}. For sink use {}. For rework use {} or {"delay": number}.
- "x", "y": numbers for position (e.g. 50, 100, 200, ... spacing by ~150).

**Edges** is an array of objects. Each edge has:
- "from": id of the node that sends jobs
- "to": id of the node that receives jobs
- optional "probability": number between 0 and 1. When a node has multiple outgoing edges (e.g. from a station: 0.9 to next step, 0.1 to rework), include probability on each so they sum to 1.

Flow: sources have no incoming edges; sinks have no outgoing edges. Rework nodes have incoming edges from stations (with probability) and outgoing edges back to a station. Use the exact node ids in "from" and "to".

Output only the JSON object, no markdown code fence and no other text."""


def _extract_json(text: str) -> dict:
    """Try to extract a JSON object from LLM response (may be wrapped in markdown)."""
    text = text.strip()
    # Remove markdown code block if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _assign_positions_if_missing(data: dict) -> dict:
    """Ensure every node has x, y so the graph doesn't overlap. Use simple left-to-right."""
    nodes = data.get("nodes", [])
    if not nodes:
        return data
    spacing = 150
    for i, n in enumerate(nodes):
        if "x" not in n or "y" not in n:
            n["x"] = 80 + (i % 4) * spacing
            n["y"] = 80 + (i // 4) * 100
    return data


def generate_layout_from_description(
    description: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> FactoryLayout:
    """
    Call the LLM to generate a factory layout JSON from a natural-language description,
    then parse and return a FactoryLayout.

    Args:
        description: User's description of the factory (e.g. "Raw material goes to assembly, then a buffer, then testing, then out").
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
        model: Model name (default gpt-4o-mini for speed/cost).

    Returns:
        FactoryLayout with nodes and edges.

    Raises:
        ValueError: If no API key, or LLM returns invalid/unparseable JSON.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("No API key. Set OPENAI_API_KEY or pass api_key.")

    try:
        from openai import OpenAI
    except ImportError:
        raise ValueError("Install the openai package: pip install openai")

    client = OpenAI(api_key=key)
    user_content = f"""Describe the factory layout as a single JSON object with "nodes" and "edges".

Example layout:
{json.dumps(EXAMPLE_LAYOUT, indent=2)}

User description: {description}

Output only the JSON object."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = response.choices[0].message.content
    if not raw:
        raise ValueError("LLM returned empty response.")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = _extract_json(raw)

    if "nodes" not in data or "edges" not in data:
        raise ValueError("LLM response must contain 'nodes' and 'edges'.")

    data = _assign_positions_if_missing(data)
    return FactoryLayout.from_dict(data)
