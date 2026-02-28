import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { documentsApi, healthApi } from '@/api/client'
import { FileText, GitGraph, Activity, CheckCircle, XCircle, Clock } from 'lucide-react'

interface Stats {
  documents: {
    total: number
    processed: number
    pending: number
    failed: number
  }
  health: {
    status: string
    version: string
  }
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [docs, health] = await Promise.all([
          documentsApi.getAll(),
          healthApi.check(),
        ])

        const allDocs = Object.values(docs.statuses).flat()
        setStats({
          documents: {
            total: allDocs.length,
            processed: docs.statuses.processed?.length || 0,
            pending:
              (docs.statuses.pending?.length || 0) +
              (docs.statuses.processing?.length || 0),
            failed: docs.statuses.failed?.length || 0,
          },
          health: {
            status: health.status,
            version: health.core_version || 'unknown',
          },
        })
      } catch (error) {
        console.error('Failed to fetch stats:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="mb-2 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
          <p>Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.documents.total}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Processed</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.documents.processed}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.documents.pending}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.documents.failed}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              System Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status:</span>
                <span className="font-medium text-green-500">
                  {stats?.health.status}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Version:</span>
                <span className="font-medium">{stats?.health.version}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitGraph className="h-5 w-5" />
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Use the sidebar to navigate to different sections:
              </p>
              <ul className="list-disc list-inside text-sm text-muted-foreground">
                <li>Documents - Manage and upload documents</li>
                <li>Knowledge Graph - Visualize entity relationships</li>
                <li>Retrieval - Test RAG queries</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
