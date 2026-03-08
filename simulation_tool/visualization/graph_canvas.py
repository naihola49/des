"""
Interactive graph canvas for the factory layout.

Renders a FactoryLayout using each node's stored (x, y). When you add a node,
only that node gets a new position (to the right); existing nodes stay put.
If every node is at (0,0), a type-based fallback layout is used so they don't overlap.
"""

from typing import Dict, Optional, Tuple

import json as _json

# Layout model: work whether run from repo root or simulation_tool
try:
    from layout.model import FactoryLayout, NodeType, Node, Edge
except ImportError:
    from simulation_tool.layout.model import FactoryLayout, NodeType, Node, Edge


def _node_color(node: Node) -> str:
    """Distinct color per node type so the palette matches the canvas."""
    return {
        NodeType.SOURCE: "#4CAF50",
        NodeType.STATION: "#2196F3",
        NodeType.BUFFER: "#FF9800",
        NodeType.SINK: "#9C27B0",
    }[node.type]


# Column order for fallback when all positions are (0,0)
_TYPE_ORDER = (NodeType.SOURCE, NodeType.STATION, NodeType.BUFFER, NodeType.SINK)


def _compute_positions_fallback(layout: FactoryLayout, col_spacing: float = 220.0, row_spacing: float = 100.0) -> Dict[str, Tuple[float, float]]:
    """Only used when every node has (0,0) so we don't draw everything on top of each other."""
    by_type: Dict[NodeType, list] = {t: [] for t in _TYPE_ORDER}
    for node in layout.nodes:
        by_type[node.type].append(node)
    for nodes in by_type.values():
        nodes.sort(key=lambda n: n.id)
    positions: Dict[str, Tuple[float, float]] = {}
    x0, y0 = 80.0, 80.0
    for col_idx, node_type in enumerate(_TYPE_ORDER):
        for row_idx, node in enumerate(by_type[node_type]):
            positions[node.id] = (x0 + col_idx * col_spacing, y0 + row_idx * row_spacing)
    return positions


def layout_to_pyvis_html(
    layout: FactoryLayout,
    height: int = 580,
    width: Optional[str] = None,
    physics: bool = False,
) -> str:
    """
    Render the layout using each node's stored (x, y). Existing nodes are never
    moved by the renderer; only a new node (added in the sidebar) gets a new position.
    If every node is at (0,0), we use a type-based fallback so they don't overlap.
    """
    try:
        from pyvis.network import Network
    except ImportError:
        return (
            "<div style='padding:2rem;font-family:sans-serif'>"
            "Install <b>pyvis</b> to show the graph: <code>pip install pyvis</code>"
            "</div>"
        )
    net = Network(
        height=f"{height}px",
        width=width or "100%",
        directed=True,
        heading="",
    )
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=120,
        spring_strength=0.001,
        damping=0.09,
    )
    options = {
        "physics": {"enabled": physics},
        "nodes": {"font": {"size": 14}},
        "edges": {"arrows": "to"},
    }
    net.set_options(_json.dumps(options))

    use_stored = layout.nodes and not all(n.x == 0 and n.y == 0 for n in layout.nodes)
    if use_stored:
        for node in layout.nodes:
            x, y = node.x, node.y
            net.add_node(
                node.id,
                label=node.label or node.id,
                title=f"{node.type.value}: {node.id}",
                x=x,
                y=y,
                color=_node_color(node),
            )
    else:
        positions = _compute_positions_fallback(layout)
        for node in layout.nodes:
            x, y = positions.get(node.id, (100.0, 100.0))
            net.add_node(
                node.id,
                label=node.label or node.id,
                title=f"{node.type.value}: {node.id}",
                x=x,
                y=y,
                color=_node_color(node),
            )

    for edge in layout.edges:
        net.add_edge(edge.from_id, edge.to_id, title=str(edge.probability or 1.0))

    return net.generate_html()


def get_position_for_new_node(layout: FactoryLayout, spacing: float = 150.0) -> Tuple[float, float]:
    """
    Position for a newly added node so it doesn't overlap existing ones.
    Puts the new node to the right of the rightmost node (or below if only one column).
    Existing nodes are never moved; only this return value is used for the new node.
    """
    if not layout.nodes:
        return (100.0, 100.0)
    xs = [n.x for n in layout.nodes]
    ys = [n.y for n in layout.nodes]
    max_x = max(xs)
    min_y = min(ys)
    return (max_x + spacing, min_y)


def get_next_grid_position(layout: FactoryLayout, spacing: float = 120.0) -> Tuple[float, float]:
    """Alias for get_position_for_new_node so existing callers keep working."""
    return get_position_for_new_node(layout, spacing)
