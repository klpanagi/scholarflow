import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Select } from "@/components/ui/select"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import {
  Bot,
  Plus,
  Save,
  Trash2,
  Play,
  Loader2,
  Settings2,
  ChevronRight,
  Puzzle,
  Wrench,
} from "lucide-react"

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

const ROLES = [
  { value: "researcher", label: "Researcher" },
  { value: "writer", label: "Writer" },
  { value: "reviewer", label: "Reviewer" },
  { value: "recommender", label: "Recommender" },
]

const STRATEGIES = [
  { value: "direct", label: "Direct" },
  { value: "critique", label: "Critique" },
  { value: "reflection", label: "Reflection" },
  { value: "evaluator_optimizer", label: "Evaluator Optimizer" },
]

export default function AgentsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const [selectedConfig, setSelectedConfig] = useState<AgentConfig | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [runInput, setRunInput] = useState("")
  const [runResult, setRunResult] = useState<AgentResult | null>(null)

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

  const { data: agentTypes = [] } = useQuery<AgentType[]>({
    queryKey: ["agent-types"],
    queryFn: async () => {
      const { data } = await api.get("/agents/types")
      return data.agents || []
    },
  })

  const { data: configs = [] } = useQuery<AgentConfig[]>({
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
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<typeof form> }) => {
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
    mutationFn: async ({ configId, skillIds }: { configId: string; skillIds: string[] }) => {
      const { data } = await api.post(`/skills/assign/${configId}`, { skill_ids: skillIds })
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

  return (
    <div className="flex gap-6 h-full">
      <div className="w-80 shrink-0 space-y-4 overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Agent Configs</h2>
          <Button size="sm" onClick={handleNew}>
            <Plus className="h-4 w-4 mr-1" /> New
          </Button>
        </div>

        {configs.map((config) => (
          <Card
            key={config.id}
            className={`cursor-pointer transition-colors ${
              selectedConfig?.id === config.id ? "border-primary" : ""
            }`}
            onClick={() => {
              setSelectedConfig(config)
              setIsCreating(false)
            }}
          >
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4 text-primary" />
                  <span className="font-medium text-sm">{config.name}</span>
                </div>
                {config.is_default && (
                  <Badge variant="secondary" className="text-xs">Default</Badge>
                )}
              </div>
              <div className="mt-1 flex gap-1">
                <Badge variant="outline" className="text-xs">{config.role}</Badge>
                <Badge variant="outline" className="text-xs">{config.provider}</Badge>
                {config.skills && config.skills.length > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    <Puzzle className="h-3 w-3 mr-1" /> {config.skills.length}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1 truncate">
                {config.model}
              </p>
            </CardContent>
          </Card>
        ))}

        {configs.length === 0 && (
          <Card>
            <CardContent className="py-6 text-center text-sm text-muted-foreground">
              No configs yet. Create one to get started.
            </CardContent>
          </Card>
        )}

        <div className="border-t pt-4">
          <h3 className="text-sm font-medium mb-2 text-muted-foreground">
            Available Agent Types
          </h3>
          {agentTypes.map((agent) => (
            <div key={agent.name} className="flex items-center gap-2 py-1 text-sm">
              <ChevronRight className="h-3 w-3" />
              <span className="font-medium">{agent.name}</span>
              <span className="text-muted-foreground truncate">— {agent.description}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto">
        {(selectedConfig || isCreating) ? (
          <>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Settings2 className="h-5 w-5" />
                      {isCreating ? "New Agent Config" : `Edit: ${selectedConfig?.name}`}
                    </CardTitle>
                    <CardDescription>
                      Configure the agent's model, behavior, and system prompt
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {!isCreating && (
                      <Button variant="destructive" size="sm" onClick={handleDelete}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                    <Button size="sm" onClick={handleSave}>
                      <Save className="h-4 w-4 mr-1" /> Save
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium">Name</label>
                    <Input
                      value={form.name}
                      onChange={(e) => updateForm("name", e.target.value)}
                      placeholder="My Scholar Agent"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Role</label>
                    <Select
                      options={ROLES}
                      value={form.role}
                      onChange={(e) => updateForm("role", e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium">Provider</label>
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
                    <label className="text-sm font-medium">Model</label>
                    <Select
                      options={providerModels.map((m) => ({ value: m, label: m }))}
                      value={form.model}
                      onChange={(e) => updateForm("model", e.target.value)}
                      placeholder={providerModels.length ? "Select model" : "No models available"}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium">Strategy</label>
                    <Select
                      options={STRATEGIES}
                      value={form.strategy}
                      onChange={(e) => updateForm("strategy", e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">
                      Temperature: {form.temperature}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={form.temperature}
                      onChange={(e) => updateForm("temperature", parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Max Tokens</label>
                    <Input
                      type="number"
                      value={form.max_tokens}
                      onChange={(e) => updateForm("max_tokens", parseInt(e.target.value) || 4096)}
                      min={1}
                      max={128000}
                    />
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium">System Prompt</label>
                  <Textarea
                    value={form.system_prompt}
                    onChange={(e) => updateForm("system_prompt", e.target.value)}
                    placeholder="You are a helpful academic research assistant..."
                    rows={6}
                  />
                </div>

                <div>
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Puzzle className="h-4 w-4" /> Assigned Skills
                  </label>
                  <p className="text-xs text-muted-foreground mb-2">
                    Select skills to give this agent specialized capabilities
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {availableSkills.map((skill) => {
                      const isAssigned = selectedConfig?.skills?.some((s) => s.id === skill.id)
                      return (
                        <label
                          key={skill.id}
                          className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                            isAssigned
                              ? "border-primary bg-primary/5"
                              : "border-muted-foreground/20 hover:border-muted-foreground/40"
                          }`}
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
                            disabled={!selectedConfig || isCreating}
                            className="mt-0.5"
                          />
                          <div>
                            <span className="text-sm font-medium">{skill.name}</span>
                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                              {skill.description}
                            </p>
                          </div>
                        </label>
                      )
                    })}
                    {availableSkills.length === 0 && (
                      <p className="text-sm text-muted-foreground col-span-2">
                        No skills available. Create skills first.
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_default"
                    checked={form.is_default}
                    onChange={(e) => updateForm("is_default", e.target.checked)}
                  />
                  <label htmlFor="is_default" className="text-sm">
                    Set as default config for this role
                  </label>
                </div>
              </CardContent>
            </Card>

            {selectedConfig && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Wrench className="h-5 w-5" /> Tools & Capabilities
                  </CardTitle>
                  <CardDescription>
                    Tools available to this agent from direct config and assigned skills
                  </CardDescription>
                </CardHeader>
                <CardContent>
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
                    const entries = Array.from(toolSources.entries()).sort((a, b) => a[0].localeCompare(b[0]))
                    if (entries.length === 0) {
                      return <p className="text-sm text-muted-foreground">No tools assigned. Add skills or configure tools directly.</p>
                    }
                    return (
                      <div className="flex flex-wrap gap-2">
                        {entries.map(([tool, sources]) => (
                          <div key={tool} className="group relative">
                            <Badge variant="secondary" className="text-xs cursor-default">
                              {tool}
                            </Badge>
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                              <div className="bg-popover text-popover-foreground text-xs rounded-md px-2 py-1 shadow-md whitespace-nowrap border">
                                From: {Array.from(sources).join(", ")}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )
                  })()}
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Test Agent</CardTitle>
                <CardDescription>
                  Run this agent config with a test query
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  placeholder="Enter a query to test this agent..."
                  value={runInput}
                  onChange={(e) => setRunInput(e.target.value)}
                  rows={3}
                />
                <Button
                  onClick={handleRun}
                  disabled={runMutation.isPending || !runInput.trim()}
                >
                  {runMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      Run Agent
                    </>
                  )}
                </Button>

                {runResult && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium mb-2">Result</h4>
                    <pre className="whitespace-pre-wrap bg-muted p-4 rounded-md text-sm max-h-96 overflow-y-auto">
                      {runResult.output}
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <Bot className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">Select or Create an Agent Config</h3>
              <p className="text-muted-foreground mb-4">
                Choose a config from the left panel or create a new one to get started.
              </p>
              <Button onClick={handleNew}>
                <Plus className="h-4 w-4 mr-1" /> Create New Config
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
