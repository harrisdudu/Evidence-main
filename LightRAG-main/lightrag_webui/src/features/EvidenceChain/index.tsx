// Evidence Chain Main Component
// Based on: docs/evidence_chain_frontend_design.md

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import EvidenceQueryPanel from './EvidenceQueryPanel'
import EvidenceStatsPanel from './EvidenceStatsPanel'
import EvidenceList from './EvidenceList'
import EvidenceGraph from './EvidenceGraph'
import EvidenceDetail from './EvidenceDetail'
import { evidenceApi } from '@/api/evidence'
import {
  EvidenceQueryParams,
  EvidenceEntity,
  EvidenceStats,
  EvidenceGraphData,
} from '@/types/evidence'

export default function EvidenceChain() {
  const { t } = useTranslation()
  const [viewMode, setViewMode] = useState<'list' | 'graph'>('list')

  // Query state
  const [queryParams, setQueryParams] = useState<EvidenceQueryParams>({
    evidence_levels: [],
    relation_types: [],
    scene_tags: [],
    keyword: '',
    page: 1,
    page_size: 20,
    sort_by: 'relevance',
    sort_order: 'desc',
  })

  const [results, setResults] = useState<{
    items: EvidenceEntity[]
    total: number
    page: number
    page_size: number
    total_pages: number
  } | null>(null)
  const [stats, setStats] = useState<EvidenceStats | null>(null)
  const [graphData, setGraphData] = useState<EvidenceGraphData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detail drawer state
  const [selectedEntity, setSelectedEntity] = useState<EvidenceEntity | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      // Fetch list data
      const listRes = await evidenceApi.query(queryParams)
      setResults(listRes)

      // Fetch stats
      const statsRes = await evidenceApi.getStats({
        scene_tag: queryParams.scene_tags?.[0],
      })
      setStats(statsRes)

      // Fetch graph data (for visualization)
      if (queryParams.keyword) {
        const graphRes = await evidenceApi.getVisualize({
          entity_name: queryParams.keyword,
          depth: 2,
          evidence_levels: queryParams.evidence_levels,
          relation_types: queryParams.relation_types,
        })
        setGraphData(graphRes)
      } else {
        setGraphData(null)
      }
    } catch (err: any) {
      console.error('Error fetching evidence data:', err)
      setError(err.message || 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }, [queryParams])

  // Initial fetch
  useEffect(() => {
    fetchData()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch on params change
  useEffect(() => {
    fetchData()
  }, [queryParams]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleViewDetails = useCallback((entity: EvidenceEntity) => {
    setSelectedEntity(entity)
    setDetailOpen(true)
  }, [])

  return (
    <div className="flex h-full flex-col p-4">
      {/* Query + Stats Row */}
      <div className="mb-4 flex gap-4">
        <div className="w-1/3">
          <EvidenceQueryPanel
            params={queryParams}
            onParamsChange={setQueryParams}
            onSearch={fetchData}
          />
        </div>
        <div className="flex-1">
          <EvidenceStatsPanel stats={stats} loading={loading} />
        </div>
      </div>

      {/* View Mode Toggle */}
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          {t('evidence.title') || '证据链检索'}
        </h2>
        <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'list' | 'graph')}>
          <TabsList>
            <TabsTrigger value="list">
              {t('evidence.view_list') || '列表视图'}
            </TabsTrigger>
            <TabsTrigger value="graph">
              {t('evidence.view_graph') || '图谱视图'}
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {error && (
          <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-600">
            {error}
          </div>
        )}

        {viewMode === 'list' ? (
          <EvidenceList
            items={results?.items || []}
            loading={loading}
            pagination={results || undefined}
            onParamsChange={setQueryParams}
            onViewDetails={handleViewDetails}
          />
        ) : (
          <EvidenceGraph data={graphData} loading={loading} />
        )}
      </div>

      {/* Detail Drawer */}
      <EvidenceDetail
        entity={selectedEntity}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </div>
  )
}
