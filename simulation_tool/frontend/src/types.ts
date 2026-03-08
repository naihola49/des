/** Matches the backend layout JSON (nodes + edges). */
export interface LayoutNode {
  id: string
  type: 'source' | 'station' | 'buffer' | 'sink' | 'rework'
  label: string
  params: Record<string, unknown>
  x: number
  y: number
}

export interface LayoutEdge {
  from: string
  to: string
  probability?: number
}

export interface FactoryLayout {
  nodes: LayoutNode[]
  edges: LayoutEdge[]
}
