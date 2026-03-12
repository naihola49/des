import { memo } from 'react'
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import type { NodeData } from './layoutAdapter'

function CustomNode({ data }: NodeProps<Node<NodeData>>) {
  const label = (data as NodeData)?.label ?? 'Node'
  return (
    <>
      <Handle type="target" position={Position.Left} />
      <div>{label}</div>
      <Handle type="source" position={Position.Right} />
    </>
  )
}

export const SourceNode = memo(CustomNode)
export const ManualNode = memo(CustomNode)
export const StationNode = memo(CustomNode)
export const BufferNode = memo(CustomNode)
export const SinkNode = memo(CustomNode)
export const ReworkNode = memo(CustomNode)
