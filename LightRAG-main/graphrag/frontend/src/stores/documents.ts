import { create } from 'zustand'
import { createSelectors } from '@/lib/utils'

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

interface DocumentState {
  documents: Document[]
  isLoading: boolean
  selectedIds: Set<string>
  statusCounts: Record<string, number>
  
  setDocuments: (docs: Document[]) => void
  addDocument: (doc: Document) => void
  updateDocument: (id: string, updates: Partial<Document>) => void
  deleteDocuments: (ids: string[]) => void
  toggleSelection: (id: string) => void
  selectAll: (ids: string[]) => void
  clearSelection: () => void
  setStatusCounts: (counts: Record<string, number>) => void
  setLoading: (loading: boolean) => void
}

const useDocumentStoreBase = create<DocumentState>((set, get) => ({
  documents: [],
  isLoading: false,
  selectedIds: new Set(),
  statusCounts: {},
  
  setDocuments: (docs) => set({ documents: docs }),
  
  addDocument: (doc) =>
    set((state) => ({
      documents: [...state.documents, doc],
    })),
  
  updateDocument: (id, updates) =>
    set((state) => ({
      documents: state.documents.map((d) =>
        d.id === id ? { ...d, ...updates } : d
      ),
    })),
  
  deleteDocuments: (ids) =>
    set((state) => ({
      documents: state.documents.filter((d) => !ids.includes(d.id)),
      selectedIds: new Set(
        [...state.selectedIds].filter((id) => !ids.includes(id))
      ),
    })),
  
  toggleSelection: (id) =>
    set((state) => {
      const newIds = new Set(state.selectedIds)
      if (newIds.has(id)) {
        newIds.delete(id)
      } else {
        newIds.add(id)
      }
      return { selectedIds: newIds }
    }),
  
  selectAll: (ids) => set({ selectedIds: new Set(ids) }),
  
  clearSelection: () => set({ selectedIds: new Set() }),
  
  setStatusCounts: (counts) => set({ statusCounts: counts }),
  
  setLoading: (loading) => set({ isLoading: loading }),
}))

export const useDocumentStore = createSelectors(useDocumentStoreBase)
