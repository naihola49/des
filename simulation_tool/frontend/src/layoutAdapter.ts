import type { Node, Edge } from '@xyflow/react'
import type { FactoryLayout, LayoutNode, LayoutEdge } from './types'

export type NodeData = {
  label: string
  nodeType: 'source' | 'manual' | 'station' | 'buffer' | 'sink' | 'rework'
  params: Record<string, unknown>
}

export function layoutToFlow(layout: FactoryLayout): { nodes: Node<NodeData>[]; edges: Edge[] } {
  const nodes: Node<NodeData>[] = layout.nodes.map((n) => ({
    id: n.id,
    type: n.type,
    position: { x: n.x, y: n.y },
    data: {
      label: n.label || n.id,
      nodeType: n.type,
      params: n.params ?? {},
    },
  }))
  const edges: Edge[] = layout.edges.map((e, i) => ({
    id: `e-${e.from}-${e.to}-${i}`,
    source: e.from,
    target: e.to,
    data: { probability: e.probability },
  }))
  return { nodes, edges }
}

export function flowToLayout(nodes: Node<NodeData>[], edges: Edge[]): FactoryLayout {
  const layoutNodes: LayoutNode[] = nodes.map((n) => ({
    id: n.id,
    type: (n.data?.nodeType ?? 'station') as LayoutNode['type'],
    label: n.data?.label ?? n.id,
    params: n.data?.params ?? {},
    x: n.position.x,
    y: n.position.y,
  }))
  const layoutEdges: LayoutEdge[] = edges.map((e) => ({
    from: e.source,
    to: e.target,
    probability: (e.data as { probability?: number })?.probability,
  }))
  return { nodes: layoutNodes, edges: layoutEdges }
}
