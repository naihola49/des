import { useState, useEffect } from 'react'
import type { Node, Edge } from '@xyflow/react'
import type { NodeData } from './layoutAdapter'

interface EditPanelProps {
  node: Node<NodeData> | null
  edge: Edge | null
  nodes: Node<NodeData>[]
  onUpdateNode: (id: string, u: { label?: string; params?: Record<string, unknown> }) => void
  onDeleteNode: (id: string) => void
  onUpdateEdge: (id: string, probability: number | undefined) => void
  onDeleteEdge: (id: string) => void
  onAddEdge: (sourceId: string, targetId: string, probability?: number) => void
  onClose: () => void
}

export function EditPanel({
  node,
  edge,
  nodes,
  onUpdateNode,
  onDeleteNode,
  onUpdateEdge,
  onDeleteEdge,
  onAddEdge,
  onClose,
}: EditPanelProps) {
  const [label, setLabel] = useState('')
  const [paramsStr, setParamsStr] = useState('')
  const [probStr, setProbStr] = useState('')
  const [addEdgeTargetId, setAddEdgeTargetId] = useState('')
  const [addEdgeProbStr, setAddEdgeProbStr] = useState('')

  useEffect(() => {
    if (node) {
      setLabel(node.data?.label ?? '')
      setParamsStr(JSON.stringify(node.data?.params ?? {}, null, 2))
    }
  }, [node])

  useEffect(() => {
    if (edge) {
      const p = (edge.data as { probability?: number })?.probability
      setProbStr(p != null ? String(p) : '')
    }
  }, [edge])

  if (!node && !edge) {
    return (
      <div
        style={{
          width: 260,
          background: 'white',
          borderLeft: '1px solid #ddd',
          padding: 16,
          fontSize: 14,
          color: '#666',
        }}
      >
        Click a node or edge to edit it.
      </div>
    )
  }

  if (node) {
    let paramsObj: Record<string, unknown> = {}
    try {
      paramsObj = JSON.parse(paramsStr || '{}')
    } catch {
      // leave as previous
    }
    return (
      <div
        style={{
          width: 280,
          background: 'white',
          borderLeft: '1px solid #ddd',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <strong>Edit node</strong>
          <button type="button" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 4 }}>Label</label>
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            style={{ width: '100%', padding: 6 }}
          />
        </div>
        {(node.data?.nodeType === 'source' || node.data?.nodeType === 'station' || node.data?.nodeType === 'buffer' || node.data?.nodeType === 'rework') && (
          <div>
            <label style={{ display: 'block', fontSize: 12, marginBottom: 4 }}>
              Params (JSON){node.data?.nodeType === 'rework' ? ' — e.g. {"delay": 1} for mean delay before sending back' : ''}
            </label>
            <textarea
              value={paramsStr}
              onChange={(e) => setParamsStr(e.target.value)}
              rows={4}
              style={{ width: '100%', padding: 6, fontFamily: 'monospace', fontSize: 12 }}
            />
          </div>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            type="button"
            onClick={() => onUpdateNode(node.id, { label, params: paramsObj })}
          >
            Update
          </button>
          <button
            type="button"
            onClick={() => onDeleteNode(node.id)}
            style={{ background: '#dc3545', color: 'white' }}
          >
            Delete
          </button>
        </div>
        <hr style={{ border: 'none', borderTop: '1px solid #eee', margin: '8px 0' }} />
        <div>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 4 }}>Add edge from this node</label>
          <select
            value={addEdgeTargetId}
            onChange={(e) => setAddEdgeTargetId(e.target.value)}
            style={{ width: '100%', padding: 6, marginBottom: 6 }}
          >
            <option value="">Select target node…</option>
            {nodes
              .filter((n) => n.id !== node.id)
              .map((n) => (
                <option key={n.id} value={n.id}>
                  {n.data?.label ?? n.id}
                </option>
              ))}
          </select>
          <input
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={addEdgeProbStr}
            onChange={(e) => setAddEdgeProbStr(e.target.value)}
            placeholder="Probability (optional)"
            style={{ width: '100%', padding: 6, marginBottom: 6 }}
          />
          <button
            type="button"
            disabled={!addEdgeTargetId}
            onClick={() => {
              const prob = addEdgeProbStr === '' ? undefined : parseFloat(addEdgeProbStr)
              onAddEdge(node.id, addEdgeTargetId, prob)
              setAddEdgeTargetId('')
              setAddEdgeProbStr('')
            }}
            style={{ width: '100%' }}
          >
            Add edge
          </button>
        </div>
      </div>
    )
  }

  if (edge) {
    const prob = probStr === '' ? undefined : parseFloat(probStr)
    return (
      <div
        style={{
          width: 280,
          background: 'white',
          borderLeft: '1px solid #ddd',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <strong>Edit edge</strong>
          <button type="button" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div style={{ fontSize: 12, color: '#666' }}>
          {edge.source} → {edge.target}
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 12, marginBottom: 4 }}>Probability (optional)</label>
          <input
            type="number"
            min={0}
            max={1}
            step={0.1}
            value={probStr}
            onChange={(e) => setProbStr(e.target.value)}
            placeholder="1.0"
            style={{ width: '100%', padding: 6 }}
          />
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" onClick={() => onUpdateEdge(edge.id, prob)}>
            Update
          </button>
          <button
            type="button"
            onClick={() => onDeleteEdge(edge.id)}
            style={{ background: '#dc3545', color: 'white' }}
          >
            Delete
          </button>
        </div>
      </div>
    )
  }

  return null
}
