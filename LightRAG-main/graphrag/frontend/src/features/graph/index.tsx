import { useEffect, useState } from 'react'
import { SigmaContainer, useRegisterEvents, useSigma } from '@react-sigma/core'
import { useLayoutForceAtlas2 } from '@react-sigma/layout-forceatlas2'
import { Settings as SigmaSettings } from 'sigma/settings'
import { NodeBorderProgram } from '@sigma/node-border'
import { createEdgeCurveProgram } from '@sigma/edge-curve'
import { useGraphStore } from '@/stores/graph'
import { graphApi } from '@/api/client'
import { toast } from 'sonner'
import '@react-sigma/core/lib/style.css'

const createSigmaSettings = (isDark: boolean): Partial<SigmaSettings> => ({
  allowInvalidContainer: true,
  defaultNodeType: 'border',
  defaultEdgeType: 'curvedNoArrow',
  renderEdgeLabels: false,
  nodeProgramClasses: {
    border: NodeBorderProgram,
  },
  edgeProgramClasses: {
    curvedNoArrow: createEdgeCurveProgram(),
  },
  labelColor: {
    color: isDark ? '#ffffff' : '#000000',
  },
  enableEdgeEvents: true,
})

const GraphEvents = () => {
  const registerEvents = useRegisterEvents()
  const sigma = useSigma()
  const { setSelectedNode, setFocusedNode } = useGraphStore()

  useEffect(() => {
    registerEvents({
      clickNode: (event) => {
        setSelectedNode(event.node)
      },
      enterNode: (event) => {
        setFocusedNode(event.node)
      },
      leaveNode: () => {
        setFocusedNode(null)
      },
      clickStage: () => {
        setSelectedNode(null)
      },
    })
  }, [registerEvents, sigma])

  return null
}

export default function GraphPage() {
  const [isDark] = useState(false)
  const { nodes, edges, setNodes, setEdges, isLoading, setLoading } = useGraphStore()

  const sigmaSettings = createSigmaSettings(isDark)
  const { assign } = useLayoutForceAtlas2({ iterations: 50 })

  const fetchGraph = async (label: string = '*') => {
    setLoading(true)
    try {
      const data = await graphApi.query(label, 3, 1000)
      setNodes(data.nodes)
      setEdges(data.edges)
    } catch (error) {
      toast.error('Failed to load graph')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchGraph()
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Knowledge Graph</h2>
        <div className="flex gap-2">
          <Button onClick={() => fetchGraph()}>Refresh</Button>
          <Button onClick={assign}>Layout</Button>
        </div>
      </div>

      <div className="relative h-[calc(100vh-12rem)] w-full overflow-hidden rounded-lg border">
        <SigmaContainer settings={sigmaSettings} className="!bg-background !size-full">
          <GraphEvents />
          
          <div className="absolute bottom-4 left-4 z-10 flex gap-2">
            <Button variant="outline" size="sm" onClick={assign}>Force Atlas</Button>
          </div>
        </SigmaContainer>

        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80">
            <div className="text-center">
              <div className="mb-2 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
              <p>Loading graph...</p>
            </div>
          </div>
        )}
      </div>

      <div className="text-sm text-muted-foreground">
        Nodes: {nodes.length} | Edges: {edges.length}
      </div>
    </div>
  )
}

import { Button } from '@/components/ui/button'
