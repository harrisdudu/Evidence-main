// Evidence Card Component
// Based on: docs/evidence_chain_frontend_design.md

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { EvidenceEntity, EVIDENCE_LEVEL_CONFIG, RELATION_TYPE_CONFIG } from '@/types/evidence'

interface EvidenceCardProps {
  entity: EvidenceEntity
  onViewDetails: (entity: EvidenceEntity) => void
}

export default function EvidenceCard({ entity, onViewDetails }: EvidenceCardProps) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  const levelConfig = EVIDENCE_LEVEL_CONFIG[entity.evidence_level]

  return (
    <div className="rounded-lg border bg-card shadow-sm transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="flex items-start justify-between border-b p-4">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">{entity.entity_name}</h3>
            <span
              className="rounded px-2 py-0.5 text-xs font-medium text-white"
              style={{ backgroundColor: levelConfig.color }}
            >
              {levelConfig.label}
            </span>
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
            <span>{entity.entity_type}</span>
            <span>
              {t('evidence.card.confidence') || '置信度'}: {Math.round(entity.confidence * 100)}%
            </span>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setExpanded(!expanded)}>
          {expanded ? '▲' : '▼'}
        </Button>
      </div>

      {/* Description */}
      <div className="p-4">
        <p className="text-sm text-muted-foreground line-clamp-2">{entity.description}</p>

        {/* Scene Tags */}
        {entity.scene_tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {entity.scene_tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {entity.scene_tags.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{entity.scene_tags.length - 3}
              </Badge>
            )}
          </div>
        )}

        {/* Provenance */}
        <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
          <span>📄</span>
          <span className="truncate">{entity.source_provenance.file_name}</span>
          {entity.source_provenance.page_num && (
            <span>({t('evidence.card.page') || '第'}{entity.source_provenance.page_num}{t('evidence.card.page_num') || '页'})</span>
          )}
        </div>
      </div>

      {/* Expanded: Evidence Chains */}
      {expanded && entity.evidence_chains.length > 0 && (
        <div className="border-t p-4">
          <div className="mb-2 text-xs font-medium text-muted-foreground">
            {t('evidence.card.related_chains') || '关联证据链'}
          </div>
          <div className="space-y-2">
            {entity.evidence_chains.map((chain) => {
              const relationConfig = RELATION_TYPE_CONFIG[chain.chain_type]
              const targetLevelConfig = EVIDENCE_LEVEL_CONFIG[chain.evidence_level]

              return (
                <div
                  key={chain.chain_id}
                  className="flex items-center gap-2 rounded bg-muted p-2 text-xs"
                >
                  <span style={{ color: relationConfig.color }}>{relationConfig.icon}</span>
                  <span className="font-medium">[{relationConfig.label}]</span>
                  <span>→</span>
                  <span className="flex-1 truncate">{chain.target_entity}</span>
                  <span
                    className="rounded px-1.5 py-0.5 text-white"
                    style={{ backgroundColor: targetLevelConfig.color }}
                  >
                    {targetLevelConfig.label}
                  </span>
                  <span className="text-muted-foreground">
                    {Math.round(chain.confidence * 100)}%
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex justify-end border-t p-4 pt-2">
        <Button variant="outline" size="sm" onClick={() => onViewDetails(entity)}>
          {t('evidence.card.view_details') || '查看详情'}
        </Button>
      </div>
    </div>
  )
}
