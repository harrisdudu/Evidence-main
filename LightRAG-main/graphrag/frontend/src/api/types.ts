// API Types

export type DocStatus = 'pending' | 'processing' | 'preprocessed' | 'processed' | 'failed'

export interface Document {
  id: string
  content_summary: string
  content_length: number
  status: DocStatus
  created_at: string
  updated_at: string
  track_id?: string
  chunks_count?: number
  error_msg?: string
  metadata?: Record<string, any>
  file_path: string
}

export interface DocsStatusesResponse {
  statuses: Record<DocStatus, Document[]>
}

export interface PaginatedDocsResponse {
  documents: Document[]
  pagination: {
    page: number
    page_size: number
    total_count: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
  }
  status_counts: Record<string, number>
}

export interface GraphNode {
  id: string
  labels: string[]
  properties: Record<string, any>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type?: string
  properties: Record<string, any>
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export type QueryMode = 'naive' | 'local' | 'global' | 'hybrid' | 'mix' | 'bypass'

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface QueryRequest {
  query: string
  mode: QueryMode
  stream?: boolean
  top_k?: number
  chunk_top_k?: number
  max_entity_tokens?: number
  max_relation_tokens?: number
  max_total_tokens?: number
  conversation_history?: Message[]
  history_turns?: number
  response_type?: string
  user_prompt?: string
  enable_rerank?: boolean
}

export interface QueryResponse {
  response: string
}

export interface HealthStatus {
  status: 'healthy'
  working_directory: string
  input_directory: string
  configuration: {
    llm_binding: string
    llm_binding_host: string
    llm_model: string
    embedding_binding: string
    embedding_binding_host: string
    embedding_model: string
    kv_storage: string
    doc_status_storage: string
    graph_storage: string
    vector_storage: string
    workspace?: string
    max_graph_nodes?: string
    enable_rerank?: boolean
    rerank_binding?: string | null
    rerank_model?: string | null
    summary_language: string
    force_llm_summary_on_merge: boolean
    max_parallel_insert: number
    max_async: number
    [key: string]: any
  }
  pipeline_busy: boolean
  core_version?: string
  api_version?: string
  auth_mode?: 'enabled' | 'disabled'
}

export interface PipelineStatusResponse {
  autoscanned: boolean
  busy: boolean
  job_name: string
  job_start?: string
  docs: number
  batchs: number
  cur_batch: number
  request_pending: boolean
  cancellation_requested?: boolean
  latest_message: string
  history_messages?: string[]
}

export interface AuthStatusResponse {
  auth_configured: boolean
  access_token?: string
  token_type?: string
  auth_mode?: 'enabled' | 'disabled'
  message?: string
  core_version?: string
  api_version?: string
  webui_title?: string
  webui_description?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  auth_mode?: 'enabled' | 'disabled'
  message?: string
  core_version?: string
  api_version?: string
}

export interface DocActionResponse {
  status: 'success' | 'partial_success' | 'failure' | 'duplicated'
  message: string
  track_id?: string
}

export interface EntityUpdateResponse {
  status: string
  message: string
  data: Record<string, any>
}
