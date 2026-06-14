import { useEffect, useRef, useState } from 'react'
import { useChat } from '@/hooks/useChat'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import {
  Plus,
  Trash2,
  Send,
  Square,
  GitFork,
  Upload,
  MessageSquare,
  Bot,
  User,
  ChevronDown,
  Search,
  Loader2,
} from 'lucide-react'

export default function ChatPage() {
  const {
    sessions,
    currentSession,
    messages,
    isStreaming,
    streamingContent,
    availableModels,
    fetchSessions,
    createSession,
    deleteSession,
    selectSession,
    fetchModels,
    sendMessage,
    stopStreaming,
    forkSession,
    uploadFile,
  } = useChat()

  const { toast } = useToast()
  const [input, setInput] = useState('')
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [showModelPicker, setShowModelPicker] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showNewSession, setShowNewSession] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    fetchSessions()
    fetchModels()
  }, [fetchSessions, fetchModels])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const providers = [...new Set(availableModels.map((m) => m.provider))]
  const filteredModels = availableModels.filter(
    (m) => m.provider === selectedProvider && m.id.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleCreateSession = async () => {
    if (!selectedProvider || !selectedModel) {
      toast({ title: 'Select a model', description: 'Choose a provider and model first.' })
      return
    }
    try {
      await createSession(selectedModel, selectedProvider, newTitle || undefined, systemPrompt || undefined)
      setShowNewSession(false)
      setNewTitle('')
      setSystemPrompt('')
    } catch {
      toast({ title: 'Error', description: 'Failed to create session.' })
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return
    const msg = input.trim()
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    await sendMessage(msg)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFork = async (messageId: string) => {
    try {
      await forkSession(messageId)
      toast({ title: 'Session forked', description: 'A new session was created from this message.' })
    } catch {
      toast({ title: 'Error', description: 'Failed to fork session.' })
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !currentSession) return
    try {
      const result = await uploadFile(file)
      if (result) {
        setInput((prev) => prev + `\n\n[Attached: ${result.file_name}]`)
        toast({ title: 'File uploaded', description: `${result.file_name} attached.` })
      }
    } catch {
      toast({ title: 'Error', description: 'Failed to upload file.' })
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`
  }

  return (
    <div className="flex h-full">
      <div className="w-72 border-r bg-muted/30 flex flex-col">
        <div className="p-3 border-b">
          <Button onClick={() => setShowNewSession(true)} className="w-full" size="sm">
            <Plus className="h-4 w-4 mr-2" /> New Chat
          </Button>
        </div>

        {showNewSession && (
          <div className="p-3 border-b space-y-2">
            <select
              value={selectedProvider}
              onChange={(e) => {
                setSelectedProvider(e.target.value)
                setSelectedModel('')
              }}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="">Provider...</option>
              {providers.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="">Model...</option>
              {availableModels.filter((m) => m.provider === selectedProvider).map((m) => (
                <option key={m.id} value={m.id}>{m.id}</option>
              ))}
            </select>
            <Input
              placeholder="Session title (optional)"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="text-sm"
            />
            <Textarea
              placeholder="System prompt (optional)"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="text-sm min-h-[60px]"
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={handleCreateSession} className="flex-1">Create</Button>
              <Button size="sm" variant="ghost" onClick={() => setShowNewSession(false)}>Cancel</Button>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto">
          {sessions.length === 0 && (
            <p className="text-sm text-muted-foreground p-4 text-center">No sessions yet</p>
          )}
          {sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => selectSession(session)}
              className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer hover:bg-accent transition-colors ${
                currentSession?.id === session.id ? 'bg-accent' : ''
              }`}
            >
              <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{session.title || 'Untitled'}</p>
                <p className="text-xs text-muted-foreground truncate">{session.model}</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => {
                  e.stopPropagation()
                  deleteSession(session.id)
                }}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        {currentSession ? (
          <>
            <div className="h-14 border-b px-4 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <h2 className="font-semibold text-sm">{currentSession.title || 'Untitled'}</h2>
                <Badge variant="outline" className="text-xs">{currentSession.provider}</Badge>
                <Badge variant="secondary" className="text-xs">{currentSession.model}</Badge>
              </div>
              <div className="relative">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowModelPicker(!showModelPicker)}
                  className="text-xs"
                >
                  Switch Model <ChevronDown className="h-3 w-3 ml-1" />
                </Button>
                {showModelPicker && (
                  <div className="absolute right-0 top-full mt-1 w-80 bg-popover border rounded-lg shadow-lg z-50 p-2">
                    <div className="relative mb-2">
                      <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search models..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-8 text-sm"
                      />
                    </div>
                    <div className="max-h-60 overflow-y-auto space-y-1">
                      {filteredModels.map((m) => (
                        <button
                          key={m.id}
                          onClick={() => {
                            setSelectedProvider(m.provider)
                            setSelectedModel(m.id)
                            setShowModelPicker(false)
                            setSearchQuery('')
                          }}
                          className="w-full text-left px-3 py-2 rounded-md text-sm hover:bg-accent transition-colors"
                        >
                          <span className="font-medium">{m.id}</span>
                          <span className="text-muted-foreground ml-2 text-xs">{m.provider}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 && !isStreaming && (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                  <Bot className="h-12 w-12 mb-4 opacity-50" />
                  <p className="text-lg font-medium">Start a conversation</p>
                  <p className="text-sm">Send a message to begin</p>
                </div>
              )}
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role !== 'user' && (
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  <div
                    className={`max-w-[70%] rounded-2xl px-4 py-2.5 ${
                      msg.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    }`}
                  >
                    {msg.role === 'user' ? (
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown
                          components={{
                            code({ className, children, ...props }) {
                              const match = /language-(\w+)/.exec(className || '')
                              return match ? (
                                <SyntaxHighlighter
                                  style={oneDark}
                                  language={match[1]}
                                  PreTag="div"
                                  className="rounded-lg text-xs"
                                >
                                  {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                              ) : (
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              )
                            },
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    )}
                    {msg.file_name && (
                      <div className="mt-2 flex items-center gap-1 text-xs opacity-70">
                        <Upload className="h-3 w-3" /> {msg.file_name}
                      </div>
                    )}
                    {msg.role === 'assistant' && (
                      <div className="mt-2 flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => handleFork(msg.id)}
                          title="Fork from here"
                        >
                          <GitFork className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                  </div>
                  {msg.role === 'user' && (
                    <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </div>
              ))}

              {isStreaming && (
                <div className="flex gap-3 justify-start">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="max-w-[70%] rounded-2xl px-4 py-2.5 bg-muted">
                    {streamingContent ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown>{streamingContent}</ReactMarkdown>
                      </div>
                    ) : (
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    )}
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="border-t p-4 shrink-0">
              <div className="flex gap-2 items-end">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden"
                  accept=".pdf,.txt,.md,.py,.js,.ts,.json,.csv"
                />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={!currentSession || isStreaming}
                  title="Upload file"
                >
                  <Upload className="h-4 w-4" />
                </Button>
                <div className="flex-1 relative">
                  <Textarea
                    ref={textareaRef}
                    value={input}
                    onChange={handleTextareaInput}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a message... (Shift+Enter for new line)"
                    className="min-h-[44px] max-h-[200px] resize-none pr-12"
                    disabled={isStreaming}
                  />
                </div>
                {isStreaming ? (
                  <Button variant="destructive" size="icon" onClick={stopStreaming}>
                    <Square className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button size="icon" onClick={handleSend} disabled={!input.trim()}>
                    <Send className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <MessageSquare className="h-16 w-16 mb-4 opacity-30" />
            <p className="text-xl font-medium">Select or create a chat session</p>
            <p className="text-sm mt-1">Choose a session from the sidebar or start a new one</p>
          </div>
        )}
      </div>
    </div>
  )
}
