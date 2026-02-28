import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { Zap, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { login } = useAuthStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username || !password) {
      toast.error('Please enter username and password')
      return
    }

    setLoading(true)
    try {
      const response = await authApi.login(username, password)
      login(
        response.access_token,
        response.auth_mode === 'disabled',
        username,
        response.core_version,
        response.api_version
      )
      toast.success('Login successful')
      navigate('/')
    } catch (error) {
      toast.error('Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen w-full items-center justify-center bg-gradient-to-br from-emerald-50 to-teal-100 dark:from-gray-900 dark:to-gray-800">
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center gap-2">
            <Zap className="h-8 w-8 text-emerald-500" />
          </div>
          <CardTitle className="text-center text-2xl">GraphRAG</CardTitle>
          <CardDescription className="text-center">
            Enter your credentials to access the system
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Logging in...
                </>
              ) : (
                'Login'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
