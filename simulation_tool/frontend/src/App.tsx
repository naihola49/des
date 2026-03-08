import { useCallback, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  addEdge,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type Connection,
  type NodeTypes,
  Panel,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { layoutToFlow, flowToLayout } from './layoutAdapter'
import type { FactoryLayout } from './types'
import { EditPanel } from './EditPanel'
import { Toolbar } from './Toolbar'
import { SourceNode, StationNode, BufferNode, SinkNode, ReworkNode } from './CustomNode'

const nodeTypes: NodeTypes = {
  source: SourceNode,
  station: StationNode,
  buffer: BufferNode,
  sink: SinkNode,
  rework: ReworkNode,
}

const initialLayout: FactoryLayout = { nodes: [], edges: [] }

function App() {
  const { nodes: initialNodes, edges: initialEdges } = layoutToFlow(initialLayout)
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [generateStatus, setGenerateStatus] = useState<'idle' | 'loading' | 'error'>( 'idle')
  const [generateError, setGenerateError] = useState<string | null>(null)

  const onConnect = useCallback(
    (conn: Connection) => setEdges((eds) => addEdge(conn, eds)),
    [setEdges]
  )

  const onNodeClick = useCallback((_e: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id)
    setSelectedEdgeId(null)
  }, [])
  const onEdgeClick = useCallback((_e: React.MouseEvent, edge: Edge) => {
    setSelectedEdgeId(edge.id)
    setSelectedNodeId(null)
  }, [])
  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null)
    setSelectedEdgeId(null)
  }, [])

  const selectedNode = selectedNodeId ? nodes.find((n) => n.id === selectedNodeId) : null
  const selectedEdge = selectedEdgeId ? edges.find((e) => e.id === selectedEdgeId) : null

  const handleUpdateNode = useCallback(
    (nodeId: string, updates: { label?: string; params?: Record<string, unknown> }) => {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id !== nodeId) return n
          return {
            ...n,
            data: {
              ...n.data,
              label: updates.label ?? n.data?.label,
              params: updates.params ?? n.data?.params,
            },
          }
        })
      )
    },
    [setNodes]
  )

  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId))
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId))
      setSelectedNodeId(null)
    },
    [setNodes, setEdges]
  )

  const handleUpdateEdge = useCallback(
    (edgeId: string, probability: number | undefined) => {
      setEdges((eds) =>
        eds.map((e) =>
          e.id !== edgeId ? e : { ...e, data: { ...e.data, probability } }
        )
      )
    },
    [setEdges]
  )

  const handleDeleteEdge = useCallback(
    (edgeId: string) => {
      setEdges((eds) => eds.filter((e) => e.id !== edgeId))
      setSelectedEdgeId(null)
    },
    [setEdges]
  )

  const handleAddEdge = useCallback(
    (sourceId: string, targetId: string, probability?: number) => {
      if (sourceId === targetId) return
      const id = `e-${sourceId}-${targetId}-${Date.now()}`
      setEdges((eds) =>
        eds.concat({
          id,
          source: sourceId,
          target: targetId,
          data: probability != null ? { probability } : {},
        })
      )
    },
    [setEdges]
  )

  const handleLoad = useCallback((layout: FactoryLayout) => {
    const { nodes: n, edges: e } = layoutToFlow(layout)
    setNodes(n)
    setEdges(e)
    setSelectedNodeId(null)
    setSelectedEdgeId(null)
  }, [setNodes, setEdges])

  const handleSave = useCallback(() => {
    const layout = flowToLayout(nodes, edges)
    const blob = new Blob([JSON.stringify(layout, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'factory_layout.json'
    a.click()
    URL.revokeObjectURL(url)
  }, [nodes, edges])

  const handleGenerate = useCallback(
    async (description: string) => {
      setGenerateStatus('loading')
      setGenerateError(null)
      try {
        const res = await fetch('/api/generate-layout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ description: description.trim() }),
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }))
          throw new Error(err.detail || 'Generate failed')
        }
        const layout: FactoryLayout = await res.json()
        handleLoad(layout)
        setGenerateStatus('idle')
      } catch (e) {
        setGenerateError(e instanceof Error ? e.message : 'Failed')
        setGenerateStatus('error')
      }
    },
    [handleLoad]
  )

  const handleAddNode = useCallback(
    (nodeType: 'source' | 'station' | 'buffer' | 'sink' | 'rework', position?: { x: number; y: number }) => {
      const id = `${nodeType}_${Date.now()}`
      const defaults: Record<string, Record<string, unknown>> = {
        source: { distribution: 'exponential', mean: 2 },
        station: { distribution: 'gamma', mean: 5, cv: 0.5 },
        buffer: { capacity: 10 },
        sink: {},
        rework: { delay: 0 },
      }
      const x = position?.x ?? 100 + nodes.length * 180
      const y = position?.y ?? 150
      setNodes((nds) =>
        nds.concat({
          id,
          type: nodeType,
          position: { x, y },
          data: {
            label: id.replace('_', ' '),
            nodeType,
            params: defaults[nodeType] ?? {},
          },
        })
      )
    },
    [nodes.length, setNodes]
  )

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes as NodeTypes}
        noDragClassName="toolbar-no-drag"
        fitView
      >
        <Background />
        <Controls />
        <Panel position="top-left">
          <Toolbar
            onAddNode={handleAddNode}
            onLoad={handleLoad}
            onSave={handleSave}
            onGenerate={handleGenerate}
            generateStatus={generateStatus}
            generateError={generateError}
          />
        </Panel>
      </ReactFlow>
      <EditPanel
        node={selectedNode ?? null}
        edge={selectedEdge ?? null}
        nodes={nodes}
        onUpdateNode={handleUpdateNode}
        onDeleteNode={handleDeleteNode}
        onUpdateEdge={handleUpdateEdge}
        onDeleteEdge={handleDeleteEdge}
        onAddEdge={handleAddEdge}
        onClose={() => {
          setSelectedNodeId(null)
          setSelectedEdgeId(null)
        }}
      />
    </div>
  )
}

export default App
