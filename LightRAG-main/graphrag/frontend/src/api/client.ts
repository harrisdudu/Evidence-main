import axios, { AxiosError } from 'axios'
import { useAuthStore } from '@/stores/auth'
import type {
  Document,
  DocsStatusesResponse,
  PaginatedDocsResponse,
  GraphData,
  QueryRequest,
  QueryResponse,
  HealthStatus,
  PipelineStatusResponse,
  AuthStatusResponse,
  LoginResponse,
  DocActionResponse,
  EntityUpdateResponse,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

// Create axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor to handle errors
apiClient.interceptors.response.use(
  (response) => {
    // Check for new token in response headers
    const newToken = response.headers['x-new-token']
    if (newToken) {
      useAuthStore.getState().login(newToken)
    }
    return response
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Documents API
export const documentsApi = {
  getAll: async (): Promise<DocsStatusesResponse> => {
    const response = await apiClient.get('/documents')
    return response.data
  },

  getPaginated: async (params: {
    page: number
    page_size: number
    status_filter?: string | null
    sort_field?: string
    sort_direction?: 'asc' | 'desc'
  }): Promise<PaginatedDocsResponse> => {
    const response = await apiClient.post('/documents/paginated', params)
    return response.data
  },

  upload: async (
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<DocActionResponse> => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress
        ? (e) => {
            const percent = Math.round((e.loaded * 100) / (e.total || 1))
            onProgress(percent)
          }
        : undefined,
    })
    return response.data
  },

  insertText: async (text: string): Promise<DocActionResponse> => {
    const response = await apiClient.post('/documents/text', { text })
    return response.data
  },

  scan: async (): Promise<{ status: string; message: string; track_id: string }> => {
    const response = await apiClient.post('/documents/scan')
    return response.data
  },

  delete: async (
    ids: string[],
    deleteFile: boolean = false,
    deleteLLMCache: boolean = false
  ): Promise<{ status: string; message: string }> => {
    const response = await apiClient.delete('/documents/delete_document', {
      data: {
        doc_ids: ids,
        delete_file: deleteFile,
        delete_llm_cache: deleteLLMCache,
      },
    })
    return response.data
  },

  clear: async (): Promise<DocActionResponse> => {
    const response = await apiClient.delete('/documents')
    return response.data
  },

  getPipelineStatus: async (): Promise<PipelineStatusResponse> => {
    const response = await apiClient.get('/documents/pipeline_status')
    return response.data
  },

  cancelPipeline: async (): Promise<{ status: string; message: string }> => {
    const response = await apiClient.post('/documents/cancel_pipeline')
    return response.data
  },
}

// Graph API
export const graphApi = {
  query: async (
    label: string,
    maxDepth: number = 3,
    maxNodes: number = 1000
  ): Promise<GraphData> => {
    const response = await apiClient.get(
      `/graphs?label=${encodeURIComponent(label)}&max_depth=${maxDepth}&max_nodes=${maxNodes}`
    )
    return response.data
  },

  getLabels: async (): Promise<string[]> => {
    const response = await apiClient.get('/graph/label/list')
    return response.data
  },

  searchLabels: async (query: string, limit: number = 50): Promise<string[]> => {
    const response = await apiClient.get(
      `/graph/label/search?q=${encodeURIComponent(query)}&limit=${limit}`
    )
    return response.data
  },

  updateEntity: async (
    entityName: string,
    data: Record<string, any>,
    allowRename: boolean = false
  ): Promise<EntityUpdateResponse> => {
    const response = await apiClient.post('/graph/entity/edit', {
      entity_name: entityName,
      updated_data: data,
      allow_rename: allowRename,
    })
    return response.data
  },
}

// Query API
export const queryApi = {
  search: async (params: QueryRequest): Promise<QueryResponse> => {
    const response = await apiClient.post('/query', params)
    return response.data
  },

  stream: async (
    params: QueryRequest,
    onChunk: (chunk: string) => void,
    onError?: (error: string) => void
  ): Promise<void> => {
    const token = useAuthStore.getState().token
    const response = await fetch(`${API_BASE_URL}/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/x-ndjson',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(params),
    })

    if (!response.ok) {
      if (response.status === 401) {
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return
      }
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('Response body is null')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.trim()) {
            try {
              const parsed = JSON.parse(line)
              if (parsed.response) {
                onChunk(parsed.response)
              } else if (parsed.error && onError) {
                onError(parsed.error)
              }
            } catch (e) {
              console.error('Failed to parse stream chunk:', e)
            }
          }
        }
      }

      // Process remaining buffer
      if (buffer.trim()) {
        try {
          const parsed = JSON.parse(buffer)
          if (parsed.response) {
            onChunk(parsed.response)
          } else if (parsed.error && onError) {
            onError(parsed.error)
          }
        } catch (e) {
          console.error('Failed to parse final chunk:', e)
        }
      }
    } finally {
      reader.releaseLock()
    }
  },
}

// Auth API
export const authApi = {
  getStatus: async (): Promise<AuthStatusResponse> => {
    const response = await apiClient.get('/auth-status')
    return response.data
  },

  login: async (username: string, password: string): Promise<LoginResponse> => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const response = await apiClient.post('/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

// Health API
export const healthApi = {
  check: async (): Promise<HealthStatus> => {
    const response = await apiClient.get('/health')
    return response.data
  },
}
