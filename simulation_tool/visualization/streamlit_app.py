"""
Factory Layout Designer — drag-and-drop style UI.

Design your factory by adding nodes (Source, Station, Buffer, Sink), connecting
them with edges, and editing params. The graph is the same format the DES will
use. Save to JSON and load it when running the simulation (or here to keep editing).
"""

import json
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Run from repo root: streamlit run simulation_tool/visualization/streamlit_app.py
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Load .env from repo root so OPENAI_API_KEY is available for "Generate from description"
try:
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
except ImportError:
    pass

_sim_tool = _root / "simulation_tool"
if str(_sim_tool) not in sys.path:
    sys.path.insert(0, str(_sim_tool))

from layout.model import (
    FactoryLayout,
    Node,
    Edge,
    NodeType,
)
from visualization.graph_canvas import layout_to_pyvis_html, get_position_for_new_node
try:
    from llm_layout_generator import generate_layout_from_description
except ImportError:
    generate_layout_from_description = None


def default_params_for_type(node_type: NodeType) -> dict:
    """Sensible defaults when adding a new node."""
    if node_type == NodeType.SOURCE:
        return {"distribution": "exponential", "mean": 2.0}
    if node_type == NodeType.STATION:
        return {"distribution": "gamma", "mean": 5.0, "cv": 0.5}
    if node_type == NodeType.BUFFER:
        return {"capacity": 10}
    return {}


def init_session_layout():
    if "layout" not in st.session_state:
        st.session_state.layout = FactoryLayout(nodes=[], edges=[])
    if "next_id" not in st.session_state:
        st.session_state.next_id = 1


def main():
    st.set_page_config(
        page_title="Factory Layout Designer",
        page_icon="🏭",
        layout="wide",
    )
    init_session_layout()

    st.title("🏭 Factory Layout Designer")
    st.caption(
        "Add nodes, connect them, then Save. Or describe your factory below and generate a layout."
    )

    layout: FactoryLayout = st.session_state.layout

    # ----- Generate from description (LLM) -----
    if generate_layout_from_description is not None:
        with st.expander("✨ Generate layout from description", expanded=False):
            st.caption("Describe your factory in plain language (e.g. \"Raw material arrives, then assembly, then a buffer, then testing, then finished goods out\"). The AI will create the graph.")
            description = st.text_area(
                "Describe your factory",
                placeholder="e.g. Parts arrive at receiving, go to machining, then to a buffer, then assembly, then inspection, then shipping.",
                height=100,
                key="llm_description",
            )
            if st.button("Generate layout", type="primary", key="generate_layout_btn"):
                if not (description or "").strip():
                    st.error("Please enter a description.")
                else:
                    with st.spinner("Generating layout…"):
                        try:
                            new_layout = generate_layout_from_description(description.strip())
                            st.session_state.layout = new_layout
                            max_num = 0
                            for n in st.session_state.layout.nodes:
                                parts = n.id.rsplit("_", 1)
                                if len(parts) == 2 and parts[1].isdigit():
                                    max_num = max(max_num, int(parts[1]))
                            st.session_state.next_id = max_num + 1
                            st.success("Layout generated. You can edit it below or in the sidebar.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Generation failed: {e}")
    else:
        st.caption("Install `openai` and set OPENAI_API_KEY to enable **Generate from description**.")

    # ----- Sidebar: palette + load/save + edit -----
    with st.sidebar:
        st.header("📁 Load / Save")
        uploaded = st.file_uploader("Load layout", type=["json"], label_visibility="collapsed")
        load_clicked = st.button("Load from file", use_container_width=True, help="Load the selected file into the canvas (replaces current layout)")
        if load_clicked and uploaded is not None:
            try:
                data = json.load(uploaded)
                st.session_state.layout = FactoryLayout.from_dict(data)
                # Update next_id so new nodes don't clash with loaded ids
                max_num = 0
                for n in st.session_state.layout.nodes:
                    parts = n.id.rsplit("_", 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        max_num = max(max_num, int(parts[1]))
                st.session_state.next_id = max_num + 1
                st.success("Layout loaded.")
                st.rerun()
            except Exception as e:
                st.error(f"Load failed: {e}")

        layout_json = json.dumps(layout.to_dict(), indent=2)
        st.download_button(
            "Save layout (JSON)",
            data=layout_json,
            file_name="factory_layout.json",
            mime="application/json",
            use_container_width=True,
        )

        st.divider()
        st.header("➕ Add node")

        node_type = st.selectbox(
            "Type",
            [NodeType.SOURCE, NodeType.STATION, NodeType.BUFFER, NodeType.SINK],
            format_func=lambda x: x.value.capitalize(),
        )
        new_id = st.text_input("ID", value=f"{node_type.value}_{st.session_state.next_id}", key="new_node_id")
        new_label = st.text_input("Label", value=new_id.replace("_", " ").title(), key="new_node_label")

        if st.button("Add node", type="primary", use_container_width=True):
            if not new_id.strip():
                st.sidebar.error("ID is required.")
            elif layout.node_by_id(new_id.strip()):
                st.sidebar.error("That ID already exists.")
            else:
                x, y = get_position_for_new_node(layout)
                params = default_params_for_type(node_type)
                layout.nodes.append(
                    Node(id=new_id.strip(), type=node_type, label=new_label.strip() or new_id.strip(), params=params, x=x, y=y)
                )
                st.session_state.next_id += 1
                st.rerun()

        st.divider()
        st.header("Edges")

        node_ids = [n.id for n in layout.nodes]
        if len(node_ids) >= 2:
            from_id = st.selectbox("From", node_ids, key="edge_from")
            to_id = st.selectbox("To", node_ids, key="edge_to")
            prob = st.number_input("Probability (optional)", min_value=0.0, max_value=1.0, value=1.0, step=0.1, key="edge_prob")
            if st.button("Add edge", use_container_width=True):
                if from_id == to_id:
                    st.sidebar.error("From and To must differ.")
                elif any(e.from_id == from_id and e.to_id == to_id for e in layout.edges):
                    st.sidebar.error("Edge already exists.")
                else:
                    layout.edges.append(Edge(from_id=from_id, to_id=to_id, probability=prob if prob < 1.0 else None))
                    st.rerun()
        else:
            st.caption("Add at least 2 nodes to connect.")

        # Delete node
        st.divider()
        st.header("Edit / Delete")
        if node_ids:
            edit_id = st.selectbox("Node", node_ids, key="edit_node")
            node = layout.node_by_id(edit_id)
            if node:
                new_label_edit = st.text_input("Label", value=node.label, key="edit_label")
                if node.type in (NodeType.SOURCE, NodeType.STATION):
                    st.caption("Params (e.g. distribution, mean, cv or capacity)")
                    params_str = st.text_input("Params (JSON)", value=json.dumps(node.params, indent=0), key="edit_params")
                    try:
                        new_params = json.loads(params_str) if params_str else {}
                    except json.JSONDecodeError:
                        new_params = node.params
                else:
                    new_params = node.params

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Update node", use_container_width=True):
                        node.label = new_label_edit
                        node.params = new_params
                        st.rerun()
                with col_b:
                    if st.button("Delete node", use_container_width=True):
                        layout.nodes = [n for n in layout.nodes if n.id != edit_id]
                        layout.edges = [e for e in layout.edges if e.from_id != edit_id and e.to_id != edit_id]
                        st.rerun()
        if layout.edges:
            edge_options = [f"{e.from_id} → {e.to_id}" for e in layout.edges]
            to_remove = st.selectbox("Edge to remove", edge_options, key="del_edge")
            if st.button("Delete edge", use_container_width=True) and to_remove:
                part = to_remove.split(" → ", 1)
                if len(part) == 2:
                    layout.edges = [e for e in layout.edges if e.from_id != part[0] or e.to_id != part[1]]
                    st.rerun()

    # ----- Main: canvas -----
    if layout.nodes:
        html = layout_to_pyvis_html(layout, height=620)
        components.html(html, height=630, scrolling=False)
        st.caption("Add nodes, connect edges, then Save layout (JSON). New nodes are placed to the right of existing ones so the layout stays stable.")
    else:
        st.info("Add a node from the sidebar to start. Use **Source** for where jobs enter and **Sink** for where they leave.")

    st.divider()
    st.markdown("**How it works:** Sources generate jobs; Stations process them; Buffers hold WIP; Sinks are exits. Connect with edges, then Save layout (JSON).")


if __name__ == "__main__":
    main()
