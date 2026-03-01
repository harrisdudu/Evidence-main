// Evidence Stats Panel Component
// Based on: docs/evidence_chain_frontend_design.md

import { useTranslation } from 'react-i18next'
import { EvidenceStats, EVIDENCE_LEVEL_CONFIG, EvidenceLevel } from '@/types/evidence'

interface EvidenceStatsPanelProps {
  stats: EvidenceStats | null
  loading: boolean
}

export default function EvidenceStatsPanel({ stats, loading }: EvidenceStatsPanelProps) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <div className="rounded-lg border bg-card p-4 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold">
          {t('evidence.stats.title') || '证据聚合统计'}
        </h3>
        <div className="flex h-32 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="rounded-lg border bg-card p-4 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold">
          {t('evidence.stats.title') || '证据聚合统计'}
        </h3>
        <div className="flex h-32 items-center justify-center text-muted-foreground">
          {t('evidence.stats.no_data') || '暂无数据'}
        </div>
      </div>
    )
  }

  // Calculate max for bar chart
  const maxCount = Math.max(...Object.values(stats.by_level), 1)

  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold">
        {t('evidence.stats.title') || '证据聚合统计'}
      </h3>

      {/* Total */}
      <div className="mb-4 rounded-md bg-muted p-3 text-center">
        <div className="text-2xl font-bold">{stats.total}</div>
        <div className="text-xs text-muted-foreground">
          {t('evidence.stats.total') || '总证据数'}
        </div>
      </div>

      {/* Level Distribution */}
      <div className="mb-4 space-y-2">
        <div className="text-xs font-medium text-muted-foreground">
          {t('evidence.stats.by_level') || '按证据等级'}
        </div>
        {(Object.keys(EVIDENCE_LEVEL_CONFIG) as EvidenceLevel[]).map((level) => {
          const count = stats.by_level[level] || 0
          const percentage = (count / maxCount) * 100
          const config = EVIDENCE_LEVEL_CONFIG[level]

          return (
            <div key={level} className="flex items-center gap-2">
              <span className="w-8 text-xs" style={{ color: config.color }}>
                {config.label}
              </span>
              <div className="flex-1 overflow-hidden rounded bg-muted">
                <div
                  className="h-4 transition-all"
                  style={{
                    width: `${percentage}%`,
                    backgroundColor: config.color,
                  }}
                />
              </div>
              <span className="w-8 text-right text-xs">{count}</span>
            </div>
          )
        })}
      </div>

      {/* Support vs Contradict */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-muted-foreground">
          {t('evidence.stats.support_contradict') || '支持/反驳'}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 rounded bg-green-500/20 p-2 text-center">
            <div className="text-lg font-bold text-green-600">
              {stats.support_contradict_ratio.support}
            </div>
            <div className="text-xs text-green-600/70">
              {t('evidence.stats.support') || '支持'}
            </div>
          </div>
          <div className="flex-1 rounded bg-red-500/20 p-2 text-center">
            <div className="text-lg font-bold text-red-600">
              {stats.support_contradict_ratio.contradict}
            </div>
            <div className="text-xs text-red-600/70">
              {t('evidence.stats.contradict') || '反驳'}
            </div>
          </div>
        </div>
        <div className="text-center text-xs text-muted-foreground">
          {t('evidence.stats.ratio') || '比例'}: {stats.support_contradict_ratio.ratio}
        </div>
      </div>
    </div>
  )
}
