import { create } from 'zustand'
import { createSelectors } from '@/lib/utils'
import { DirectedGraph } from 'graphology'

export interface GraphNode {
  id: string
  labels: string[]
  properties: Record<string, any>
  x?: number
  y?: number
  color?: string
  size?: number
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type?: string
  properties: Record<string, any>
}

export interface RawGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

interface GraphState {
  nodes: GraphNode[]
  edges: GraphEdge[]
  selectedNode: string | null
  focusedNode: string | null
  selectedEdge: string | null
  focusedEdge: string | null
  sigmaGraph: DirectedGraph | null
  isLoading: boolean
  graphIsEmpty: boolean
  
  setNodes: (nodes: GraphNode[]) => void
  setEdges: (edges: GraphEdge[]) => void
  setSelectedNode: (id: string | null) => void
  setFocusedNode: (id: string | null) => void
  setSelectedEdge: (id: string | null) => void
  setFocusedEdge: (id: string | null) => void
  setSigmaGraph: (graph: DirectedGraph | null) => void
  setLoading: (loading: boolean) => void
  setGraphIsEmpty: (isEmpty: boolean) => void
  clearSelection: () => void
  reset: () => void
}

const useGraphStoreBase = create<GraphState>((set) => ({
  nodes: [],
  edges: [],
  selectedNode: null,
  focusedNode: null,
  selectedEdge: null,
  focusedEdge: null,
  sigmaGraph: null,
  isLoading: false,
  graphIsEmpty: false,
  
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  setSelectedNode: (id) => set({ selectedNode: id }),
  setFocusedNode: (id) => set({ focusedNode: id }),
  setSelectedEdge: (id) => set({ selectedEdge: id }),
  setFocusedEdge: (id) => set({ focusedEdge: id }),
  setSigmaGraph: (graph) => set({ sigmaGraph: graph }),
  setLoading: (loading) => set({ isLoading: loading }),
  setGraphIsEmpty: (isEmpty) => set({ graphIsEmpty: isEmpty }),
  
  clearSelection: () =>
    set({
      selectedNode: null,
      focusedNode: null,
      selectedEdge: null,
      focusedEdge: null,
    }),
  
  reset: () =>
    set({
      nodes: [],
      edges: [],
      selectedNode: null,
      focusedNode: null,
      selectedEdge: null,
      focusedEdge: null,
      sigmaGraph: null,
      isLoading: false,
      graphIsEmpty: false,
    }),
}))

export const useGraphStore = createSelectors(useGraphStoreBase)
