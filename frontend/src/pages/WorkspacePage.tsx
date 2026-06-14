import { useState } from "react"
import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import { Send, Loader2 } from "lucide-react"
import ReactMarkdown from "react-markdown"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
}

export default function WorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [input, setInput] = useState("")

  const { data: conversation, isLoading } = useQuery<Conversation>({
    queryKey: ["conversation", id],
    queryFn: async () => {
      if (id === "new") {
        return { id: "new", title: "New Conversation", messages: [] }
      }
      const { data } = await api.get(`/workspaces/conversations/${id}`)
      return data
    },
    enabled: !!id,
  })

  const sendMutation = useMutation({
    mutationFn: async (content: string) => {
      const { data } = await api.post(`/workspaces/conversations/${id}/messages`, {
        content,
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversation", id] })
      setInput("")
    },
    onError: (error: any) => {
      toast({
        title: "Failed to send message",
        description: error.response?.data?.detail,
        variant: "destructive",
      })
    },
  })

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    sendMutation.mutate(input)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 flex flex-col h-[calc(100vh-4rem)]">
      <h1 className="text-2xl font-bold mb-4">
        {conversation?.title || "Conversation"}
      </h1>

      <div className="flex-1 overflow-auto mb-4 space-y-4">
        {conversation?.messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            Start a conversation by typing a message below
          </div>
        ) : (
          conversation?.messages.map((msg) => (
            <Card
              key={msg.id}
              className={msg.role === "user" ? "ml-12" : "mr-12"}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">
                  {msg.role === "user" ? "You" : "Assistant"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {msg.role === "assistant" ? (
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm">{msg.content}</p>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <form onSubmit={handleSend} className="flex gap-4">
        <Input
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sendMutation.isPending}
          className="flex-1"
        />
        <Button type="submit" disabled={sendMutation.isPending || !input.trim()}>
          {sendMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </form>
    </div>
  )
}
