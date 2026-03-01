// Evidence List Component
// Based on: docs/evidence_chain_frontend_design.md

import { useTranslation } from 'react-i18next'
import EvidenceCard from './EvidenceCard'
import { EvidenceEntity, EvidenceQueryParams } from '@/types/evidence'
import Button from '@/components/ui/Button'
import PaginationControls from '@/components/ui/PaginationControls'

interface EvidenceListProps {
  items: EvidenceEntity[]
  loading: boolean
  pagination?: {
    total: number
    page: number
    page_size: number
    total_pages: number
  }
  onParamsChange: (params: EvidenceQueryParams) => void
  onViewDetails: (entity: EvidenceEntity) => void
}

export default function EvidenceList({
  items,
  loading,
  pagination,
  onParamsChange,
  onViewDetails,
}: EvidenceListProps) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
        <span className="mb-2 text-4xl">🔍</span>
        <p>{t('evidence.list.no_results') || '暂无证据链数据'}</p>
        <p className="text-sm">
          {t('evidence.list.no_results_hint') || '请尝试调整筛选条件'}
        </p>
      </div>
    )
  }

  const handlePageChange = (page: number) => {
    onParamsChange({ ...pagination, page } as EvidenceQueryParams)
  }

  return (
    <div className="space-y-4">
      {/* Results count */}
      <div className="text-sm text-muted-foreground">
        {t('evidence.list.total') || '共'} {pagination?.total || 0} {t('evidence.list.results') || '条结果'}
      </div>

      {/* Cards Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {items.map((entity) => (
          <EvidenceCard
            key={`${entity.entity_name}-${entity.entity_type}`}
            entity={entity}
            onViewDetails={onViewDetails}
          />
        ))}
      </div>

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex justify-center pt-4">
          <PaginationControls
            currentPage={pagination.page}
            totalPages={pagination.total_pages}
            onPageChange={handlePageChange}
          />
        </div>
      )}
    </div>
  )
}
