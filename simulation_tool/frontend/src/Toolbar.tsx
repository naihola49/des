import { useRef, useState } from 'react'
import { useReactFlow } from '@xyflow/react'
import type { FactoryLayout } from './types'

type NodeType = 'source' | 'station' | 'buffer' | 'sink' | 'rework'

interface ToolbarProps {
  onAddNode: (type: NodeType, position?: { x: number; y: number }) => void
  onLoad: (layout: FactoryLayout) => void
  onSave: () => void
  onGenerate: (description: string) => Promise<void>
  generateStatus: 'idle' | 'loading' | 'error'
  generateError: string | null
}

export function Toolbar({
  onAddNode,
  onLoad,
  onSave,
  onGenerate,
  generateStatus,
  generateError,
}: ToolbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const lastAddNodeTimeRef = useRef(0)
  const [generateText, setGenerateText] = useState('')
  const [showGenerate, setShowGenerate] = useState(false)
  const { screenToFlowPosition } = useReactFlow()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const layout = JSON.parse(reader.result as string) as FactoryLayout
        if (layout?.nodes && layout?.edges) {
          onLoad(layout)
        } else {
          alert('Invalid layout file: needs nodes and edges')
        }
      } catch {
        alert('Invalid JSON file')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const handleAddNode = (e: React.MouseEvent, type: NodeType) => {
    e.preventDefault()
    e.stopPropagation()
    const now = Date.now()
    if (now - lastAddNodeTimeRef.current < 500) return
    lastAddNodeTimeRef.current = now

    const container = document.querySelector('.react-flow')
    if (container) {
      const rect = container.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      const position = screenToFlowPosition({ x: centerX, y: centerY })
      onAddNode(type, position)
    } else {
      onAddNode(type)
    }
  }

  return (
    <div
      className="toolbar-no-drag"
      style={{
        background: 'white',
        padding: 12,
        borderRadius: 8,
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        maxWidth: 320,
        pointerEvents: 'auto',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Factory Layout</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
        {(['source', 'station', 'buffer', 'sink', 'rework'] as const).map((type) => (
          <button
            key={type}
            type="button"
            onClick={(e) => handleAddNode(e, type)}
            style={{ padding: '6px 10px', fontSize: 12, textTransform: 'capitalize', cursor: 'pointer' }}
          >
            + {type}
          </button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
        <button type="button" onClick={() => fileInputRef.current?.click()} style={{ flex: 1 }}>
          Load
        </button>
        <button type="button" onClick={onSave} style={{ flex: 1 }}>
          Save
        </button>
      </div>
      <div>
        <button
          type="button"
          onClick={() => setShowGenerate((s) => !s)}
          style={{ width: '100%' }}
        >
          ✨ Generate from description
        </button>
        {showGenerate && (
          <div style={{ marginTop: 8 }}>
            <textarea
              placeholder="e.g. Raw material → assembly → buffer → test → shipping"
              value={generateText}
              onChange={(e) => setGenerateText(e.target.value)}
              rows={3}
              style={{ width: '100%', resize: 'vertical', marginBottom: 6 }}
            />
            <button
              type="button"
              disabled={generateStatus === 'loading' || !generateText.trim()}
              onClick={() => onGenerate(generateText)}
              style={{ width: '100%' }}
            >
              {generateStatus === 'loading' ? 'Generating…' : 'Generate layout'}
            </button>
            {generateStatus === 'error' && generateError && (
              <div style={{ color: '#c00', fontSize: 12, marginTop: 4 }}>{generateError}</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
