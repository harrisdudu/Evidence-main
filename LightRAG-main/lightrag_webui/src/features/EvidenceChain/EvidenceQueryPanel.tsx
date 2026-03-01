// Evidence Query Panel Component
// Based on: docs/evidence_chain_frontend_design.md

import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
import {
  EvidenceQueryParams,
  EvidenceLevel,
  EvidenceRelationType,
  EVIDENCE_LEVEL_CONFIG,
  RELATION_TYPE_CONFIG,
  SCENE_TAGS,
} from '@/types/evidence'

interface EvidenceQueryPanelProps {
  params: EvidenceQueryParams
  onParamsChange: (params: EvidenceQueryParams) => void
  onSearch: () => void
}

export default function EvidenceQueryPanel({
  params,
  onParamsChange,
  onSearch,
}: EvidenceQueryPanelProps) {
  const { t } = useTranslation()
  const [localKeyword, setLocalKeyword] = useState(params.keyword || '')

  const handleReset = useCallback(() => {
    setLocalKeyword('')
    onParamsChange({
      evidence_levels: [],
      relation_types: [],
      scene_tags: [],
      keyword: '',
      page: 1,
      page_size: 20,
      sort_by: 'relevance',
      sort_order: 'desc',
    })
  }, [onParamsChange])

  const handleSearch = useCallback(() => {
    onParamsChange({ ...params, keyword: localKeyword, page: 1 })
    onSearch()
  }, [localKeyword, onParamsChange, onSearch, params])

  const handleLevelChange = useCallback(
    (value: string) => {
      const levels = value === 'all' ? [] : ([value] as EvidenceLevel[])
      onParamsChange({ ...params, evidence_levels: levels, page: 1 })
    },
    [onParamsChange, params]
  )

  const handleRelationTypeChange = useCallback(
    (value: string) => {
      const types = value === 'all' ? [] : ([value] as EvidenceRelationType[])
      onParamsChange({ ...params, relation_types: types, page: 1 })
    },
    [onParamsChange, params]
  )

  const handleSceneChange = useCallback(
    (value: string) => {
      const tags = value === 'all' ? [] : [value]
      onParamsChange({ ...params, scene_tags: tags, page: 1 })
    },
    [onParamsChange, params]
  )

  const handleSortChange = useCallback(
    (value: string) => {
      const [sort_by, sort_order] = value.split('-') as [
        EvidenceQueryParams['sort_by'],
        EvidenceQueryParams['sort_order']
      ]
      onParamsChange({ ...params, sort_by, sort_order })
    },
    [onParamsChange, params]
  )

  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold">{t('evidence.query.title') || '检索条件'}</h3>

      <div className="space-y-4">
        {/* Evidence Level */}
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">
            {t('evidence.query.evidence_level') || '证据等级'}
          </label>
          <Select
            value={params.evidence_levels?.[0] || 'all'}
            onValueChange={handleLevelChange}
          >
            <SelectTrigger>
              <SelectValue placeholder={t('evidence.query.select_level') || '全部'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('evidence.query.all') || '全部'}</SelectItem>
              {Object.entries(EVIDENCE_LEVEL_CONFIG).map(([level, config]) => (
                <SelectItem key={level} value={level}>
                  <span className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: config.color }}
                    />
                    {config.label} - {config.description}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Relation Type */}
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">
            {t('evidence.query.relation_type') || '关系类型'}
          </label>
          <Select
            value={params.relation_types?.[0] || 'all'}
            onValueChange={handleRelationTypeChange}
          >
            <SelectTrigger>
              <SelectValue placeholder={t('evidence.query.select_type') || '全部'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('evidence.query.all') || '全部'}</SelectItem>
              {Object.entries(RELATION_TYPE_CONFIG).map(([type, config]) => (
                <SelectItem key={type} value={type}>
                  <span className="flex items-center gap-2">
                    <span style={{ color: config.color }}>{config.icon}</span>
                    {config.label}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Scene Tags */}
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">
            {t('evidence.query.scene_tag') || '场景标签'}
          </label>
          <Select
            value={params.scene_tags?.[0] || 'all'}
            onValueChange={handleSceneChange}
          >
            <SelectTrigger>
              <SelectValue placeholder={t('evidence.query.select_scene') || '选择场景'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('evidence.query.all') || '全部'}</SelectItem>
              {SCENE_TAGS.map((tag) => (
                <SelectItem key={tag} value={tag}>
                  {tag}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Keyword */}
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">
            {t('evidence.query.keyword') || '关键词'}
          </label>
          <Input
            placeholder={t('evidence.query.keyword_placeholder') || '搜索实体名称...'}
            value={localKeyword}
            onChange={(e) => setLocalKeyword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
        </div>

        {/* Sort */}
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">
            {t('evidence.query.sort_by') || '排序'}
          </label>
          <Select
            value={`${params.sort_by || 'relevance'}-${params.sort_order || 'desc'}`}
            onValueChange={handleSortChange}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="relevance-desc">
                {t('evidence.query.relevance') || '相关性'} ↓
              </SelectItem>
              <SelectItem value="relevance-asc">
                {t('evidence.query.relevance') || '相关性'} ↑
              </SelectItem>
              <SelectItem value="evidence_level-desc">
                {t('evidence.query.level') || '证据等级'} ↓
              </SelectItem>
              <SelectItem value="evidence_level-asc">
                {t('evidence.query.level') || '证据等级'} ↑
              </SelectItem>
              <SelectItem value="confidence-desc">
                {t('evidence.query.confidence') || '置信度'} ↓
              </SelectItem>
              <SelectItem value="confidence-asc">
                {t('evidence.query.confidence') || '置信度'} ↑
              </SelectItem>
              <SelectItem value="update_time-desc">
                {t('evidence.query.update_time') || '更新时间'} ↓
              </SelectItem>
              <SelectItem value="update_time-asc">
                {t('evidence.query.update_time') || '更新时间'} ↑
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Buttons */}
        <div className="flex gap-2 pt-2">
          <Button variant="outline" onClick={handleReset} className="flex-1">
            {t('evidence.query.reset') || '重置'}
          </Button>
          <Button onClick={handleSearch} className="flex-1">
            {t('evidence.query.search') || '检索'}
          </Button>
        </div>
      </div>
    </div>
  )
}
