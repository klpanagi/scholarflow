import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  Group,
  Panel,
  Separator,
  useDefaultLayout,
} from "react-resizable-panels"
import { useStickToBottom } from "use-stick-to-bottom"
import {
  ArrowLeft,
  Bot,
  Loader2,
  Paperclip,
  Send,
  Square,
} from "lucide-react"

import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { useToast } from "@/hooks/use-toast"
import { useRevisionSession } from "@/hooks/useRevisionSession"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MarkdownRenderer } from "@/components/MarkdownRenderer"
import { EmptyState } from "@/components/revisions/EmptyState"
import { FilePreviewChip } from "@/components/revisions/FilePreviewChip"
import { WorkflowContextPanel } from "@/components/revisions/WorkflowContextPanel"
import type { WorkflowExecution } from "@/constants/workflows"

const PANEL_IDS = ["chat", "context"] as const
const PANEL_STORAGE_KEY = "revision-page-panels"

const PAPERCLIP_ACCEPT =
  ".pdf,.md,.txt,.docx,.png,.jpg,.jpeg,.gif,.webp"

function formatTokens(count: number): string {
  if (!Number.isFinite(count) || count <= 0) return "0"
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}K`
  return String(count)
}

function formatCost(usd: number): string {
  if (!Number.isFinite(usd) || usd <= 0) return "$0.0000"
  if (usd < 0.0001) return "<$0.0001"
  return `$${usd.toFixed(4)}`
}

interface AgentConfigResponse {
  id: string
  name?: string
  model: string
  provider: string
}

interface PaperSummary {
  id: string
  title?: string
}

export default function RevisionPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()

  const {
    session,
    messages,
    isLoading,
    isStreaming,
    streamingContent,
    loadSession,
    sendMessage,
    stopStreaming,
    attachedFiles,
    uploadFile,
    attachFile,
    removeAttachedFile,
    setAvailableStageIds,
    selectedStageIds,
    toggleStage,
  } = useRevisionSession()

  const [input, setInput] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { scrollRef, contentRef } = useStickToBottom({ initial: "smooth" })

  // Persist panel sizes to localStorage via react-resizable-panels v4's hook
  // (v4 dropped the old autoSaveId prop in favor of useDefaultLayout).
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({
    id: PANEL_STORAGE_KEY,
    panelIds: [...PANEL_IDS],
    storage: typeof window !== "undefined" ? window.localStorage : undefined,
  })

  const { data: execution, isLoading: executionLoading } = useQuery<WorkflowExecution | null>({
    queryKey: ["workflow-execution", session?.workflow_execution_id],
    queryFn: async () => {
      if (!session?.workflow_execution_id) return null
      const { data } = await api.get<WorkflowExecution>(
        `/workflows/results/${session.workflow_execution_id}`,
      )
      return data
    },
    enabled: !!session?.workflow_execution_id,
  })

  const { data: agentConfig } = useQuery<AgentConfigResponse | null>({
    queryKey: ["agent-config", session?.agent_config_id],
    queryFn: async () => {
      if (!session?.agent_config_id) return null
      const { data } = await api.get<AgentConfigResponse>(
        `/agents/configs/${session.agent_config_id}`,
      )
      return data
    },
    enabled: !!session?.agent_config_id,
  })

  const { data: paper } = useQuery<PaperSummary | null>({
    queryKey: ["paper-summary", execution?.paper_id],
    queryFn: async () => {
      if (!execution?.paper_id) return null
      const { data } = await api.get<PaperSummary>(`/papers/${execution.paper_id}`)
      return data
    },
    enabled: !!execution?.paper_id,
  })

  useEffect(() => {
    if (id) {
      void loadSession(id)
    }
  }, [id, loadSession])

  useEffect(() => {
    if (!execution) return
    const stageIds = execution.stages.map((_, i) => `stage-${i}`)
    setAvailableStageIds(stageIds)
  }, [execution, setAvailableStageIds])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [input])

  const { totalTokens, totalCostUsd } = useMemo(() => {
    let tokens = 0
    let cost = 0
    for (const msg of messages) {
      const usage = msg.extra_metadata?.usage as
        | { total_tokens?: number; cost_usd?: number }
        | undefined
      if (usage) {
        if (typeof usage.total_tokens === "number") tokens += usage.total_tokens
        if (typeof usage.cost_usd === "number") cost += usage.cost_usd
      }
    }
    return { totalTokens: tokens, totalCostUsd: cost }
  }, [messages])

  const hasTokenOrCostData = totalTokens > 0 || totalCostUsd > 0

  const handlePaperclipClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      try {
        const result = await uploadFile(file)
        attachFile(result)
        toast({
          title: "File attached",
          description: result.file_name,
        })
      } catch (err) {
        console.error("File upload failed:", err)
        toast({
          title: "Upload failed",
          description: err instanceof Error ? err.message : "Could not upload file",
          variant: "destructive",
        })
      } finally {
        if (fileInputRef.current) fileInputRef.current.value = ""
      }
    },
    [uploadFile, attachFile, toast],
  )

  const handleSend = useCallback(async () => {
    const content = input.trim()
    if (!content || isStreaming) return
    setInput("")
    if (textareaRef.current) textareaRef.current.style.height = "auto"
    const fileRefs = attachedFiles.map((f) => f.file_key)
    await sendMessage(content, fileRefs.length > 0 ? fileRefs : undefined)
  }, [input, isStreaming, sendMessage, attachedFiles])

  const handleSendPrompt = useCallback(
    (text: string) => {
      if (isStreaming) return
      const fileRefs = attachedFiles.map((f) => f.file_key)
      void sendMessage(text, fileRefs.length > 0 ? fileRefs : undefined)
    },
    [isStreaming, sendMessage, attachedFiles],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        void handleSend()
      }
    },
    [handleSend],
  )

  if (isLoading || !session) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const showEmptyState = messages.length === 0 && !isStreaming
  const lastIndex = messages.length - 1
  const hasStreamingDraft = isStreaming
  const canSend = !!input.trim() && !isStreaming

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-background">
      <Group
        orientation="horizontal"
        id={PANEL_STORAGE_KEY}
        defaultLayout={defaultLayout}
        onLayoutChanged={onLayoutChanged}
        className="flex-1 overflow-hidden"
      >
        <Panel
          id={PANEL_IDS[0]}
          defaultSize={70}
          minSize={30}
          className="flex flex-col h-full overflow-hidden"
        >
          <div className="border-b border-border/60 px-4 py-3 shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate("/workflows")}
                aria-label="Back to workflows"
                className="shrink-0"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div className="flex-1 min-w-0">
                <h1 className="text-sm font-semibold truncate">
                  {execution?.workflow_name ?? "Revision Session"}
                </h1>
                {paper?.title && (
                  <p
                    className="text-xs text-muted-foreground truncate"
                    title={paper.title}
                  >
                    {paper.title}
                  </p>
                )}
              </div>
              {agentConfig && (
                <Badge variant="secondary" className="text-[10px] shrink-0">
                  {agentConfig.model}
                </Badge>
              )}
              {hasTokenOrCostData && (
                <span className="text-[11px] text-muted-foreground shrink-0 tabular-nums">
                  {formatTokens(totalTokens)} tokens · {formatCost(totalCostUsd)}
                </span>
              )}
            </div>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto">
            <div ref={contentRef} className="px-4 py-6 space-y-6">
              {showEmptyState ? (
                <EmptyState onSendPrompt={handleSendPrompt} />
              ) : (
                <>
                  {messages.map((msg, i) => {
                    const isUser = msg.role === "user"
                    const isLastAssistant =
                      !isUser && i === lastIndex && hasStreamingDraft
                    const attachedFileNames = (
                      msg.extra_metadata as { file_names?: string[] } | null
                    )?.file_names

                    if (isUser) {
                      return (
                        <div key={msg.id} className="flex justify-end">
                          <div className="ml-12 max-w-[80%] rounded-2xl rounded-tr-md bg-primary text-primary-foreground px-4 py-2.5 shadow-sm">
                            <p className="text-sm whitespace-pre-wrap break-words">
                              {msg.content}
                            </p>
                            {Array.isArray(attachedFileNames) &&
                              attachedFileNames.length > 0 && (
                                <div className="mt-2 flex flex-wrap gap-1.5">
                                  {attachedFileNames.map((name) => (
                                    <span
                                      key={name}
                                      className="inline-flex items-center gap-1 rounded-full bg-primary-foreground/20 px-2 py-0.5 text-[10px]"
                                    >
                                      <Paperclip className="h-3 w-3" />
                                      <span className="truncate max-w-[140px]">
                                        {name}
                                      </span>
                                    </span>
                                  ))}
                                </div>
                              )}
                          </div>
                        </div>
                      )
                    }

                    return (
                      <div
                        key={msg.id}
                        className="flex justify-start gap-3"
                      >
                        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-1">
                          <Bot className="h-4 w-4 text-primary" />
                        </div>
                        <div className="mr-12 max-w-[80%] rounded-2xl rounded-tl-md bg-muted px-4 py-2.5 shadow-sm">
                          <MarkdownRenderer
                            content={msg.content}
                            streaming={isLastAssistant}
                          />
                        </div>
                      </div>
                    )
                  })}

                  {hasStreamingDraft && (
                    <div className="flex justify-start gap-3">
                      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-1">
                        <Bot className="h-4 w-4 text-primary" />
                      </div>
                      <div className="mr-12 max-w-[80%] rounded-2xl rounded-tl-md bg-muted px-4 py-2.5 shadow-sm">
                        {streamingContent ? (
                          <MarkdownRenderer
                            content={streamingContent}
                            streaming={true}
                          />
                        ) : (
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm">Thinking…</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="sticky bottom-0 bg-background border-t border-border/60 p-4 shrink-0">
            {attachedFiles.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-2">
                {attachedFiles.map((file, i) => (
                  <FilePreviewChip
                    key={`${file.file_key}-${i}`}
                    file={{
                      file_key: file.file_key,
                      file_name: file.file_name,
                    }}
                    onRemove={() => removeAttachedFile(i)}
                  />
                ))}
              </div>
            )}
            <div className="flex items-end gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept={PAPERCLIP_ACCEPT}
                onChange={handleFileChange}
                className="hidden"
                aria-hidden="true"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={handlePaperclipClick}
                disabled={isStreaming}
                aria-label="Attach file"
                title="Attach file"
              >
                <Paperclip className="h-4 w-4" />
              </Button>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question or request a revision… (Shift+Enter for new line)"
                rows={1}
                disabled={isStreaming}
                className={cn(
                  "flex-1 min-h-[44px] max-h-[200px] resize-none rounded-md border border-input bg-background px-3 py-2 text-sm",
                  "placeholder:text-muted-foreground",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                )}
              />
              {isStreaming ? (
                <Button
                  type="button"
                  variant="destructive"
                  size="icon"
                  onClick={stopStreaming}
                  aria-label="Stop generating"
                  title="Stop"
                >
                  <Square className="h-4 w-4" />
                </Button>
              ) : (
                <Button
                  type="button"
                  size="icon"
                  onClick={() => void handleSend()}
                  disabled={!canSend}
                  aria-label="Send message"
                  title="Send"
                >
                  <Send className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </Panel>

        <Separator className="w-1.5 bg-border/40 hover:bg-primary/40 transition-colors data-[resize-handle-state=drag]:bg-primary/60" />

        <Panel
          id={PANEL_IDS[1]}
          defaultSize={30}
          minSize={20}
          className="h-full overflow-hidden border-l border-border/60"
        >
          {execution ? (
            <WorkflowContextPanel
              execution={execution}
              selectedStageIds={selectedStageIds}
              onToggleStage={toggleStage}
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center text-muted-foreground gap-2 p-6">
              {executionLoading ? (
                <>
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <p className="text-sm">Loading workflow context…</p>
                </>
              ) : (
                <>
                  <Bot className="h-8 w-8 opacity-40" />
                  <p className="text-sm">No workflow context available</p>
                </>
              )}
            </div>
          )}
        </Panel>
      </Group>
    </div>
  )
}
