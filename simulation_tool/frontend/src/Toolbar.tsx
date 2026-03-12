import { useRef, useState } from 'react'
import { useReactFlow } from '@xyflow/react'
import type { FactoryLayout } from './types'

type NodeType = 'source' | 'manual' | 'station' | 'buffer' | 'sink' | 'rework'

export interface SimulationResult {
  results: Record<string, number>
  explanation: string | null
}

interface ToolbarProps {
  onAddNode: (type: NodeType, position?: { x: number; y: number }) => void
  onLoad: (layout: FactoryLayout) => void
  onSave: () => void
  onGenerate: (description: string) => Promise<void>
  generateStatus: 'idle' | 'loading' | 'error'
  generateError: string | null
  onRunSimulation: (nTrials: number) => Promise<void>
  simulationStatus: 'idle' | 'loading' | 'error'
  simulationError: string | null
  simulationResult: SimulationResult | null
}

export function Toolbar({
  onAddNode,
  onLoad,
  onSave,
  onGenerate,
  generateStatus,
  generateError,
  onRunSimulation,
  simulationStatus,
  simulationError,
  simulationResult,
}: ToolbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const lastAddNodeTimeRef = useRef(0)
  const [generateText, setGenerateText] = useState('')
  const [showGenerate, setShowGenerate] = useState(false)
  const [nTrials, setNTrials] = useState(30)
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
        padding: 14,
        borderRadius: 10,
        boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        maxWidth: 360,
        maxHeight: '95vh',
        overflowY: 'auto',
        pointerEvents: 'auto',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Factory Layout</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
        {(['source', 'manual', 'station', 'buffer', 'sink', 'rework'] as const).map((type) => (
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
          <div
            style={{
              marginTop: 10,
              padding: 12,
              background: '#f8f9fa',
              borderRadius: 8,
              border: '1px solid #e8eaed',
            }}
          >
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#5f6368', marginBottom: 6 }}>
              Describe your layout
            </label>
            <textarea
              placeholder="e.g. source → 3 parallel machines with rework → buffer → 2 machines → buffer → finished goods"
              value={generateText}
              onChange={(e) => setGenerateText(e.target.value)}
              rows={6}
              style={{
                width: '100%',
                minHeight: 120,
                padding: 10,
                fontSize: 13,
                lineHeight: 1.45,
                border: '1px solid #dadce0',
                borderRadius: 6,
                resize: 'vertical',
                marginBottom: 10,
                fontFamily: 'inherit',
                boxSizing: 'border-box',
              }}
            />
            <button
              type="button"
              disabled={generateStatus === 'loading' || !generateText.trim()}
              onClick={() => onGenerate(generateText)}
              style={{
                width: '100%',
                padding: '8px 12px',
                fontSize: 13,
                fontWeight: 600,
                borderRadius: 6,
                border: 'none',
                background: generateText.trim() ? '#1a73e8' : '#dadce0',
                color: generateText.trim() ? '#fff' : '#80868b',
                cursor: generateText.trim() ? 'pointer' : 'default',
              }}
            >
              {generateStatus === 'loading' ? 'Generating…' : 'Generate layout'}
            </button>
            {generateStatus === 'error' && generateError && (
              <div style={{ color: '#c00', fontSize: 12, marginTop: 6 }}>{generateError}</div>
            )}
          </div>
        )}
      </div>

      <hr style={{ border: 'none', borderTop: '1px solid #eee', margin: '10px 0' }} />
      <div style={{ fontWeight: 600, marginBottom: 6 }}>Simulation (Monte Carlo)</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <label style={{ fontSize: 12 }}>N trials</label>
        <input
          type="number"
          min={1}
          max={500}
          value={nTrials}
          onChange={(e) => setNTrials(Math.max(1, Math.min(500, parseInt(e.target.value, 10) || 30)))}
          style={{ width: 56, padding: 4, fontSize: 12 }}
        />
        <button
          type="button"
          disabled={simulationStatus === 'loading'}
          onClick={() => onRunSimulation(nTrials)}
          style={{ flex: 1, padding: '6px 10px', fontSize: 12 }}
        >
          {simulationStatus === 'loading' ? 'Running…' : 'Run simulation'}
        </button>
      </div>
      {simulationStatus === 'error' && simulationError && (
        <div style={{ color: '#c00', fontSize: 12, marginBottom: 8 }}>{simulationError}</div>
      )}
      {simulationResult && (
        <div
          style={{
            marginTop: 10,
            border: '1px solid #e8eaed',
            borderRadius: 10,
            overflow: 'hidden',
            boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
          }}
        >
          <div
            style={{
              padding: '12px 14px',
              background: 'linear-gradient(180deg, #f1f3f4 0%, #e8eaed 100%)',
              borderBottom: '1px solid #e8eaed',
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: '0.02em',
              color: '#202124',
            }}
          >
            Statistics
          </div>
          <div
            style={{
              padding: '12px 14px',
              display: 'grid',
              gap: 8,
              fontSize: 12,
              color: '#3c4043',
              background: '#fafafa',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#5f6368' }}>Throughput</span>
              <span style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 600 }}>
                {simulationResult.results.throughput_mean?.toFixed(4)} ± {simulationResult.results.throughput_std?.toFixed(4)}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#5f6368' }}>Cycle time</span>
              <span style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 600 }}>
                {simulationResult.results.cycle_time_mean?.toFixed(2)} ± {simulationResult.results.cycle_time_std?.toFixed(2)}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#5f6368' }}>Completed (mean)</span>
              <span style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 600 }}>
                {simulationResult.results.total_completed_mean?.toFixed(1)}
              </span>
            </div>
            <div style={{ paddingTop: 4, borderTop: '1px solid #eee', fontSize: 11, color: '#5f6368' }}>
              Throughput 5th / 50th / 95th %: {simulationResult.results.throughput_5pct?.toFixed(4)} / {simulationResult.results.throughput_50pct?.toFixed(4)} / {simulationResult.results.throughput_95pct?.toFixed(4)}
            </div>
          </div>
          {simulationResult.explanation && (
            <>
              <div
                style={{
                  padding: '10px 14px',
                  background: 'linear-gradient(180deg, #e8f0fe 0%, #d2e3fc 100%)',
                  borderTop: '1px solid #d2e3fc',
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: '0.02em',
                  color: '#1967d2',
                }}
              >
                Insights & recommendations
              </div>
              <div
                style={{
                  padding: '14px 16px',
                  background: '#fff',
                  fontSize: 13,
                  lineHeight: 1.6,
                  color: '#3c4043',
                  maxHeight: 380,
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  borderTop: '1px solid #e8eaed',
                }}
              >
                {simulationResult.explanation}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
