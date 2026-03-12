"""
Factory layout: the graph that defines "factory."

Design (DAG) -> Simulation (DES)

Nodes:
source: no incoming edges, generates jobs at random times.
station: incoming + outgoing edges. holds job for random processing time, then sends along outgoing edge (or to rework via probabilistic edge).
buffer: incoming + outgoing edges. FIFO queue.
sink: incoming edges. signals completion of job.
rework: receives jobs from stations (when a probabilistic "rework" edge is chosen). Feeds them back into a station. Optional params: delay (mean time before sending back).
"""

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class NodeType(str, Enum):
    """
    Node types in the factory graph. Rework nodes receive jobs via probabilistic
    edges from stations and send them back into processing (same or another station).
    """
    SOURCE = "source"
    STATION = "station"
    MANUAL = "manual"
    BUFFER = "buffer"
    SINK = "sink"
    REWORK = "rework"


@dataclass
class Node:
    """
    One node in the factory layout (a source, station, buffer, or sink).

    - id:       Unique string (e.g. "station_1", "buffer_a"). Used by edges.
    - type:     NodeType — determines behavior in the DES.
    - label:    Human-readable name (e.g. "Assembly").
    - params:   Type-specific settings. Examples:
      source  → {"distribution": "exponential", "mean": 2.0}
      station → {"distribution": "gamma", "mean": 5.0, "cv": 0.5}
      manual  → {
                   "distribution": "weibull",
                   "shape": 1.5,
                   "base_scale": 1.0,
                   "fatigue_rate": 0.1,
                   "break_interval_hours": 2.0,
                   "break_duration": 0.25,
                 }
      buffer  → {"capacity": 10}  or {} for infinite
      sink    → {}
      rework  → {} or {"delay": 1.0} for mean delay before sending back
    - x, y:     Position on the canvas (for the drag-and-drop UI). The DES
                ignores these; they're only so the layout looks right when
                you reopen the file.
    """
    id: str
    type: NodeType
    label: str
    params: Dict[str, Any] = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-friendly dict (for save_layout)."""
        return {
            "id": self.id,
            "type": self.type.value,
            "label": self.label,
            "params": self.params,
            "x": self.x,
            "y": self.y,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Node":
        """Deserialize from dict (for load_layout)."""
        return cls(
            id=d["id"],
            type=NodeType(d["type"]),
            label=d.get("label", d["id"]),
            params=d.get("params", {}),
            x=float(d.get("x", 0)),
            y=float(d.get("y", 0)),
        )


@dataclass
class Edge:
    """
    A directed connection from one node to another.

    - from_id:      Node id that sends jobs (e.g. a station or source).
    - to_id:       Node id that receives jobs (e.g. a buffer or sink).
    - probability: Optional. If the source node has multiple outgoing edges,
                   we use these to choose one (e.g. 0.9 to "next_station",
                   0.1 to "rework_station"). If omitted or 1.0, treat as
                   deterministic when there's only one outgoing edge.

    The DES will use edges to move jobs: when a job leaves a node, we look
    at that node's outgoing edges and decide the next node (by probability
    if present).
    """
    from_id: str
    to_id: str
    probability: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"from": self.from_id, "to": self.to_id}
        if self.probability is not None:
            out["probability"] = self.probability
        return out

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Edge":
        return cls(
            from_id=d["from"],
            to_id=d["to"],
            probability=d.get("probability"),
        )


@dataclass
class FactoryLayout:
    """
    The full factory graph: all nodes and all edges.

    This is the single "design" object:
    - The UI (canvas) builds this when the user saves.
    - The DES loads this and runs the factory.

    Validation (optional): we could check that every edge "from" and "to"
    refers to an existing node id, that sources have no incoming edges,
    sinks have no outgoing edges, etc. For now we keep the structure simple.
    """

    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FactoryLayout":
        nodes = [Node.from_dict(n) for n in d.get("nodes", [])]
        edges = [Edge.from_dict(e) for e in d.get("edges", [])]
        return cls(nodes=nodes, edges=edges)

    def node_by_id(self, id: str) -> Optional[Node]:
        """Look up a node by id (handy for the DES when routing)."""
        for n in self.nodes:
            if n.id == id:
                return n
        return None

    def edges_from(self, node_id: str) -> List[Edge]:
        """All edges that start at this node (outgoing). DES uses this to route jobs."""
        return [e for e in self.edges if e.from_id == node_id]

    def edges_to(self, node_id: str) -> List[Edge]:
        """All edges that end at this node (incoming)."""
        return [e for e in self.edges if e.to_id == node_id]

    def source_ids(self) -> List[str]:
        """Node ids that have no incoming edges — where jobs enter the system."""
        all_ids = {n.id for n in self.nodes}
        have_incoming = {e.to_id for e in self.edges}
        return [nid for nid in all_ids if nid not in have_incoming]

    def sink_ids(self) -> List[str]:
        """Node ids that have no outgoing edges — where jobs leave the system."""
        all_ids = {n.id for n in self.nodes}
        have_outgoing = {e.from_id for e in self.edges}
        return [nid for nid in all_ids if nid not in have_outgoing]

    def sample_next_node(self, node_id: str, rng: Any) -> Optional[str]:
        """
        Given a node id, sample the next node by outgoing edge probabilities.
        Used by the DES for routing (including rework: station -> rework or next;
        rework -> station). If probabilities are missing, they are treated as
        equal; if only one edge, that edge is chosen.
        """
        edges = self.edges_from(node_id)
        if not edges:
            return None
        probs = [e.probability if e.probability is not None else 1.0 for e in edges]
        total = sum(probs)
        if total <= 0:
            return edges[0].to_id
        r = rng.random() * total
        for e, p in zip(edges, probs):
            r -= p
            if r <= 0:
                return e.to_id
        return edges[-1].to_id


def save_layout(layout: FactoryLayout, path: Union[str, Path]) -> None:
    """Write the layout to a JSON file (e.g. from the canvas save button)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(layout.to_dict(), f, indent=2)


def load_layout(path: Union[str, Path]) -> FactoryLayout:
    """Read a layout from a JSON file (e.g. when starting the DES or reopening the canvas)."""
    with open(path) as f:
        d = json.load(f)
    return FactoryLayout.from_dict(d)
