import { useState, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Puzzle,
  Plus,
  Save,
  Trash2,
  Wrench,
  Globe,
  Lock,
  Search,
  Terminal,
  BookOpen,
  Brain,
  PenLine,
  Code,
  BarChart3,
  Activity,
  Play,
  Eye,
  SlidersHorizontal,
  Download,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Select } from "@/components/ui/select"
import { useToast } from "@/hooks/use-toast"
import { api, exportSkillsAndAgents } from "@/lib/api"
import { cn } from "@/lib/utils"
import { PageHeader } from "@/components/shared/PageHeader"
import { ModalShell } from "@/components/shared/ModalShell"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { EmptyState } from "@/components/shared/EmptyState"
import { LoadingState } from "@/components/shared/LoadingState"

// ========================================================================
// Types
// ========================================================================

interface BuiltinTool {
  name: string
  description: string
}

interface Skill {
  id: string
  name: string
  description: string
  prompt_template: string
  builtin_tools: string[]
  custom_tools: any[]
  input_schema: Record<string, any> | null
  output_schema: Record<string, any> | null
  tags: string[]
  is_public: boolean
  created_at: string
  updated_at: string
}

// ========================================================================
// Helpers
// ========================================================================

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffDays < 1) return "Today"
  if (diffDays === 1) return "Yesterday"
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function getSkillIcon(name: string) {
  const lower = name.toLowerCase()
  if (lower.includes("search") || lower.includes("finder") || lower.includes("discover")) return Search
  if (lower.includes("review") || lower.includes("critique") || lower.includes("assess")) return BookOpen
  if (lower.includes("write") || lower.includes("polish") || lower.includes("rewrite") || lower.includes("edit")) return PenLine
  if (lower.includes("code") || lower.includes("implement") || lower.includes("develop")) return Code
  if (lower.includes("brain") || lower.includes("think") || lower.includes("reason") || lower.includes("analyze")) return Brain
  if (lower.includes("terminal") || lower.includes("tool") || lower.includes("exec")) return Terminal
  if (lower.includes("stats") || lower.includes("metric") || lower.includes("chart")) return BarChart3
  return Puzzle
}

const ICON_COLORS = [
  "text-primary bg-primary/10",
  "text-emerald-400 bg-emerald-500/10",
  "text-amber-400 bg-amber-500/10",
  "text-sky-400 bg-sky-500/10",
  "text-rose-400 bg-rose-500/10",
  "text-violet-400 bg-violet-500/10",
]

function pickColor(index: number): string {
  return ICON_COLORS[index % ICON_COLORS.length]
}

// ========================================================================
// Main Component
// ========================================================================

export default function SkillsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  // ----- Export state -----
  const [isExporting, setIsExporting] = useState(false)

  // ----- Modal state -----
  const [detailSkill, setDetailSkill] = useState<Skill | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [isEditing, setIsEditing] = useState(false)

  // ----- Filters -----
  const [searchQuery, setSearchQuery] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("all")

  // ----- Form state -----
  const [form, setForm] = useState({
    name: "",
    description: "",
    prompt_template: "",
    builtin_tools: [] as string[],
    custom_tools: [] as any[],
    input_schema: "",
    output_schema: "",
    tags: [] as string[],
    is_public: false,
  })
  const [tagInput, setTagInput] = useState("")

  // ----- Queries -----
  const { data: skills = [], isLoading } = useQuery<Skill[]>({
    queryKey: ["skills"],
    queryFn: async () => {
      const { data } = await api.get("/skills/")
      return data || []
    },
    staleTime: 0,
    refetchOnMount: "always",
  })

  const { data: builtinTools = [] } = useQuery<BuiltinTool[]>({
    queryKey: ["builtin-tools"],
    queryFn: async () => {
      const { data } = await api.get("/skills/builtin-tools")
      return data || []
    },
    staleTime: 0,
    refetchOnMount: "always",
  })

  // ----- Mutations -----
  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await api.post("/skills/", payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      setShowCreateModal(false)
      resetForm()
      toast({ title: "Skill created" })
    },
    onError: (error: any) => {
      toast({
        title: "Failed to create skill",
        description: error.response?.data?.detail || "Unknown error",
        variant: "destructive",
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: any }) => {
      const { data } = await api.patch(`/skills/${id}`, payload)
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      setDetailSkill(data)
      setShowCreateModal(false)
      resetForm()
      toast({ title: "Skill updated" })
    },
    onError: (error: any) => {
      toast({
        title: "Failed to update skill",
        description: error.response?.data?.detail || "Unknown error",
        variant: "destructive",
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/skills/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      setDetailSkill(null)
      setShowCreateModal(false)
      resetForm()
      toast({ title: "Skill deleted" })
    },
    onError: (error: any) => {
      toast({
        title: "Failed to delete skill",
        description: error.response?.data?.detail || "Unknown error",
        variant: "destructive",
      })
    },
  })

  // ----- Derived stats -----
  const stats = useMemo(() => {
    const total = skills.length
    const active = skills.filter((s) => s.builtin_tools.length > 0).length
    const totalTools = skills.reduce((sum, s) => sum + s.builtin_tools.length, 0)
    const withTemplates = skills.filter((s) => s.prompt_template && s.prompt_template.trim().length > 0).length
    const successRate = total > 0 ? Math.round((withTemplates / total) * 100) : 0
    return { total, active, totalTools, successRate }
  }, [skills])

  // ----- Categories from tags -----
  const categories = useMemo(() => {
    const cats = new Set<string>()
    skills.forEach((s) => {
      if (s.tags?.length) {
        s.tags.forEach((t) => cats.add(t))
      }
    })
    return Array.from(cats).sort()
  }, [skills])

  // ----- Filtered skills -----
  const filteredSkills = useMemo(() => {
    return skills.filter((skill) => {
      const matchesSearch =
        searchQuery === "" ||
        skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (skill.description?.toLowerCase() || "").includes(searchQuery.toLowerCase())
      const matchesCategory =
        categoryFilter === "all" ||
        (skill.tags && skill.tags.includes(categoryFilter))
      return matchesSearch && matchesCategory
    })
  }, [skills, searchQuery, categoryFilter])

  // ----- Form helpers -----
  const resetForm = () => {
    setForm({
      name: "",
      description: "",
      prompt_template: "",
      builtin_tools: [],
      custom_tools: [],
      input_schema: "",
      output_schema: "",
      tags: [],
      is_public: false,
    })
    setTagInput("")
    setIsEditing(false)
  }

  const openCreateModal = () => {
    resetForm()
    setIsEditing(false)
    setShowCreateModal(true)
  }

  const openEditModal = (skill: Skill) => {
    setForm({
      name: skill.name,
      description: skill.description || "",
      prompt_template: skill.prompt_template || "",
      builtin_tools: skill.builtin_tools || [],
      custom_tools: skill.custom_tools || [],
      input_schema: skill.input_schema ? JSON.stringify(skill.input_schema, null, 2) : "",
      output_schema: skill.output_schema ? JSON.stringify(skill.output_schema, null, 2) : "",
      tags: skill.tags || [],
      is_public: skill.is_public,
    })
    setTagInput((skill.tags || []).join(", "))
    setIsEditing(true)
    setDetailSkill(skill)
    setShowCreateModal(true)
  }

  const buildPayload = () => {
    let input_schema = null
    let output_schema = null
    try {
      if (form.input_schema.trim()) input_schema = JSON.parse(form.input_schema)
    } catch {
      toast({ title: "Invalid input schema JSON", variant: "destructive" })
      return null
    }
    try {
      if (form.output_schema.trim()) output_schema = JSON.parse(form.output_schema)
    } catch {
      toast({ title: "Invalid output schema JSON", variant: "destructive" })
      return null
    }
    return {
      name: form.name,
      description: form.description,
      prompt_template: form.prompt_template,
      builtin_tools: form.builtin_tools,
      custom_tools: form.custom_tools,
      input_schema,
      output_schema,
      tags: tagInput
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      is_public: form.is_public,
    }
  }

  const handleSave = () => {
    if (!form.name.trim()) {
      toast({ title: "Name is required", variant: "destructive" })
      return
    }
    if (!form.prompt_template.trim()) {
      toast({ title: "Prompt template is required", variant: "destructive" })
      return
    }
    const payload = buildPayload()
    if (!payload) return

    if (!isEditing) {
      createMutation.mutate(payload)
    } else if (detailSkill) {
      updateMutation.mutate({ id: detailSkill.id, payload })
    }
  }

  const toggleBuiltinTool = (toolName: string) => {
    setForm((prev) => ({
      ...prev,
      builtin_tools: prev.builtin_tools.includes(toolName)
        ? prev.builtin_tools.filter((t) => t !== toolName)
        : [...prev.builtin_tools, toolName],
    }))
  }

  const updateForm = (field: string, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleExport = async () => {
    setIsExporting(true)
    try {
      const bundle = await exportSkillsAndAgents()
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `academic-pal-export-${new Date().toISOString().split("T")[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast({ title: "Export complete", description: "Your skills and agents have been exported." })
    } catch (error: any) {
      toast({
        title: "Export failed",
        description: error.response?.data?.detail || error.message || "Unknown error",
        variant: "destructive",
      })
    } finally {
      setIsExporting(false)
    }
  }

  // ========================================================================
  // Stats config
  // ========================================================================

  const statCards = [
    {
      label: "Total Skills",
      value: stats.total,
      icon: Puzzle,
      suffix: "custom skills",
      color: "text-primary bg-primary/10",
    },
    {
      label: "Active",
      value: stats.active,
      icon: Activity,
      suffix: "with tools assigned",
      color: "text-emerald-400 bg-emerald-500/10",
    },
    {
      label: "Tool Bindings",
      value: stats.totalTools,
      icon: Wrench,
      suffix: "across all skills",
      color: "text-amber-400 bg-amber-500/10",
    },
    {
      label: "Template Rate",
      value: `${stats.successRate}%`,
      icon: BarChart3,
      suffix: "skills with prompts",
      color: "text-sky-400 bg-sky-500/10",
    },
  ]

  // ========================================================================
  // Loading state
  // ========================================================================

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Scholar Skills"
          description="Manage and organize your agent skills — reusable prompt templates with tool bindings"
        />
        <LoadingState label="Loading skills..." size="lg" />
      </div>
    )
  }

  // ========================================================================
  // Render
  // ========================================================================

  return (
    <div className="space-y-8">
      {/* ================================================================= */}
      {/* Hero                                                              */}
      {/* ================================================================= */}
      <PageHeader
        title="Scholar Skills"
        description="Manage and organize your agent skills — reusable prompt templates with tool bindings"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={isExporting}
              className="gap-2"
            >
              <Download className={cn("h-4 w-4", isExporting && "animate-spin")} />
              {isExporting ? "Exporting..." : "Export"}
            </Button>
            <Button onClick={openCreateModal} className="gap-2">
              <Plus className="h-4 w-4" />
              New Skill
            </Button>
          </div>
        }
      />

      {/* ================================================================= */}
      {/* Stats Row                                                         */}
      {/* ================================================================= */}
      <section>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {statCards.map((stat) => {
            const StatIcon = stat.icon
            return (
              <div
                key={stat.label}
                className="group rounded-xl border border-border/50 bg-card/60 p-5 backdrop-blur-xl transition-all duration-300 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
              >
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    {stat.label}
                  </span>
                  <div
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-lg",
                      stat.color,
                    )}
                  >
                    <StatIcon className="h-4 w-4" />
                  </div>
                </div>
                <div className="font-display text-3xl font-semibold text-foreground">
                  {stat.value}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{stat.suffix}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* ================================================================= */}
      {/* Filters                                                           */}
      {/* ================================================================= */}
      <section>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
            <Select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              options={[
                { value: "all", label: "All Categories" },
                ...categories.map((c) => ({ value: c, label: c.charAt(0).toUpperCase() + c.slice(1) })),
              ]}
              className="w-44"
            />
          </div>
        </div>
      </section>

      {/* ================================================================= */}
      {/* Skill Cards Grid                                                  */}
      {/* ================================================================= */}
      <section>
        {filteredSkills.length > 0 ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {filteredSkills.map((skill, index) => {
              const SkillIcon = getSkillIcon(skill.name)
              const iconColor = pickColor(index)
              return (
                <div
                  key={skill.id}
                  className="group relative overflow-hidden rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl transition-all duration-300 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/10"
                >
                  {/* Hover glow */}
                  <div
                    aria-hidden="true"
                    className="pointer-events-none absolute -inset-px rounded-xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                    style={{
                      background:
                    "radial-gradient(600px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), color-mix(in srgb, hsl(var(--primary)) 6%, transparent), transparent 40%)",
                    }}
                  />

                  <div className="relative p-5">
                    {/* Header: icon + badges */}
                    <div className="mb-4 flex items-start justify-between">
                      <div
                        className={cn(
                          "flex h-10 w-10 items-center justify-center rounded-lg",
                          iconColor,
                        )}
                      >
                        <SkillIcon className="h-5 w-5" />
                      </div>
                      <div className="flex items-center gap-1.5">
                        {skill.is_public ? (
                          <StatusBadge status="success" label="Public" />
                        ) : (
                          <StatusBadge status="info" label="Private" />
                        )}
                      </div>
                    </div>

                    {/* Name */}
                    <h3 className="mb-1 font-display text-lg font-semibold text-foreground">
                      {skill.name}
                    </h3>

                    {/* Description */}
                    <p className="mb-4 text-sm text-muted-foreground line-clamp-2">
                      {skill.description || "No description provided"}
                    </p>

                    {/* Stats row */}
                    <div className="mb-4 flex items-center gap-4 text-xs text-muted-foreground">
                      {skill.builtin_tools.length > 0 && (
                        <span className="flex items-center gap-1">
                          <Wrench className="h-3 w-3" />
                          {skill.builtin_tools.length} tool{skill.builtin_tools.length !== 1 ? "s" : ""}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Activity className="h-3 w-3" />
                        {skill.tags.length > 0
                          ? `${skill.tags.length} tag${skill.tags.length !== 1 ? "s" : ""}`
                          : "No tags"}
                      </span>
                    </div>

                    {/* Tools badges */}
                    {skill.builtin_tools.length > 0 && (
                      <div className="mb-4 flex flex-wrap gap-1.5">
                        {skill.builtin_tools.slice(0, 3).map((t) => (
                          <Badge
                            key={t}
                            variant="secondary"
                            className="text-[10px] font-normal"
                          >
                            {t}
                          </Badge>
                        ))}
                        {skill.builtin_tools.length > 3 && (
                          <Badge variant="secondary" className="text-[10px] font-normal">
                            +{skill.builtin_tools.length - 3}
                          </Badge>
                        )}
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="default"
                        className="flex-1 gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
                        onClick={() => setDetailSkill(skill)}
                      >
                        <Eye className="h-3.5 w-3.5" />
                        View
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-1.5"
                        onClick={() => openEditModal(skill)}
                      >
                        <Wrench className="h-3.5 w-3.5" />
                        Edit
                      </Button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <EmptyState
            icon={Puzzle}
            title={searchQuery || categoryFilter !== "all" ? "No matching skills" : "No skills yet"}
            description={
              searchQuery || categoryFilter !== "all"
                ? "Try adjusting your search or filter to find what you're looking for."
                : "Create your first skill to get started with reusable prompt templates and tool bindings."
            }
            action={
              searchQuery || categoryFilter !== "all"
                ? undefined
                : { label: "Create Skill", onClick: openCreateModal }
            }
          />
        )}
      </section>

      {/* ================================================================= */}
      {/* Detail Modal                                                      */}
      {/* ================================================================= */}
      <ModalShell
        open={!!detailSkill && !showCreateModal}
        onOpenChange={(open) => {
          if (!open) setDetailSkill(null)
        }}
        title={detailSkill?.name || ""}
        description={detailSkill?.description || ""}
        size="lg"
        footer={
          <div className="flex w-full items-center justify-between">
            <div className="flex items-center gap-2">
              {detailSkill && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    if (detailSkill) deleteMutation.mutate(detailSkill.id)
                  }}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Delete
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              {detailSkill && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (detailSkill) openEditModal(detailSkill)
                  }}
                >
                  <Wrench className="h-4 w-4 mr-1" />
                  Edit
                </Button>
              )}
              <Button
                size="sm"
                className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Play className="h-4 w-4" />
                Use this skill
              </Button>
            </div>
          </div>
        }
      >
        {detailSkill && (
          <div className="space-y-6">
            {/* Meta info */}
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge
                status={detailSkill.is_public ? "success" : "info"}
                label={detailSkill.is_public ? "Public" : "Private"}
              />
              <span className="text-xs text-muted-foreground">
                Created {formatDate(detailSkill.created_at)}
              </span>
              <span className="text-xs text-muted-foreground">
                Updated {formatDate(detailSkill.updated_at)}
              </span>
            </div>

            {/* Tags */}
            {detailSkill.tags && detailSkill.tags.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-medium text-foreground">Categories</h4>
                <div className="flex flex-wrap gap-1.5">
                  {detailSkill.tags.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Builtin tools */}
            {detailSkill.builtin_tools && detailSkill.builtin_tools.length > 0 && (
              <div>
                <h4 className="mb-2 flex items-center gap-1.5 text-sm font-medium text-foreground">
                  <Wrench className="h-3.5 w-3.5 text-primary" />
                  Builtin Tools
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {detailSkill.builtin_tools.map((tool) => (
                    <Badge key={tool} variant="outline" className="border-primary/20 text-primary">
                      {tool}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Parameters (input/output schemas) */}
            {(detailSkill.input_schema || detailSkill.output_schema) && (
              <div>
                <h4 className="mb-2 flex items-center gap-1.5 text-sm font-medium text-foreground">
                  <SlidersHorizontal className="h-3.5 w-3.5 text-primary" />
                  Parameters
                </h4>
                <div className="space-y-3">
                  {detailSkill.input_schema && (
                    <div>
                      <p className="mb-1 text-xs font-medium text-muted-foreground">Input Schema</p>
                      <pre className="max-h-32 overflow-auto rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
                        {JSON.stringify(detailSkill.input_schema, null, 2)}
                      </pre>
                    </div>
                  )}
                  {detailSkill.output_schema && (
                    <div>
                      <p className="mb-1 text-xs font-medium text-muted-foreground">Output Schema</p>
                      <pre className="max-h-32 overflow-auto rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
                        {JSON.stringify(detailSkill.output_schema, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Prompt template */}
            {detailSkill.prompt_template && (
              <div>
                <h4 className="mb-2 flex items-center gap-1.5 text-sm font-medium text-foreground">
                  <Terminal className="h-3.5 w-3.5 text-primary" />
                  Prompt Template
                </h4>
                <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
                  {detailSkill.prompt_template}
                </pre>
              </div>
            )}

            {/* Usage stats (derived) */}
            <div>
              <h4 className="mb-2 flex items-center gap-1.5 text-sm font-medium text-foreground">
                <Activity className="h-3.5 w-3.5 text-primary" />
                Usage Summary
              </h4>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-border/50 bg-muted/30 p-3">
                  <p className="text-xs text-muted-foreground">Tool Bindings</p>
                  <p className="mt-0.5 font-display text-xl font-semibold text-foreground">
                    {detailSkill.builtin_tools.length}
                  </p>
                </div>
                <div className="rounded-lg border border-border/50 bg-muted/30 p-3">
                  <p className="text-xs text-muted-foreground">Categories/Tags</p>
                  <p className="mt-0.5 font-display text-xl font-semibold text-foreground">
                    {detailSkill.tags.length}
                  </p>
                </div>
                <div className="rounded-lg border border-border/50 bg-muted/30 p-3">
                  <p className="text-xs text-muted-foreground">Has Template</p>
                  <p className="mt-0.5 font-display text-xl font-semibold text-foreground">
                    {detailSkill.prompt_template ? "Yes" : "No"}
                  </p>
                </div>
                <div className="rounded-lg border border-border/50 bg-muted/30 p-3">
                  <p className="text-xs text-muted-foreground">Custom Tools</p>
                  <p className="mt-0.5 font-display text-xl font-semibold text-foreground">
                    {detailSkill.custom_tools?.length || 0}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </ModalShell>

      {/* ================================================================= */}
      {/* Create / Edit Modal                                               */}
      {/* ================================================================= */}
      <ModalShell
        open={showCreateModal}
        onOpenChange={(open) => {
          if (!open) {
            setShowCreateModal(false)
            resetForm()
          }
        }}
        title={isEditing ? `Edit: ${detailSkill?.name}` : "New Skill"}
        description={
          isEditing
            ? "Modify this skill's configuration"
            : "Define what this skill does and how agents should use it"
        }
        size="xl"
        footer={
          <div className="flex w-full items-center justify-between">
            <div>
              {isEditing && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    if (detailSkill) {
                      deleteMutation.mutate(detailSkill.id)
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Delete
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowCreateModal(false)
                  resetForm()
                }}
              >
                Cancel
              </Button>
              <Button size="sm" onClick={handleSave}>
                <Save className="h-4 w-4 mr-1" />
                {isEditing ? "Update" : "Create"}
              </Button>
            </div>
          </div>
        }
      >
        <div className="space-y-5">
          {/* Name + Visibility */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input
                value={form.name}
                onChange={(e) => updateForm("name", e.target.value)}
                placeholder="e.g. Literature Reviewer"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Visibility</label>
              <div className="flex items-center gap-2 mt-2">
                <button
                  type="button"
                  onClick={() => updateForm("is_public", false)}
                  className={cn(
                    "flex items-center gap-1 px-3 py-1.5 rounded-md text-sm border transition-colors",
                    !form.is_public
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border text-muted-foreground hover:border-muted-foreground/40",
                  )}
                >
                  <Lock className="h-3 w-3" /> Private
                </button>
                <button
                  type="button"
                  onClick={() => updateForm("is_public", true)}
                  className={cn(
                    "flex items-center gap-1 px-3 py-1.5 rounded-md text-sm border transition-colors",
                    form.is_public
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border text-muted-foreground hover:border-muted-foreground/40",
                  )}
                >
                  <Globe className="h-3 w-3" /> Public
                </button>
              </div>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="text-sm font-medium">Description</label>
            <Input
              value={form.description}
              onChange={(e) => updateForm("description", e.target.value)}
              placeholder="What does this skill help with?"
            />
          </div>

          {/* Tags */}
          <div>
            <label className="text-sm font-medium">Tags</label>
            <Input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              placeholder="e.g. research, writing, review (comma-separated)"
            />
          </div>

          {/* Prompt Template */}
          <div>
            <label className="text-sm font-medium">Prompt Template</label>
            <Textarea
              value={form.prompt_template}
              onChange={(e) => updateForm("prompt_template", e.target.value)}
              placeholder={`You are an expert academic reviewer. 

Your task is to review the following paper:

{{paper_text}}

Provide feedback on:
1. Methodology
2. Writing quality
3. Contribution to the field`}
              rows={8}
              className="font-mono text-sm mt-1"
            />
            <p className="text-xs text-muted-foreground mt-1.5">
              Tip: Use {"{{variable_name}}"} for placeholders that will be filled at runtime.
            </p>
          </div>

          {/* Builtin Tools */}
          <div>
            <label className="mb-2 flex items-center gap-1.5 text-sm font-medium">
              <Wrench className="h-3.5 w-3.5 text-primary" />
              Builtin Tools
            </label>
            <div className="grid grid-cols-2 gap-2">
              {builtinTools.map((tool) => (
                <label
                  key={tool.name}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                    form.builtin_tools.includes(tool.name)
                      ? "border-primary/40 bg-primary/5"
                      : "border-border hover:border-muted-foreground/40",
                  )}
                >
                  <input
                    type="checkbox"
                    checked={form.builtin_tools.includes(tool.name)}
                    onChange={() => toggleBuiltinTool(tool.name)}
                    className="mt-0.5"
                  />
                  <div>
                    <span className="text-sm font-medium">{tool.name}</span>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {tool.description}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Schemas */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">Input Schema (JSON)</label>
              <Textarea
                value={form.input_schema}
                onChange={(e) => updateForm("input_schema", e.target.value)}
                placeholder={`{
  "type": "object",
  "properties": {
    "paper_text": { "type": "string" }
  },
  "required": ["paper_text"]
}`}
                rows={6}
                className="font-mono text-sm mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Output Schema (JSON)</label>
              <Textarea
                value={form.output_schema}
                onChange={(e) => updateForm("output_schema", e.target.value)}
                placeholder={`{
  "type": "object",
  "properties": {
    "summary": { "type": "string" },
    "score": { "type": "number" }
  }
}`}
                rows={6}
                className="font-mono text-sm mt-1"
              />
            </div>
          </div>
        </div>
      </ModalShell>
    </div>
  )
}
