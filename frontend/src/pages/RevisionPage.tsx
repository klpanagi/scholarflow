import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useRevisionSession } from "@/hooks/useRevisionSession"
import { api } from "@/lib/api"
import { Send, Loader2, ArrowLeft, FileText, ChevronDown, ChevronUp, Square } from "lucide-react"
import ReactMarkdown from "react-markdown"

interface WorkflowStage {
  agent_role?: string
  agent_name?: string
  status: string
  output: string
  metadata?: Record<string, unknown>
}

interface WorkflowExecution {
  id: string
  workflow_id: string
  workflow_name: string
  input_text?: string
  stages: WorkflowStage[]
  status: string
  created_at: string
}

export default function RevisionPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const {
    session,
    messages,
    isLoading: sessionLoading,
    isStreaming,
    streamingContent,
    loadSession,
    sendMessage,
    stopStreaming,
  } = useRevisionSession()
  const [input, setInput] = useState("")
  const [showWorkflowContext, setShowWorkflowContext] = useState(false)

  const { data: workflow } = useQuery<WorkflowExecution>({
    queryKey: ["workflow-execution", session?.workflow_execution_id],
    queryFn: async () => {
      const { data } = await api.get(`/workflows/results`)
      return data.find((w: WorkflowExecution) => w.id === session?.workflow_execution_id)
    },
    enabled: !!session?.workflow_execution_id,
  })

  useEffect(() => {
    if (id) {
      loadSession(id)
    }
  }, [id, loadSession])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return
    const message = input
    setInput("")
    await sendMessage(message)
  }

  if (sessionLoading || !session) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 flex flex-col h-[calc(100vh-4rem)]">
      <div className="flex items-center gap-4 mb-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate("/workflows")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{session.title}</h1>
          <p className="text-sm text-muted-foreground">
            Discuss and revise the workflow results
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowWorkflowContext(!showWorkflowContext)}
        >
          <FileText className="h-4 w-4 mr-2" />
          Workflow Context
          {showWorkflowContext ? (
            <ChevronUp className="h-4 w-4 ml-2" />
          ) : (
            <ChevronDown className="h-4 w-4 ml-2" />
          )}
        </Button>
      </div>

      {showWorkflowContext && workflow && (
        <Card className="mb-4 max-h-64 overflow-auto">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Workflow Stages</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {workflow.stages.map((stage, i) => (
              <div key={i} className="border-l-2 border-primary/20 pl-3">
                <div className="text-xs font-medium text-muted-foreground">
                  Stage {i + 1}: {stage.agent_role || "Unknown"}
                  {stage.agent_name && ` — ${stage.agent_name}`}
                </div>
                <div className="text-sm mt-1 line-clamp-3">{stage.output}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="flex-1 overflow-auto mb-4 space-y-4">
        {messages.length === 0 && !isStreaming ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <FileText className="h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">Start discussing the review</p>
            <p className="text-sm">
              Ask questions, request revisions, or refine specific sections
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <Card
                key={msg.id}
                className={msg.role === "user" ? "ml-12" : "mr-12"}
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">
                    {msg.role === "user" ? "You" : "Revision Agent"}
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
            ))}

            {isStreaming && streamingContent && (
              <Card className="mr-12">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Revision Agent</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown>{streamingContent}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            )}

            {isStreaming && !streamingContent && (
              <div className="flex items-center gap-2 text-muted-foreground ml-4">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Thinking...</span>
              </div>
            )}
          </>
        )}
      </div>

      <form onSubmit={handleSend} className="flex gap-4">
        <Input
          placeholder="Ask a question or request a revision..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isStreaming}
          className="flex-1"
        />
        {isStreaming ? (
          <Button
            type="button"
            variant="destructive"
            onClick={stopStreaming}
          >
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button type="submit" disabled={!input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        )}
      </form>
    </div>
  )
}
