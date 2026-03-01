// Evidence Chain API - Based on technical specification
// Reference: docs/evidence_chain_frontend_design.md

import axios from 'axios'
import { backendBaseUrl } from '@/lib/constants'
import {
  EvidenceQueryParams,
  EvidenceQueryResponse,
  EvidenceStats,
  EvidenceEntity,
  EvidenceGraphData,
  ApiResponse,
} from '@/types/evidence'

// Create axios instance with auth
const createApiClient = () => {
  const client = axios.create({
    baseURL: backendBaseUrl,
    timeout: 30000,
  })

  // Add auth token to requests
  client.interceptors.request.use((config) => {
    const token = localStorage.getItem('LIGHTRAG-API-TOKEN')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  return client
}

const apiClient = createApiClient()

// Evidence Chain API
export const evidenceApi = {
  // Query evidence chains
  query: async (params: EvidenceQueryParams): Promise<EvidenceQueryResponse> => {
    const response = await apiClient.post<ApiResponse<EvidenceQueryResponse>>(
      '/evidence/query',
      params
    )
    return response.data.data
  },

  // Get evidence statistics
  getStats: async (params?: { scene_tag?: string }): Promise<EvidenceStats> => {
    const response = await apiClient.get<ApiResponse<EvidenceStats>>('/evidence/stats', {
      params,
    })
    return response.data.data
  },

  // Get entity details
  getEntity: async (entityName: string): Promise<EvidenceEntity> => {
    const encodedName = encodeURIComponent(entityName)
    const response = await apiClient.get<ApiResponse<EvidenceEntity>>(
      `/evidence/entity/${encodedName}`
    )
    return response.data.data
  },

  // Get evidence chain details
  getChain: async (chainId: string): Promise<any> => {
    const response = await apiClient.get<ApiResponse<any>>(`/evidence/chain/${chainId}`)
    return response.data.data
  },

  // Get visualization data
  getVisualize: async (params: {
    entity_name?: string
    depth?: number
    evidence_levels?: string[]
    relation_types?: string[]
  }): Promise<EvidenceGraphData> => {
    const response = await apiClient.post<ApiResponse<EvidenceGraphData>>(
      '/evidence/visualize',
      params
    )
    return response.data.data
  },

  // Get entities by evidence level (direct Neo4j query)
  getEntitiesByLevel: async (level: string, limit: number = 100): Promise<any[]> => {
    const response = await apiClient.get('/kg/entities/by-evidence-level', {
      params: { level, limit },
    })
    return response.data
  },

  // Get relations by evidence level
  getRelationsByLevel: async (level: string, limit: number = 100): Promise<any[]> => {
    const response = await apiClient.get('/kg/relations/by-evidence-level', {
      params: { level, limit },
    })
    return response.data
  },

  // Get relations by type
  getRelationsByType: async (type: string, limit: number = 100): Promise<any[]> => {
    const response = await apiClient.get('/kg/relations/by-type', {
      params: { type, limit },
    })
    return response.data
  },

  // Get entities by evidence level and scene
  getEntitiesByLevelAndScene: async (
    level: string,
    scene: string,
    limit: number = 100
  ): Promise<any[]> => {
    const response = await apiClient.get('/kg/entities/by-level-and-scene', {
      params: { level, scene, limit },
    })
    return response.data
  },

  // Get support/contradict evidence
  getSupportContradict: async (
    entityName: string,
    minCount: number = 1
  ): Promise<{
    support_evidence: any[]
    contradict_evidence: any[]
    support_count: number
    contradict_count: number
  }> => {
    const encodedName = encodeURIComponent(entityName)
    const response = await apiClient.get(`/kg/evidence/support-contradict/${encodedName}`, {
      params: { min_count: minCount },
    })
    return response.data
  },

  // Aggregate evidence
  aggregateEvidence: async (params: {
    entity_name?: string
    evidence_level?: string
    min_count?: number
  }): Promise<any> => {
    const response = await apiClient.post('/kg/evidence/aggregate', params)
    return response.data
  },
}

export default evidenceApi
