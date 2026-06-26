import { useState, useEffect, useMemo, useCallback } from 'react'
import { useChat } from '@/hooks/useChat'
import { useToast } from '@/hooks/use-toast'
import { PageHeader } from '@/components/shared/PageHeader'
import { MessageList } from '@/components/chat/MessageList'
import { ChatInput } from '@/components/chat/ChatInput'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Plus,
  Trash2,
  MessageSquare,
  Menu,
  Sparkles,
  BookOpen,
  FileText,
  Beaker,
  GraduationCap,
  Square,
  Bot,
  GitFork,
  ChevronDown,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { AgentPicker } from '@/components/chat/AgentPicker'
import { AssetPicker } from '@/components/chat/AssetPicker'
import type { ChatListMessage } from '@/components/chat/MessageList'

/* ────────────────────────────────────────────── */
/*  Constants                                      */
/* ────────────────────────────────────────────── */

const SUGGESTIONS = [
  { icon: Sparkles, label: 'Summarize a paper', query: 'Can you summarize a research paper for me? I have the PDF ready.' },
  { icon: BookOpen, label: 'Literature review', query: 'Help me conduct a literature review on recent advances in...' },
  { icon: FileText, label: 'Write an abstract', query: 'Help me write an abstract for my paper about...' },
  { icon: Beaker, label: 'Research methods', query: 'What research methods would you recommend for studying...' },
  { icon: GraduationCap, label: 'Thesis outline', query: 'Help me create a detailed thesis outline for...' },
]

/* ────────────────────────────────────────────── */
/*  Helpers                                        */
/* ────────────────────────────────────────────── */

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60_000)
  const diffHours = Math.floor(diffMs / 3_600_000)
  const diffDays = Math.floor(diffMs / 86_400_000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

/* ────────────────────────────────────────────── */
/*  Component                                      */
/* ────────────────────────────────────────────── */

export default function ChatPage() {
  const {
    sessions,
    currentSession,
    messages,
    isStreaming,
    streamingContent,
    fetchSessions,
    createSession,
    deleteSession,
    clearAllSessions,
    selectSession,
    sendMessage,
    stopStreaming,
    forkSession,
    updateSession,
    uploadFile,
  } = useChat()

  const { toast } = useToast()

  /* ── UI state ── */
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [newSessionOpen, setNewSessionOpen] = useState(false)
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false)
  const [showAgentPicker, setShowAgentPicker] = useState(false)

  /* ── New session form ── */
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [selectedAssets, setSelectedAssets] = useState<string[]>([])
  const [newTitle, setNewTitle] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')

  /* ── Effects ── */
  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  /* ── Map messages → ChatListMessage ── */
  const chatMessages = useMemo<ChatListMessage[]>(() => {
    const mapped: ChatListMessage[] = messages.map((msg) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp,
      model: msg.role === 'assistant' ? currentSession?.model : undefined,
      provider: msg.role === 'assistant' ? currentSession?.provider : undefined,
    }))

    // During streaming, append a synthetic assistant message with partial content
    if (isStreaming) {
      mapped.push({
        id: 'streaming-msg',
        role: 'assistant',
        content: streamingContent || '',
        timestamp: new Date().toISOString(),
        model: currentSession?.model,
        provider: currentSession?.provider,
      })
    }

    return mapped
  }, [messages, isStreaming, streamingContent, currentSession])

  /* ── Handlers ── */

  const openNewSession = useCallback(() => {
    setSelectedAgentId(null)
    setSelectedAssets([])
    setNewTitle('')
    setSystemPrompt('')
    setNewSessionOpen(true)
  }, [])

  const handleCreateSession = useCallback(async () => {
    if (!selectedAgentId) {
      toast({
        title: 'Select an agent',
        description: 'Choose an agent for this conversation.',
      })
      return
    }
    try {
      await createSession({
        agentConfigId: selectedAgentId,
        assetIds: selectedAssets.length > 0 ? selectedAssets : undefined,
        title: newTitle || undefined,
        systemPrompt: systemPrompt || undefined,
      })
      setNewSessionOpen(false)
      setNewTitle('')
      setSystemPrompt('')
      setSelectedAgentId(null)
      setSelectedAssets([])
    } catch {
      toast({ title: 'Error', description: 'Failed to create session.' })
    }
  }, [selectedAgentId, selectedAssets, newTitle, systemPrompt, createSession, toast])

  const handleSelectSession = useCallback(
    (session: (typeof sessions)[number]) => {
      selectSession(session)
      setSidebarOpen(false)
    },
    [selectSession],
  )

  const handleDeleteSession = useCallback(
    (e: React.MouseEvent, sessionId: string) => {
      e.stopPropagation()
      deleteSession(sessionId)
    },
    [deleteSession],
  )

  const handleClearAll = useCallback(async () => {
    if (sessions.length === 0) {
      setClearConfirmOpen(false)
      return
    }
    const deleted = await clearAllSessions()
    setClearConfirmOpen(false)
    if (deleted < 0) {
      toast({
        title: 'Error',
        description: 'Failed to clear conversations. Please try again.',
        variant: 'destructive',
      })
      return
    }
    if (deleted === 0) {
      toast({
        title: 'No conversations cleared',
        description: 'No conversations were deleted.',
      })
      return
    }
    toast({
      title: 'Conversations cleared',
      description: `${deleted} conversation${deleted === 1 ? '' : 's'} deleted.`,
    })
  }, [sessions, clearAllSessions, toast])

  const handleAgentSwitch = useCallback(async (agentId: string) => {
    if (!currentSession) return
    const updated = await updateSession(currentSession.id, { agentConfigId: agentId })
    if (updated) {
      toast({ title: 'Agent switched', description: `Now using ${updated.model} (${updated.provider}).` })
    } else {
      toast({ title: 'Error', description: 'Failed to switch agent.', variant: 'destructive' })
    }
    setShowAgentPicker(false)
  }, [currentSession, updateSession, toast])

  const handleSend = useCallback(
    async (content: string, files?: File[]) => {
      if (!currentSession) return

      let finalContent = content
      if (files && files.length > 0) {
        const references: string[] = []
        for (const file of files) {
          try {
            const result = await uploadFile(file)
            if (result) {
              references.push(`[Attached: ${result.file_name}]`)
            }
          } catch {
            toast({
              title: 'Upload failed',
              description: `Could not upload ${file.name}.`,
            })
          }
        }
        if (references.length > 0) {
          finalContent = content + '\n\n' + references.join('\n')
        }
      }

      await sendMessage(finalContent)
    },
    [currentSession, sendMessage, uploadFile, toast],
  )

  const handleFork = useCallback(async () => {
    if (!currentSession || messages.length === 0) return
    const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant')
    if (!lastAssistant) return
    try {
      await forkSession(lastAssistant.id)
      toast({
        title: 'Session forked',
        description: 'A new session was created from this conversation.',
      })
    } catch {
      toast({ title: 'Error', description: 'Failed to fork session.' })
    }
  }, [currentSession, messages, forkSession, toast])

  const handleSuggestionClick = useCallback(
    (query: string) => {
      if (!currentSession) {
        openNewSession()
        return
      }
      sendMessage(query)
    },
    [currentSession, sendMessage, openNewSession],
  )

  /* ── Render: Sidebar content (shared by desktop + mobile) ── */

  const sidebarContent = (
    <>
      {/* New conversation button */}
      <div className="p-3">
        <Button
          onClick={openNewSession}
          className={cn(
            'w-full gap-2 bg-gradient-to-r from-primary to-primary',
            'text-primary-foreground hover:from-primary/90 hover:to-primary/80',
            'shadow-sm transition-all duration-200',
          )}
          size="default"
        >
          <Plus aria-hidden="true" className="h-4 w-4" />
          New Conversation
        </Button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 dark:scrollbar-thumb-muted-foreground/30">
        {sessions.length === 0 && (
          <div className="flex flex-col items-center gap-2 px-4 py-12 text-center">
            <MessageSquare aria-hidden="true" className="h-8 w-8 text-muted-foreground/20" />
            <p className="text-xs text-muted-foreground/40">No conversations yet</p>
          </div>
        )}
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => handleSelectSession(session)}
            className={cn(
              'group relative w-full text-left px-3 py-3 transition-all duration-150',
              'hover:bg-accent/50',
              currentSession?.id === session.id &&
                'bg-primary/5 border-l-2 border-primary',
            )}
          >
            <div className="flex items-start gap-2.5">
              <MessageSquare
                aria-hidden="true"
                className={cn(
                  'mt-0.5 h-4 w-4 shrink-0',
                  currentSession?.id === session.id
                    ? 'text-primary'
                    : 'text-muted-foreground/30 group-hover:text-muted-foreground/50',
                )}
              />
              <div className="flex-1 min-w-0">
                <p
                  className={cn(
                    'text-sm font-medium truncate leading-tight',
                    currentSession?.id === session.id && 'text-primary dark:text-primary',
                  )}
                >
                  {session.title || 'Untitled'}
                </p>
                <p className="text-[11px] text-muted-foreground/40 mt-1">
                  {formatRelativeTime(session.updated_at)}
                </p>
              </div>
              <button
                onClick={(e) => handleDeleteSession(e, session.id)}
                className={cn(
                  'absolute right-2 top-3 flex h-6 w-6 items-center justify-center rounded-md',
                  'opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity',
                  'text-muted-foreground/30 hover:text-destructive hover:bg-destructive/10',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                )}
                aria-label={`Delete session "${session.title || 'Untitled'}"`}
              >
                <Trash2 aria-hidden="true" className="h-3.5 w-3.5" />
              </button>
            </div>
          </button>
        ))}
      </div>

      {/* Clear all button */}
      {sessions.length > 0 && (
        <div className="border-t border-border/40 p-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setClearConfirmOpen(true)}
            className="w-full gap-2 text-muted-foreground/50 hover:text-destructive text-xs"
          >
            <Trash2 aria-hidden="true" className="h-3.5 w-3.5" />
            Clear all conversations
          </Button>
        </div>
      )}
    </>
  )

  /* ── Render: Welcome / suggestion chips ── */

  const suggestionChips = (
    <div className="flex flex-col items-center justify-center flex-1 px-4 py-12">
      <div className="flex flex-col items-center gap-4 text-center max-w-lg">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/15 to-primary/10 ring-1 ring-primary/20">
          <Bot aria-hidden="true" className="h-8 w-8 text-primary" />
        </div>
        <div className="space-y-2">
          <h2 className="font-display text-2xl font-semibold tracking-tight text-foreground">
            Intelligence Chat
          </h2>
          <p className="text-sm text-muted-foreground/60 leading-relaxed">
            Your AI-powered academic assistant. Ask questions, get summaries, and explore research.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full mt-4">
          {SUGGESTIONS.map((suggestion) => {
            const Icon = suggestion.icon
            return (
              <button
                key={suggestion.label}
                onClick={() => handleSuggestionClick(suggestion.query)}
                className={cn(
                  'flex items-center gap-3 rounded-xl px-4 py-3 text-left',
                  'bg-card/50 backdrop-blur-sm border border-border/40',
                  'hover:bg-primary/5 hover:border-primary/20',
                  'transition-all duration-200 group',
                )}
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary/15 transition-colors">
                  <Icon aria-hidden="true" className="h-4 w-4" />
                </div>
                <span className="text-sm font-medium text-foreground/70 group-hover:text-foreground transition-colors">
                  {suggestion.label}
                </span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )

  /* ── Render: Session header ── */

  const sessionHeader = currentSession && (
    <div className="flex items-center justify-between border-b border-border/40 px-4 lg:px-6 h-14 shrink-0 bg-card/20 backdrop-blur-sm">
      <div className="flex items-center gap-3 min-w-0">
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden -ml-2.5 h-10 w-10 shrink-0"
            aria-label="Open conversations"
          >
            <Menu aria-hidden="true" className="h-4 w-4" />
          </Button>
        </SheetTrigger>
        <h2 className="text-sm font-semibold truncate">
          {currentSession.title || 'Untitled'}
        </h2>
        <Badge
          variant="outline"
          className="hidden sm:inline-flex text-[10px] px-1.5 py-0 h-5 border-primary/20 text-primary dark:text-primary bg-primary/5 leading-none"
        >
          {currentSession.provider}
        </Badge>
        <Badge
          variant="secondary"
          className="hidden sm:inline-flex text-[10px] px-1.5 py-0 h-5 leading-none"
        >
          {currentSession.model}
        </Badge>
      </div>

        <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleFork}
          className="text-xs gap-1.5 text-muted-foreground/50 hover:text-foreground h-8"
          disabled={messages.length === 0}
        >
          <GitFork aria-hidden="true" className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Fork</span>
        </Button>
        <Popover open={showAgentPicker} onOpenChange={setShowAgentPicker}>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs gap-1 text-muted-foreground/50 hover:text-foreground h-8"
            >
              Switch <ChevronDown aria-hidden="true" className="h-3 w-3" />
            </Button>
          </PopoverTrigger>
          <PopoverContent
            align="end"
            sideOffset={4}
            className="w-80 p-2"
          >
            <AgentPicker
              value={currentSession?.agent_config_id ?? null}
              onChange={handleAgentSwitch}
            />
          </PopoverContent>
        </Popover>
      </div>
    </div>
  )

  /* ── Render: No session → welcome state ── */

  const welcomeState = !currentSession && (
    <div className="flex-1 flex flex-col">
      {/* Mobile menu trigger */}
      <div className="flex items-center px-4 lg:px-6 pt-3 lg:hidden">
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10 -ml-2.5"
            aria-label="Open conversations"
          >
            <Menu aria-hidden="true" className="h-4 w-4" />
          </Button>
        </SheetTrigger>
      </div>
      <div className="flex-1 flex items-center justify-center">
        {suggestionChips}
      </div>
    </div>
  )

  /* ── Render: Active chat area ── */

  const chatArea = currentSession && (
    <>
      {sessionHeader}
      <div className="flex-1 flex flex-col min-h-0 relative">
        <MessageList
          messages={chatMessages}
          isStreaming={isStreaming}
          className="flex-1"
        />

        {/* Chat input footer */}
        <div className="border-t border-border/40 px-4 lg:px-6 py-3 shrink-0 bg-gradient-to-t from-background via-background/95 to-transparent">
          <div className="flex items-end gap-2 max-w-4xl mx-auto">
            <div className="flex-1">
              <ChatInput
                onSend={handleSend}
                disabled={isStreaming}
                isStreaming={isStreaming}
                placeholder="Ask anything..."
                acceptFileTypes=".pdf,.txt,.md,.py,.js,.ts,.json,.csv"
              />
            </div>
            {isStreaming && (
              <Button
                variant="destructive"
                size="icon"
                onClick={stopStreaming}
                className="h-10 w-10 shrink-0 rounded-xl mb-1"
                aria-label="Stop streaming"
              >
                <Square aria-hidden="true" className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </>
  )

  /* ── MAIN RENDER ── */

  return (
    <>
      {/* ── Clear all confirmation dialog ── */}
      <Dialog open={clearConfirmOpen} onOpenChange={setClearConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear all conversations?</DialogTitle>
            <DialogDescription>
              This will permanently delete all your conversations. This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setClearConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleClearAll}
            >
              Clear all
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── New session dialog ── */}
      <Dialog open={newSessionOpen} onOpenChange={setNewSessionOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New Conversation</DialogTitle>
            <DialogDescription>
              Choose an agent and configure your session.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            {/* Agent picker */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground/60">
                Agent
              </label>
              <AgentPicker
                value={selectedAgentId}
                onChange={setSelectedAgentId}
              />
            </div>

            {/* Title */}
            <div className="space-y-1.5">
              <label htmlFor="new-session-title" className="text-xs font-medium text-muted-foreground/60">
                Session title{' '}
                <span className="text-muted-foreground/30">(optional)</span>
              </label>
              <Input
                id="new-session-title"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="E.g., Literature review on transformers"
                className="h-9 text-sm"
              />
            </div>

            {/* System prompt */}
            <div className="space-y-1.5">
              <label htmlFor="new-session-system" className="text-xs font-medium text-muted-foreground/60">
                System prompt{' '}
                <span className="text-muted-foreground/30">(optional)</span>
              </label>
              <Textarea
                id="new-session-system"
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="You are a helpful research assistant..."
                className="min-h-[60px] text-sm resize-none"
              />
            </div>

            {/* Assets */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground/60">
                Attach assets{' '}
                <span className="text-muted-foreground/30">(optional)</span>
              </label>
              <AssetPicker
                value={selectedAssets}
                onChange={setSelectedAssets}
                max={5}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setNewSessionOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateSession}
              disabled={!selectedAgentId}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              Start Conversation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Main layout ── */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        {/* Mobile sidebar */}
        <SheetContent side="left" className="w-72 p-0 flex flex-col">
          <SheetHeader className="px-4 pt-4 pb-3 border-b border-border/40 shrink-0">
            <SheetTitle className="text-sm font-display font-semibold text-left">
              Conversations
            </SheetTitle>
          </SheetHeader>
          <div className="flex-1 flex flex-col min-h-0">
            {sidebarContent}
          </div>
        </SheetContent>

        {/* Page layout */}
        <div className="flex h-full overflow-hidden">
          {/* Desktop sidebar */}
          <aside aria-label="Conversations" className="hidden lg:flex lg:flex-col w-72 border-r border-border/40 bg-card/20">
            <div className="flex flex-col h-full">
              {sidebarContent}
            </div>
          </aside>

          {/* Main chat area */}
          <div className="flex-1 flex flex-col min-w-0 bg-gradient-to-b from-background via-background to-background/30 dark:to-background/20">
            {/* PageHeader — always visible */}
            <div className="px-4 lg:px-6 pt-4 lg:pt-5 pb-1 shrink-0">
              <PageHeader
                title="Intelligence Chat"
                description="AI-powered academic assistant"
                className="mb-0"
              />
            </div>

            {/* Content */}
            {welcomeState}
            {chatArea}
          </div>
        </div>
      </Sheet>
    </>
  )
}
