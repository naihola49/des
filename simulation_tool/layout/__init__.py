"""
Factory layout (graph) model for the drag-and-drop designer.

This is the *design* layer: nodes (source, station, buffer, sink) and edges.
The same graph is saved by the canvas and loaded by the DES — one format, two uses.
"""

from .model import (
    NodeType,
    Node,
    Edge,
    FactoryLayout,
    load_layout,
    save_layout,
)

__all__ = [
    "NodeType",
    "Node",
    "Edge",
    "FactoryLayout",
    "load_layout",
    "save_layout",
]
