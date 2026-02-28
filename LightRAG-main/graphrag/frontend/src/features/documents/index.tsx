import { useEffect, useState } from 'react'
import { useDocumentStore } from '@/stores/documents'
import { documentsApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Checkbox } from '@/components/ui/checkbox'
import { toast } from 'sonner'
import { RefreshCw, Upload, Trash2, Scan } from 'lucide-react'

export default function DocumentsPage() {
  const { documents, setDocuments, selectedIds, toggleSelection, clearSelection } = useDocumentStore()
  const [loading, setLoading] = useState(false)

  const fetchDocuments = async () => {
    setLoading(true)
    try {
      const data = await documentsApi.getAll()
      const allDocs = Object.values(data.statuses).flat()
      setDocuments(allDocs)
    } catch (error) {
      toast.error('Failed to fetch documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
    const interval = setInterval(fetchDocuments, 5000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-500',
      processing: 'bg-blue-500',
      preprocessed: 'bg-purple-500',
      processed: 'bg-green-500',
      failed: 'bg-red-500',
    }
    return colors[status] || 'bg-gray-500'
  }

  const handleDelete = async () => {
    if (selectedIds.size === 0) return
    try {
      await documentsApi.delete(Array.from(selectedIds))
      toast.success('Documents deleted')
      clearSelection()
      fetchDocuments()
    } catch (error) {
      toast.error('Failed to delete documents')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Documents</h2>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchDocuments} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" onClick={() => documentsApi.scan()}>
            <Scan className="mr-2 h-4 w-4" />
            Scan
          </Button>
          <Button>
            <Upload className="mr-2 h-4 w-4" />
            Upload
          </Button>
          {selectedIds.size > 0 && (
            <Button variant="destructive" onClick={handleDelete}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete ({selectedIds.size})
            </Button>
          )}
        </div>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox
                  checked={selectedIds.size === documents.length && documents.length > 0}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      useDocumentStore.getState().selectAll(documents.map((d) => d.id))
                    } else {
                      clearSelection()
                    }
                  }}
                />
              </TableHead>
              <TableHead>File Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Chunks</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.map((doc) => (
              <TableRow key={doc.id}>
                <TableCell>
                  <Checkbox
                    checked={selectedIds.has(doc.id)}
                    onCheckedChange={() => toggleSelection(doc.id)}
                  />
                </TableCell>
                <TableCell className="font-medium">
                  {doc.file_path.split('/').pop()}
                </TableCell>
                <TableCell>
                  <Badge className={getStatusColor(doc.status)}>{doc.status}</Badge>
                </TableCell>
                <TableCell>{doc.chunks_count || '-'}</TableCell>
                <TableCell>{new Date(doc.created_at).toLocaleDateString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
