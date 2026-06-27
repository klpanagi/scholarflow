import { useState, useEffect, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Select } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  Bot,
  Search,
  FileText,
  Wand2,
  Sparkles,
  MessageCircle,
  UserCog,
  Plus,
  Save,
  Trash2,
  Play,
  Loader2,
  Settings2,
  Puzzle,
  Activity,
  CheckCircle2,
  BarChart3,
  Tag,
} from "lucide-react"

import PageHeader from "@/components/shared/PageHeader"
import StatusBadge from "@/components/shared/StatusBadge"
import EmptyState from "@/components/shared/EmptyState"
import ModalShell from "@/components/shared/ModalShell"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"

// ========================================================================
// Types
// ========================================================================

interface AgentType {
  name: string
  description: string
}

interface AgentConfig {
  id: string
  name: string
  role: string
  provider: string
  model: string
  temperature: number
  max_tokens: number
  strategy: string
  tools: string[]
  system_prompt: string | null
  is_default: boolean
  skills: Skill[]
  created_at: string
  updated_at: string
}

interface AgentResult {
  output: string
  metadata: Record<string, any>
}

interface Skill {
  id: string
  name: string
  description: string
  builtin_tools: string[]
}

// ========================================================================
// Constants
// ========================================================================

const ROLES = [
  { value: "researcher", label: "Researcher" },
  { value: "writer", label: "Writer" },
  { value: "reviewer", label: "Reviewer (Simple)" },
  { value: "deep_reviewer", label: "Reviewer (Deep \u2014 7-stage)" },
  { value: "debater", label: "Debater" },
  { value: "recommender", label: "Recommender" },
  { value: "manager", label: "Manager" },
  { value: "revision", label: "Revision" },
  { value: "chat", label: "Chat" },
]

const STRATEGIES = [
  { value: "direct", label: "Direct" },
  { value: "critique", label: "Critique" },
  { value: "reflection", label: "Reflection" },
  { value: "evaluator_optimizer", label: "Evaluator Optimizer" },
]

const TABS = [
  { value: "all", label: "All", icon: Bot },
  { value: "search", label: "Search", icon: Search },
  { value: "review", label: "Review", icon: FileText },
  { value: "writing", label: "Writing", icon: Wand2 },
  { value: "recommendation", label: "Recommendation", icon: Sparkles },
] as const

type TabValue = (typeof TABS)[number]["value"]

const TAB_ROLE_MAP: Record<TabValue, string[]> = {
  all: [],
  search: ["researcher"],
  review: ["reviewer", "deep_reviewer"],
  writing: ["writer", "revision"],
  recommendation: ["recommender"],
}

const ROLE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  researcher: Search,
  writer: Wand2,
  reviewer: FileText,
  deep_reviewer: FileText,
  debater: MessageCircle,
  recommender: Sparkles,
  manager: UserCog,
  revision: Wand2,
}

function getRoleIcon(role: string): React.ComponentType<{ className?: string }> {
  return ROLE_ICONS[role] || Bot
}

function getRoleLabel(role: string): string {
  return ROLES.find((r) => r.value === role)?.label || role
}

// ========================================================================
// Helper sub-components
// ========================================================================

function AgentCard({
  config,
  onConfigure,
}: {
  config: AgentConfig
  onConfigure: () => void
}) {
  const Icon = getRoleIcon(config.role)
  const displayTools = config.tools?.slice(0, 3) ?? []
  const extraTools = (config.tools?.length ?? 0) - 3

  return (
    <div
      onClick={onConfigure}
      className={cn(
        "group cursor-pointer rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur-xl transition-all duration-300",
        "hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-0.5",
      )}
    >
      {/* Icon + Name Row */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-display text-base font-semibold text-foreground">
              {config.name}
            </h3>
            <p className="text-xs text-muted-foreground">
              {getRoleLabel(config.role)}
            </p>
          </div>
        </div>
        <StatusBadge
          status={config.is_default ? "default" : "completed"}
          label={config.is_default ? "Default" : "Active"}
        />
      </div>

      {/* Provider + Model */}
      <div className="mb-3 space-y-1">
        <p className="text-xs text-muted-foreground line-clamp-1">
          {config.provider} / {config.model}
        </p>
      </div>

      {/* Capability chips */}
      {displayTools.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-1.5">
          {displayTools.map((tool) => (
            <span
              key={tool}
              className="inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-2 py-0.5 text-[10px] font-medium text-primary"
            >
              {tool}
            </span>
          ))}
          {extraTools > 0 && (
            <span className="inline-flex items-center rounded-full border border-border/40 bg-muted/50 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              +{extraTools} more
            </span>
          )}
        </div>
      )}

      {displayTools.length === 0 && <div className="mb-4" />}

      {/* Skills indicator */}
      {config.skills && config.skills.length > 0 && (
        <div className="mb-3 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Puzzle className="h-3 w-3" />
          <span>
            {config.skills.length} skill{config.skills.length > 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Configure button */}
      <div className="flex justify-end">
        <Button
          variant="outline"
          size="sm"
          className="border-primary/20 text-primary hover:bg-primary/10 hover:text-primary"
          onClick={(e) => {
            e.stopPropagation()
            onConfigure()
          }}
        >
          <Settings2 className="mr-1.5 h-3.5 w-3.5" />
          Configure
        </Button>
      </div>
    </div>
  )
}

// ========================================================================
// Main Component
// ========================================================================

export default function AgentsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const [selectedConfig, setSelectedConfig] = useState<AgentConfig | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [runInput, setRunInput] = useState("")
  const [runResult, setRunResult] = useState<AgentResult | null>(null)
  const [activeTab, setActiveTab] = useState<TabValue>("all")
  const [modalOpen, setModalOpen] = useState(false)

  const [form, setForm] = useState({
    name: "",
    role: "researcher",
    provider: "opencode",
    model: "",
    temperature: 0.7,
    max_tokens: 4096,
    strategy: "direct",
    system_prompt: "",
    is_default: false,
  })

  // ----- Data fetching -----

  const { data: agentTypes = [] } = useQuery<AgentType[]>({
    queryKey: ["agent-types"],
    queryFn: async () => {
      const { data } = await api.get("/agents/types")
      return data.agents || []
    },
  })

  const {
    data: configs = [],
    isLoading: configsLoading,
  } = useQuery<AgentConfig[]>({
    queryKey: ["agent-configs"],
    queryFn: async () => {
      const { data } = await api.get("/agents/configs")
      return data || []
    },
  })

  const { data: availableModels = {} } = useQuery<Record<string, string[]>>({
    queryKey: ["available-models"],
    queryFn: async () => {
      const { data } = await api.get("/chat/models")
      return data || {}
    },
  })

  const { data: availableSkills = [] } = useQuery<Skill[]>({
    queryKey: ["skills"],
    queryFn: async () => {
      const { data } = await api.get("/skills/")
      return data || []
    },
  })

  const providerModels = availableModels[form.provider] || []

  // ----- Mutations -----

  const createMutation = useMutation({
    mutationFn: async (payload: typeof form) => {
      const { data } = await api.post("/agents/configs", payload)
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["agent-configs"] })
      setSelectedConfig(data)
      setIsCreating(false)
      toast({ title: "Agent config created" })
    },
    onError: (error: any) => {
      toast({
        title: "Failed to create config",
        description: error.response?.data?.detail || "Unknown error",
        variant: "destructive",
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string
      payload: Partial<typeof form>
    }) => {
      const { data } = await api.patch(`/agents/configs/${id}`, payload)
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["agent-configs"] })
      setSelectedConfig(data)
      toast({ title: "Config updated" })
    },
    onError: (error: any) => {
      toast({
        title: "Failed to update config",
        description: error.response?.data?.detail || "Unknown error",
        variant: "destructive",
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/agents/configs/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-configs"] })
      setSelectedConfig(null)
      setModalOpen(false)
      toast({ title: "Config deleted" })
    },
    onError: (error: any) => {
      toast({
        title: "Failed to delete config",
        description: error.response?.data?.detail || "Unknown error",
        variant: "destructive",
      })
    },
  })

  const runMutation = useMutation({
    mutationFn: async ({
      agentType,
      message,
      configId,
    }: {
      agentType: string
      message: string
      configId?: string
    }) => {
      const { data } = await api.post("/agents/run", {
        agent_type: agentType,
        message,
        agent_config_id: configId,
        strategy: "direct",
      })
      return data as AgentResult
    },
    onSuccess: (data) => {
      setRunResult(data)
      toast({ title: "Agent completed" })
    },
    onError: (error: any) => {
      toast({
        title: "Agent failed",
        description: error.response?.data?.detail || "Could not run agent",
        variant: "destructive",
      })
    },
  })

  const assignSkillsMutation = useMutation({
    mutationFn: async ({
      configId,
      skillIds,
    }: {
      configId: string
      skillIds: string[]
    }) => {
      const { data } = await api.post(`/skills/assign/${configId}`, {
        skill_ids: skillIds,
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-configs"] })
      toast({ title: "Skills assigned" })
    },
    onError: (error: any) => {
      toast({
        title: "Failed to assign skills",
        description: error.response?.data?.detail || "Unknown error",
        variant: "destructive",
      })
    },
  })

  // ----- Derived state -----

  const filteredConfigs = useMemo(() => {
    if (activeTab === "all") return configs
    const allowedRoles = TAB_ROLE_MAP[activeTab]
    return configs.filter((c) => allowedRoles.includes(c.role))
  }, [configs, activeTab])

  // Stats derived from configs
  const stats = useMemo(() => {
    const total = configs.length
    const active = configs.filter((c) => c.is_default).length
    return {
      totalAgents: total,
      activeAgents: active || total,
      totalRuns: 0,
      successRate: 0,
    }
  }, [configs])

  // ----- Effects -----

  useEffect(() => {
    if (selectedConfig && !isCreating) {
      setForm({
        name: selectedConfig.name,
        role: selectedConfig.role,
        provider: selectedConfig.provider,
        model: selectedConfig.model,
        temperature: selectedConfig.temperature,
        max_tokens: selectedConfig.max_tokens,
        strategy: selectedConfig.strategy,
        system_prompt: selectedConfig.system_prompt || "",
        is_default: selectedConfig.is_default,
      })
    }
  }, [selectedConfig, isCreating])

  // Reset run result when modal opens/closes
  useEffect(() => {
    if (!modalOpen) {
      setRunResult(null)
      setRunInput("")
    }
  }, [modalOpen])

  // ----- Handlers -----

  const handleNew = () => {
    setIsCreating(true)
    setSelectedConfig(null)
    setForm({
      name: "",
      role: "researcher",
      provider: "opencode",
      model: "",
      temperature: 0.7,
      max_tokens: 4096,
      strategy: "direct",
      system_prompt: "",
      is_default: false,
    })
    setModalOpen(true)
  }

  const handleConfigure = (config: AgentConfig) => {
    setSelectedConfig(config)
    setIsCreating(false)
    setRunResult(null)
    setRunInput("")
    setModalOpen(true)
  }

  const handleSave = () => {
    if (!form.name.trim()) {
      toast({ title: "Name is required", variant: "destructive" })
      return
    }
    if (!form.model.trim()) {
      toast({ title: "Model is required", variant: "destructive" })
      return
    }

    if (isCreating) {
      createMutation.mutate(form)
    } else if (selectedConfig) {
      updateMutation.mutate({ id: selectedConfig.id, payload: form })
    }
  }

  const handleDelete = () => {
    if (selectedConfig) {
      deleteMutation.mutate(selectedConfig.id)
    }
  }

  const handleRun = () => {
    if (!runInput.trim()) return
    const agentType = selectedConfig?.role || "researcher"
    runMutation.mutate({
      agentType,
      message: runInput,
      configId: selectedConfig?.id,
    })
  }

  const updateForm = (field: string, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  // ========================================================================
  // Loading state
  // ========================================================================

  if (configsLoading) {
    return (
      <div className="animate-in fade-in duration-500 space-y-6">
        {/* Skeleton: PageHeader */}
        <div className="mb-8">
          <Skeleton className="mb-2 h-9 w-64" />
          <Skeleton className="h-4 w-48" />
        </div>

        {/* Skeleton: Stats row */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur-xl"
            >
              <Skeleton className="mb-3 h-4 w-20" />
              <Skeleton className="mb-1 h-8 w-16" />
              <Skeleton className="h-3 w-24" />
            </div>
          ))}
        </div>

        {/* Skeleton: Tabs + Grid */}
        <div>
          <Skeleton className="mb-6 h-10 w-96 rounded-lg" />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur-xl"
              >
                <div className="mb-3 flex items-center gap-3">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <div>
                    <Skeleton className="mb-1 h-4 w-28" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
                <Skeleton className="mb-3 h-3 w-36" />
                <div className="mb-4 flex gap-1.5">
                  <Skeleton className="h-5 w-16 rounded-full" />
                  <Skeleton className="h-5 w-20 rounded-full" />
                </div>
                <div className="flex justify-end">
                  <Skeleton className="h-9 w-24 rounded-md" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ========================================================================
  // Render
  // ========================================================================

  return (
    <div className="animate-in fade-in duration-500 space-y-8">
      {/* ================================================================= */}
      {/* Hero Section                                                     */}
      {/* ================================================================= */}
      <PageHeader
        title="Agent Intelligence"
        description="Configure, manage, and test your AI research agents \u2014 from literature search and peer review to academic writing."
        actions={
          <Button
            onClick={handleNew}
            className="gap-2 border-primary/30 bg-primary/10 text-primary shadow-sm backdrop-blur-sm hover:bg-primary/20 hover:text-primary"
          >
            <Plus className="h-4 w-4" />
            New Agent
          </Button>
        }
      />

      {/* ================================================================= */}
      {/* Stats Row                                                        */}
      {/* ================================================================= */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur-xl transition-all duration-300 hover:border-primary/20 hover:shadow-md hover:shadow-primary/5">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Total Agents
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Bot className="h-4 w-4" />
            </div>
          </div>
          <div className="font-display text-2xl font-semibold text-foreground">
            {stats.totalAgents}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">configured agents</p>
        </div>

        <div className="rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur-xl transition-all duration-300 hover:border-emerald-500/20 hover:shadow-md hover:shadow-emerald-500/5">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Active
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-500">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="font-display text-2xl font-semibold text-foreground">
            {stats.activeAgents}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">ready to use</p>
        </div>

        <div className="rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur-xl transition-all duration-300 hover:border-primary/20 hover:shadow-md hover:shadow-primary/5">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Total Runs
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Activity className="h-4 w-4" />
            </div>
          </div>
          <div className="font-display text-2xl font-semibold text-foreground">
            {stats.totalRuns}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">executions today</p>
        </div>

        <div className="rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur-xl transition-all duration-300 hover:border-primary/20 hover:shadow-md hover:shadow-primary/5">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Agent Types
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
              <BarChart3 className="h-4 w-4" />
            </div>
          </div>
          <div className="font-display text-2xl font-semibold text-foreground">
            {agentTypes.length}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">available types</p>
        </div>
      </div>

      {/* ================================================================= */}
      {/* Tabs + Agent Grid                                                */}
      {/* ================================================================= */}
      <Tabs
        defaultValue="all"
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as TabValue)}
      >
        <TabsList variant="pills" className="mb-6">
          {TABS.map((tab) => {
            const TabIcon = tab.icon
            return (
              <TabsTrigger key={tab.value} value={tab.value} variant="pills">
                <TabIcon className="mr-1.5 h-4 w-4" />
                {tab.label}
              </TabsTrigger>
            )
          })}
        </TabsList>

        {TABS.map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            {filteredConfigs.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredConfigs.map((config) => (
                  <AgentCard
                    key={config.id}
                    config={config}
                    onConfigure={() => handleConfigure(config)}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Bot}
                title={
                  tab.value === "all"
                    ? "No agents configured"
                    : `No ${tab.label} agents`
                }
                description={
                  tab.value === "all"
                    ? "Create your first agent config to start leveraging AI research assistance."
                    : `No agents found for the ${tab.label} category. Create one or switch tabs.`
                }
                action={
                  tab.value === "all"
                    ? { label: "Create Agent", onClick: handleNew }
                    : undefined
                }
              />
            )}
          </TabsContent>
        ))}
      </Tabs>

      {/* ================================================================= */}
      {/* Detail / Edit Modal                                              */}
      {/* ================================================================= */}
      <ModalShell
        open={modalOpen}
        onOpenChange={(open) => {
          setModalOpen(open)
          if (!open) {
            setSelectedConfig(null)
            setIsCreating(false)
          }
        }}
        title={
          <div className="flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-primary" />
            {isCreating ? "Create Agent Config" : `Edit: ${selectedConfig?.name}`}
          </div>
        }
        description={
          isCreating
            ? "Configure a new agent with model, strategy, and system prompt settings."
            : "Modify agent settings, assign skills, or run a test query."
        }
        size="xl"
        footer={
          <div className="flex w-full items-center justify-between">
            <div>
              {!isCreating && selectedConfig && (
                <Button variant="destructive" size="sm" onClick={handleDelete}>
                  <Trash2 className="mr-1 h-4 w-4" />
                  Delete
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setModalOpen(false)
                  setSelectedConfig(null)
                  setIsCreating(false)
                }}
              >
                Cancel
              </Button>
              <Button onClick={handleSave}>
                <Save className="mr-1 h-4 w-4" />
                {isCreating ? "Create" : "Save"}
              </Button>
            </div>
          </div>
        }
      >
        {/* ---- Configuration Form ---- */}
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Name
              </label>
              <Input
                value={form.name}
                onChange={(e) => updateForm("name", e.target.value)}
                placeholder="My Scholar Agent"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Role
              </label>
              <Select
                options={ROLES}
                value={form.role}
                onChange={(e) => updateForm("role", e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Provider
              </label>
              <Select
                options={[
                  { value: "opencode", label: "OpenCode Go" },
                  { value: "opencode-zen", label: "OpenCode Zen" },
                  { value: "openrouter", label: "OpenRouter" },
                  { value: "openai", label: "OpenAI" },
                ]}
                value={form.provider}
                onChange={(e) => {
                  updateForm("provider", e.target.value)
                  updateForm("model", "")
                }}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Model
              </label>
              <Select
                options={providerModels.map((m) => ({ value: m, label: m }))}
                value={form.model}
                onChange={(e) => updateForm("model", e.target.value)}
                placeholder={
                  providerModels.length
                    ? "Select model"
                    : "No models available"
                }
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Strategy
              </label>
              <Select
                options={STRATEGIES}
                value={form.strategy}
                onChange={(e) => updateForm("strategy", e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Temperature: {form.temperature}
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={form.temperature}
                onChange={(e) =>
                  updateForm("temperature", parseFloat(e.target.value))
                }
                className="w-full accent-[hsl(var(--primary))]"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Max Tokens
              </label>
              <Input
                type="number"
                value={form.max_tokens}
                onChange={(e) =>
                  updateForm("max_tokens", parseInt(e.target.value) || 4096)
                }
                min={1}
                max={128000}
              />
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">
              System Prompt
            </label>
            <Textarea
              value={form.system_prompt}
              onChange={(e) => updateForm("system_prompt", e.target.value)}
              placeholder="You are a helpful academic research assistant..."
              rows={4}
            />
          </div>

          {/* Is Default checkbox */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_default"
              checked={form.is_default}
              onChange={(e) => updateForm("is_default", e.target.checked)}
              className="accent-[hsl(var(--primary))]"
            />
            <label htmlFor="is_default" className="text-sm text-foreground">
              Set as default config for this role
            </label>
          </div>

          {/* ---- Skills Section (edit mode only) ---- */}
          {selectedConfig && !isCreating && (
            <div className="border-t border-border/50 pt-5">
              <label className="mb-1.5 flex items-center gap-2 text-sm font-medium text-foreground">
                <Puzzle className="h-4 w-4 text-primary" /> Assigned Skills
              </label>
              <p className="mb-3 text-xs text-muted-foreground">
                Select skills to give this agent specialized capabilities
              </p>
              <div className="grid grid-cols-2 gap-1.5">
                {availableSkills.map((skill) => {
                  const isAssigned =
                    selectedConfig?.skills?.some((s) => s.id === skill.id) ??
                    false
                  return (
                    <label
                      key={skill.id}
                      className={cn(
                        "flex cursor-pointer items-center gap-2 rounded-md border px-2.5 py-1.5 transition-colors",
                        isAssigned
                          ? "border-primary/40 bg-primary/5"
                          : "border-border/50 hover:border-muted-foreground/40",
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={isAssigned}
                        onChange={() => {
                          if (!selectedConfig) return
                          const current = selectedConfig.skills || []
                          const newSkills = isAssigned
                            ? current.filter((s) => s.id !== skill.id)
                            : [...current, skill]
                          assignSkillsMutation.mutate({
                            configId: selectedConfig.id,
                            skillIds: newSkills.map((s) => s.id),
                          })
                        }}
                        disabled={isCreating}
                        className="accent-[hsl(var(--primary))]"
                      />
                      <span className="text-sm font-medium text-foreground">
                        {skill.name}
                      </span>
                    </label>
                  )
                })}
                {availableSkills.length === 0 && (
                  <p className="col-span-2 text-sm text-muted-foreground">
                    No skills available. Create skills first.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ---- Tools section (edit mode only) ---- */}
          {selectedConfig && !isCreating && (
            <div className="border-t border-border/50 pt-5">
              <h4 className="mb-1.5 flex items-center gap-2 text-sm font-medium text-foreground">
                <Tag className="h-4 w-4 text-primary" /> Tools &amp; Capabilities
              </h4>
              <p className="mb-3 text-xs text-muted-foreground">
                Tools available to this agent from direct config and assigned
                skills
              </p>
              {(() => {
                const toolSources = new Map<string, Set<string>>()
                for (const t of selectedConfig.tools ?? []) {
                  if (!toolSources.has(t)) toolSources.set(t, new Set())
                  toolSources.get(t)!.add("Direct")
                }
                for (const skill of selectedConfig.skills ?? []) {
                  for (const t of skill.builtin_tools ?? []) {
                    if (!toolSources.has(t)) toolSources.set(t, new Set())
                    toolSources.get(t)!.add(skill.name)
                  }
                }
                const entries = Array.from(toolSources.entries()).sort((a, b) =>
                  a[0].localeCompare(b[0]),
                )
                if (entries.length === 0) {
                  return (
                    <p className="text-sm text-muted-foreground">
                      No tools assigned. Add skills or configure tools directly.
                    </p>
                  )
                }
                return (
                  <div className="flex flex-wrap gap-2">
                    {entries.map(([tool, sources]) => (
                      <div key={tool} className="group relative">
                        <Badge
                          variant="secondary"
                          className="cursor-default text-xs"
                        >
                          {tool}
                        </Badge>
                        <div className="pointer-events-none absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 group-hover:block">
                          <div className="whitespace-nowrap rounded-md border bg-popover px-2 py-1 text-xs text-popover-foreground shadow-md">
                            From: {Array.from(sources).join(", ")}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              })()}
            </div>
          )}

          {/* ---- Test Run Section (edit mode only) ---- */}
          {selectedConfig && !isCreating && (
            <div className="border-t border-border/50 pt-5">
              <h4 className="mb-1.5 flex items-center gap-2 text-sm font-medium text-foreground">
                <Play className="h-4 w-4 text-primary" /> Test Agent
              </h4>
              <p className="mb-3 text-xs text-muted-foreground">
                Run this agent config with a test query
              </p>
              <Textarea
                placeholder="Enter a query to test this agent..."
                value={runInput}
                onChange={(e) => setRunInput(e.target.value)}
                rows={3}
              />
              <div className="mt-3 flex items-center gap-3">
                <Button
                  onClick={handleRun}
                  disabled={runMutation.isPending || !runInput.trim()}
                  className="bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  {runMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      Test Run
                    </>
                  )}
                </Button>
                {runMutation.isPending && (
                  <span className="text-xs text-muted-foreground">
                    Agent is processing your query\u2026
                  </span>
                )}
              </div>

              {runResult && (
                <div className="mt-4 rounded-lg border border-border/50 bg-muted/30 p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    <span className="text-sm font-medium text-foreground">
                      Result
                    </span>
                  </div>
                  <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap text-sm text-muted-foreground">
                    {runResult.output}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </ModalShell>
    </div>
  )
}
