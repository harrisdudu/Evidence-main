// Evidence Detail Drawer Component
// Based on: docs/evidence_chain_frontend_design.md

import { useTranslation } from 'react-i18next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog'
import Badge from '@/components/ui/Badge'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { EvidenceEntity, EVIDENCE_LEVEL_CONFIG, RELATION_TYPE_CONFIG } from '@/types/evidence'

interface EvidenceDetailProps {
  entity: EvidenceEntity | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function EvidenceDetail({ entity, open, onOpenChange }: EvidenceDetailProps) {
  const { t } = useTranslation()

  if (!entity) return null

  const levelConfig = EVIDENCE_LEVEL_CONFIG[entity.evidence_level]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>🔗</span>
            <span>{t('evidence.detail.title') || '证据详情'}</span>
          </DialogTitle>
        </DialogHeader>

        <ScrollArea className="max-h-[70vh] pr-4">
          <div className="space-y-6">
            {/* Basic Info */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="font-semibold">{entity.entity_name}</span>
                <Badge style={{ backgroundColor: levelConfig.color }}>
                  {levelConfig.label}
                </Badge>
                <Badge variant="outline">{entity.entity_type}</Badge>
              </div>
              <div className="text-sm text-muted-foreground">
                {t('evidence.detail.confidence') || '置信度'}: {Math.round(entity.confidence * 100)}%
              </div>
            </div>

            {/* Description */}
            <div>
              <h4 className="mb-2 text-sm font-medium">📝 {t('evidence.detail.description') || '描述'}</h4>
              <p className="rounded bg-muted p-3 text-sm">{entity.description}</p>
            </div>

            {/* Scene Tags */}
            {entity.scene_tags.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-medium">🏷️ {t('evidence.detail.scene_tags') || '场景标签'}</h4>
                <div className="flex flex-wrap gap-1">
                  {entity.scene_tags.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Source Provenance */}
            <div>
              <h4 className="mb-2 text-sm font-medium">🔖 {t('evidence.detail.provenance') || '溯源信息'}</h4>
              <div className="rounded bg-muted p-3">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">{t('evidence.detail.document') || '文档'}:</span>
                    <span className="ml-2">{entity.source_provenance.file_name}</span>
                  </div>
                  {entity.source_provenance.page_num && (
                    <div>
                      <span className="text-muted-foreground">{t('evidence.detail.page') || '页码'}:</span>
                      <span className="ml-2">{entity.source_provenance.page_num}</span>
                    </div>
                  )}
                  <div className="col-span-2">
                    <span className="text-muted-foreground">{t('evidence.detail.chunk') || 'Chunk ID'}:</span>
                    <span className="ml-2 font-mono text-xs">{entity.source_provenance.chunk_id}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-muted-foreground">{t('evidence.detail.path') || '路径'}:</span>
                    <span className="ml-2 break-all text-xs">{entity.source_provenance.file_path}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Evidence Chains */}
            {entity.evidence_chains.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-medium">🔗 {t('evidence.detail.chains') || '关联证据链'}</h4>
                <div className="space-y-2">
                  {entity.evidence_chains.map((chain) => {
                    const relationConfig = RELATION_TYPE_CONFIG[chain.chain_type]
                    const chainLevelConfig = EVIDENCE_LEVEL_CONFIG[chain.evidence_level]

                    return (
                      <div key={chain.chain_id} className="rounded border p-3">
                        <div className="mb-2 flex items-center gap-2">
                          <span style={{ color: relationConfig.color, fontSize: '16px' }}>
                            {relationConfig.icon}
                          </span>
                          <span className="font-medium">[{relationConfig.label}]</span>
                          <span>{entity.entity_name}</span>
                          <span>→</span>
                          <span>{chain.target_entity}</span>
                        </div>
                        <div className="mb-2 text-sm text-muted-foreground">{chain.description}</div>
                        <div className="flex gap-2 text-xs">
                          <Badge style={{ backgroundColor: chainLevelConfig.color }}>
                            {chainLevelConfig.label}
                          </Badge>
                          <span className="text-muted-foreground">
                            {t('evidence.detail.confidence') || '置信度'}: {Math.round(chain.confidence * 100)}%
                          </span>
                          {chain.keywords.length > 0 && (
                            <div className="flex gap-1">
                              {chain.keywords.slice(0, 3).map((kw) => (
                                <Badge key={kw} variant="outline" className="text-xs">
                                  {kw}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Update Time */}
            {entity.update_time && (
              <div className="text-xs text-muted-foreground">
                {t('evidence.detail.update_time') || '更新时间'}: {entity.update_time}
              </div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
