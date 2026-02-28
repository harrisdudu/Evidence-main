import { useState, useRef, useEffect } from 'react'
import { queryApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { Send, Trash2 } from 'lucide-react'
import type { QueryMode, Message } from '@/api/types'

export default function RetrievalPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<QueryMode>('mix')
  const [isStreaming, setIsStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return

    const userMessage: Message = { role: 'user', content: input }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)

    let assistantContent = ''

    try {
      await queryApi.stream(
        {
          query: input,
          mode,
          stream: true,
          conversation_history: messages,
        },
        (chunk) => {
          assistantContent += chunk
          setMessages((prev) => {
            const newMessages = [...prev]
            const lastMsg = newMessages[newMessages.length - 1]
            if (lastMsg && lastMsg.role === 'assistant') {
              lastMsg.content = assistantContent
            } else {
              newMessages.push({ role: 'assistant', content: assistantContent })
            }
            return newMessages
          })
        },
        (error) => {
          toast.error(error)
        }
      )
    } catch (error) {
      toast.error('Query failed')
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Retrieval Testing</h2>
        <div className="flex items-center gap-2">
          <Select value={mode} onValueChange={(v) => setMode(v as QueryMode)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="naive">Naive</SelectItem>
              <SelectItem value="local">Local</SelectItem>
              <SelectItem value="global">Global</SelectItem>
              <SelectItem value="hybrid">Hybrid</SelectItem>
              <SelectItem value="mix">Mix</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={() => setMessages([])}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Card className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            Start a conversation...
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  <pre className="whitespace-pre-wrap font-sans text-sm">
                    {msg.content}
                  </pre>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </Card>

      <div className="flex gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="Type your query..."
          className="min-h-[80px] flex-1"
          disabled={isStreaming}
        />
        <Button
          onClick={handleSend}
          disabled={!input.trim() || isStreaming}
          className="h-auto px-6"
        >
          <Send className="mr-2 h-4 w-4" />
          Send
        </Button>
      </div>
    </div>
  )
}
