// Evidence Graph Visualization Component
// Based on: docs/evidence_chain_frontend_design.md

import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { EvidenceGraphData, EVIDENCE_LEVEL_CONFIG, RELATION_TYPE_CONFIG } from '@/types/evidence'

interface EvidenceGraphProps {
  data: EvidenceGraphData | null
  loading: boolean
}

export default function EvidenceGraph({ data, loading }: EvidenceGraphProps) {
  const { t } = useTranslation()
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvasRef.current || !data || data.nodes.length === 0) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size
    const rect = canvas.parentElement?.getBoundingClientRect()
    if (rect) {
      canvas.width = rect.width
      canvas.height = rect.height
    }

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Simple force-directed layout (simplified)
    const nodePositions: Record<string, { x: number; y: number }> = {}
    const centerX = canvas.width / 2
    const centerY = canvas.height / 2
    const radius = Math.min(canvas.width, canvas.height) * 0.35

    // Position nodes in a circle
    data.nodes.forEach((node, i) => {
      const angle = (i / data.nodes.length) * 2 * Math.PI
      nodePositions[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      }
    })

    // Draw edges first (behind nodes)
    data.edges.forEach((edge) => {
      const source = nodePositions[edge.source]
      const target = nodePositions[edge.target]
      if (!source || !target) return

      const relationConfig = RELATION_TYPE_CONFIG[edge.type]

      ctx.beginPath()
      ctx.strokeStyle = relationConfig.color
      ctx.lineWidth = 2
      if (edge.type === 'contradict') {
        ctx.setLineDash([5, 5])
      } else if (edge.type === 'related') {
        ctx.setLineDash([2, 2])
      } else {
        ctx.setLineDash([])
      }
      ctx.moveTo(source.x, source.y)
      ctx.lineTo(target.x, target.y)
      ctx.stroke()
      ctx.setLineDash([])
    })

    // Draw nodes
    data.nodes.forEach((node) => {
      const pos = nodePositions[node.id]
      if (!pos) return

      const levelConfig = EVIDENCE_LEVEL_CONFIG[node.level]
      const nodeRadius = 25

      // Node circle
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, nodeRadius, 0, 2 * Math.PI)
      ctx.fillStyle = levelConfig.color + '40' // Add transparency
      ctx.fill()
      ctx.strokeStyle = levelConfig.color
      ctx.lineWidth = 3
      ctx.stroke()

      // Node label
      ctx.fillStyle = '#000'
      ctx.font = '12px sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'

      // Truncate name if too long
      const displayName = node.name.length > 8 ? node.name.slice(0, 8) + '...' : node.name
      ctx.fillText(displayName, pos.x, pos.y)

      // Level badge
      ctx.font = '10px sans-serif'
      ctx.fillText(levelConfig.label, pos.x, pos.y + nodeRadius + 12)
    })

    // Draw legend
    const legendY = canvas.height - 30
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'left'

    // Level legend
    Object.entries(EVIDENCE_LEVEL_CONFIG).forEach(([level, config], i) => {
      ctx.beginPath()
      ctx.arc(20 + i * 25, legendY, 5, 0, 2 * Math.PI)
      ctx.fillStyle = config.color
      ctx.fill()
    })
  }, [data])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
        <span className="mb-2 text-4xl">🕸️</span>
        <p>{t('evidence.graph.no_data') || '暂无可视化数据'}</p>
      </div>
    )
  }

  return (
    <div className="relative h-full min-h-[400px] rounded-lg border bg-card">
      <canvas ref={canvasRef} className="h-full w-full" />
      
      {/* Legend */}
      <div className="absolute bottom-2 left-2 rounded bg-background/80 p-2 text-xs">
        <div className="mb-1 font-medium">{t('evidence.graph.legend') || '图例'}</div>
        <div className="flex gap-3">
          {Object.entries(EVIDENCE_LEVEL_CONFIG).map(([level, config]) => (
            <span key={level} className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: config.color }} />
              {config.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
