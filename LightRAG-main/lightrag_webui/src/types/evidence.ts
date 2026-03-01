// Evidence Chain Types - Based on technical specification
// Reference: docs/evidence_chain_technical_spec.md

// Evidence Level - 4-level classification
export type EvidenceLevel = 'S' | 'A' | 'B' | 'C'

// Evidence Relation Types - causal/support/contradict/related
export type EvidenceRelationType = 'causal' | 'support' | 'contradict' | 'related'

// Source Provenance - Multi-level traceability
export interface SourceProvenance {
  doc_id: string
  file_name: string
  file_path: string
  page_num?: number
  paragraph_id?: string
  chunk_id: string
}

// Evidence Chain - Relationship between entities
export interface EvidenceChain {
  chain_id: string
  chain_type: EvidenceRelationType
  target_entity: string
  target_type?: string
  description: string
  evidence_level: EvidenceLevel
  confidence: number
  keywords: string[]
  valid_from?: string
  valid_to?: string | null
}

// Evidence Entity - Enhanced entity with evidence
export interface EvidenceEntity {
  entity_name: string
  entity_type: string
  description: string
  evidence_level: EvidenceLevel
  confidence: number
  source_provenance: SourceProvenance
  scene_tags: string[]
  evidence_chains: EvidenceChain[]
  update_time?: string
}

// Query Parameters
export interface EvidenceQueryParams {
  evidence_levels?: EvidenceLevel[]
  relation_types?: EvidenceRelationType[]
  scene_tags?: string[]
  keyword?: string
  page?: number
  page_size?: number
  sort_by?: 'relevance' | 'evidence_level' | 'confidence' | 'update_time'
  sort_order?: 'asc' | 'desc'
}

// Pagination
export interface EvidencePagination {
  total: number
  page: number
  page_size: number
  total_pages: number
}

// Query Response
export interface EvidenceQueryResponse {
  items: EvidenceEntity[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// Evidence Statistics
export interface EvidenceStats {
  total: number
  by_level: Record<EvidenceLevel, number>
  by_relation_type: Record<EvidenceRelationType, number>
  by_scene: Record<string, number>
  support_contradict_ratio: {
    support: number
    contradict: number
    ratio: string
  }
}

// Visualization Types
export interface EvidenceGraphNode {
  id: string
  name: string
  type: string
  level: EvidenceLevel
  confidence: number
}

export interface EvidenceGraphEdge {
  source: string
  target: string
  type: EvidenceRelationType
  level: EvidenceLevel
  confidence: number
  description: string
}

export interface EvidenceGraphData {
  nodes: EvidenceGraphNode[]
  edges: EvidenceGraphEdge[]
}

// API Response wrapper
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

// Evidence Level Display Info
export const EVIDENCE_LEVEL_CONFIG: Record<EvidenceLevel, { label: string; color: string; bgColor: string; description: string }> = {
  S: { label: 'S级', color: '#EF4444', bgColor: 'bg-red-500', description: '监管机构/权威发布' },
  A: { label: 'A级', color: '#F97316', bgColor: 'bg-orange-500', description: '头部研报/顶刊论文' },
  B: { label: 'B级', color: '#3B82F6', bgColor: 'bg-blue-500', description: '中型机构报告' },
  C: { label: 'C级', color: '#6B7280', bgColor: 'bg-gray-500', description: '普通报告/书籍章节' },
}

// Relation Type Display Info
export const RELATION_TYPE_CONFIG: Record<EvidenceRelationType, { label: string; color: string; icon: string }> = {
  causal: { label: '因果', color: '#8B5CF6', icon: '→' },
  support: { label: '支持', color: '#10B981', icon: '✓' },
  contradict: { label: '反驳', color: '#EF4444', icon: '✗' },
  related: { label: '相关', color: '#6B7280', icon: '↔' },
}

// Scene Tags - 14 industries
export const SCENE_TAGS = [
  // Finance
  '投研分析', '风险控制', '合规审核', '产品设计', '市场研判', '政策法规', '金融', '投资',
  // Healthcare
  '医疗健康', '医药', '医疗器械', '公共卫生',
  // Urban Governance
  '城市治理', '智慧城市', '公共服务', '应急管理',
  // Education
  '教育', '职业教育', '教育科技',
  // Manufacturing
  '工业制造', '供应链', '质量管理', '智能制造',
  // Energy
  '能源', '电力', '新能源',
  // Agriculture
  '农业', '食品安全', '乡村振兴',
  // Legal
  '法律', '司法', '合规法律',
  // Media
  '媒体', '公共关系',
  // Environment
  '环境保护', '生态', '气候变化',
  // Transportation
  '交通运输', '物流', '自动驾驶',
  // Real Estate
  '房地产', '建筑', '物业管理',
  // IT
  '信息技术', '网络安全', '数据隐私',
  // Retail
  '商业零售', '电子商务', '消费者保护',
]
