import { useState, useCallback, useRef, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { PageHeader } from "@/components/shared/PageHeader"
import { PaperCard } from "@/components/shared/PaperCard"
import type { StoredPaper } from "@/components/shared/PaperCard"
import { HealthStatus, type ProviderHealth } from "@/components/shared/HealthStatus"
import { EmptyState } from "@/components/shared/EmptyState"
import { ModalShell } from "@/components/shared/ModalShell"
import { ScoreDisplay } from "@/components/shared/ScoreDisplay"
import type { Scores } from "@/components/shared/ScoreDisplay"
import {
  Search,
  Upload,
  FileText,
  Settings as SettingsIcon,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
  FileUp,
  UploadCloud,
  Sparkles,
  Trash2,
  Library,
  BookmarkCheck,
  Tags,
  Globe,
  ChevronDown,
  Tag,
  BookOpen,
  Calendar,
  ArrowUpFromLine,
  SlidersHorizontal,
  Plus,
} from "lucide-react"

// ----- Types -----

interface Asset {
  id: string
  title: string
  authors: string[]
  abstract?: string
  doi?: string
  arxiv_id?: string
  year?: number
  venue?: string
  doc_type: string
  tags: string[]
  analysis?: AssetAnalysis
  created_at: string
  updated_at: string
}

interface AssetAnalysis {
  summary?: string
  key_findings?: string[]
  methodology?: string
  contributions?: string[]
  limitations?: string[]
  keywords?: string[]
  auto_tags?: string[]
  scientific_areas?: string[]
  field_of_study?: string
  subfield?: string
  references?: { index: number; text: string; authors: string[]; year: number }[]
  strengths_weaknesses?: {
    strengths: { point: string; evidence: string }[]
    weaknesses: { point: string; evidence: string }[]
    suggestions: string[]
    quality_score: number
    quality_rationale: string
  }
}

interface UploadItem {
  id: string
  file: File
  status: "pending" | "uploading" | "done" | "error"
  progress: number
  error?: string
  result?: Asset
}

// ----- Constants -----

const DOC_TYPES = [
  { value: "paper", label: "Research Paper", icon: "📄" },
  { value: "proposal", label: "Grant Proposal", icon: "📋" },
  { value: "review", label: "Literature Review", icon: "📚" },
  { value: "report", label: "Technical Report", icon: "📊" },
  { value: "other", label: "Other", icon: "📎" },
]

const STATUS_FILTERS = [
  { value: "all", label: "All" },
  { value: "analyzed", label: "Analyzed" },
  { value: "unanalyzed", label: "Unanalyzed" },
] as const

const SOURCE_OPTIONS = [
  { value: "arxiv", label: "arXiv", icon: BookOpen },
  { value: "semantic_scholar", label: "Semantic Scholar", icon: Search },
  { value: "openalex", label: "OpenAlex", icon: Globe },
  { value: "crossref", label: "CrossRef", icon: BookmarkCheck },
] as const

type StatusFilterValue = (typeof STATUS_FILTERS)[number]["value"]

// ----- Helpers -----

function extractScores(asset: Asset): Scores | undefined {
  if (!asset.analysis?.strengths_weaknesses?.quality_score) return undefined
  const q = asset.analysis.strengths_weaknesses.quality_score
  return { quality: q, novelty: q, rigor: q, clarity: q }
}

// ----- Component -----

export default function AssetsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Dialog state (legacy upload dialog → now using ModalShell)
  const [dialogOpen, setDialogOpen] = useState(false)

  // Search & filter state
  const [searchQuery, setSearchQuery] = useState("")
  const [activeFilter, setActiveFilter] = useState<StatusFilterValue>("all")
  const [selectedSources, setSelectedSources] = useState<string[]>([])
  const [tagFilter, setTagFilter] = useState<string | null>(null)

  // Upload state
  const [uploads, setUploads] = useState<UploadItem[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [selectedDocType, setSelectedDocType] = useState("paper")
  const [urlInput, setUrlInput] = useState("")

  // Action state
  const [analyzing, setAnalyzing] = useState<string | null>(null)

  // Modal states
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null)
  const [tagModalOpen, setTagModalOpen] = useState(false)
  const [settingsModalOpen, setSettingsModalOpen] = useState(false)
  const [newTagInput, setNewTagInput] = useState("")
  const [tagTargetId, setTagTargetId] = useState<string | null>(null)

  // ----- Queries -----

  const { data: assets = [], isLoading } = useQuery<Asset[]>({
    queryKey: ["assets"],
    queryFn: async () => {
      const { data } = await api.get("/assets")
      return data.items || []
    },
  })

  const { data: settings } = useQuery({
    queryKey: ["settings-providers"],
    queryFn: async () => {
      const { data } = await api.get("/settings/providers")
      return data
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  })

  // ----- Computed -----

  const providers: ProviderHealth[] = useMemo(() => {
    if (!settings?.providers) return []
    return Object.entries(settings.providers).map(([name, info]: [string, any]) => ({
      name,
      status:
        info.status === "connected"
          ? "healthy"
          : info.status === "error"
            ? "unhealthy"
            : info.status
              ? "healthy"
              : "unknown",
      latency: info.latency || undefined,
    }))
  }, [settings])

  const stats = useMemo(() => {
    const total = assets.length
    const analyzed = assets.filter((a) => !!a.analysis).length
    const allTags = new Set(assets.flatMap((a) => a.tags))
    const hasArxiv = assets.some((a) => !!a.arxiv_id)
    const hasDoi = assets.some((a) => !!a.doi)
    const activeSources = [hasArxiv, hasDoi].filter(Boolean).length + 1
    return { total, analyzed, uniqueTags: allTags.size, activeSources }
  }, [assets])

  const allTags = useMemo(() => {
    const tagSet = new Set<string>()
    assets.forEach((a) => a.tags.forEach((t) => tagSet.add(t)))
    return Array.from(tagSet).sort()
  }, [assets])

  const tagCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    assets.forEach((a) => a.tags.forEach((t) => (counts[t] = (counts[t] || 0) + 1)))
    return counts
  }, [assets])

  const selectedPaper = useMemo(() => {
    if (!selectedPaperId) return null
    return assets.find((a) => a.id === selectedPaperId) || null
  }, [assets, selectedPaperId])

  const filteredAssets = useMemo(() => {
    let result = [...assets]

    // Local search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (a) =>
          a.title?.toLowerCase().includes(q) ||
          a.abstract?.toLowerCase().includes(q) ||
          a.authors?.some((au) => au.toLowerCase().includes(q)) ||
          a.tags?.some((t) => t.toLowerCase().includes(q)),
      )
    }

    // Status filter
    switch (activeFilter) {
      case "analyzed":
        result = result.filter((a) => !!a.analysis)
        break
      case "unanalyzed":
        result = result.filter((a) => !a.analysis)
        break
    }

    // Tag filter
    if (tagFilter) {
      result = result.filter((a) => a.tags.includes(tagFilter!))
    }

    // Source filter
    if (selectedSources.length > 0) {
      result = result.filter((a) => {
        const matchesArxiv = selectedSources.includes("arxiv") && !!a.arxiv_id
        const matchesDoi = selectedSources.includes("crossref") && !!a.doi
        const matchesSs =
          selectedSources.includes("semantic_scholar") &&
          a.tags?.some((t) => t.toLowerCase().includes("semantic"))
        const matchesOa =
          selectedSources.includes("openalex") &&
          a.tags?.some((t) => t.toLowerCase().includes("openalex"))
        return matchesArxiv || matchesDoi || matchesSs || matchesOa
      })
    }

    return result
  }, [assets, searchQuery, activeFilter, tagFilter, selectedSources])

  const mappedPapers: StoredPaper[] = useMemo(() => {
    return filteredAssets.map((asset) => ({
      id: asset.id,
      title: asset.title || "Untitled",
      abstract: asset.abstract,
      year: asset.year,
      authors: asset.authors,
      tags: asset.tags,
      field: asset.analysis?.field_of_study,
      scores: extractScores(asset),
      is_analyzed: !!asset.analysis,
    }))
  }, [filteredAssets])

  // ----- Mutations -----

  const searchMutation = useMutation({
    mutationFn: async (query: string) => {
      const { data } = await api.get(`/assets/search?q=${encodeURIComponent(query)}`)
      return data
    },
    onSuccess: () => {
      toast({ title: "Search complete" })
    },
  })

  const analyzeMutation = useMutation({
    mutationFn: async (assetId: string) => {
      const { data } = await api.post(`/assets/${assetId}/analyze`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] })
      setAnalyzing(null)
      toast({ title: "Analysis complete" })
    },
    onError: () => {
      setAnalyzing(null)
      toast({ title: "Analysis failed", variant: "destructive" })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (assetId: string) => {
      await api.delete(`/assets/${assetId}`)
    },
    onSuccess: () => {
      toast({ title: "Asset deleted" })
      queryClient.invalidateQueries({ queryKey: ["assets"] })
    },
    onError: () => {
      toast({ title: "Failed to delete asset", variant: "destructive" })
    },
  })

  const updateAssetMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Pick<Asset, "tags">> }) => {
      const response = await api.patch(`/assets/${id}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] })
    },
    onError: () => {
      toast({ title: "Failed to update asset", variant: "destructive" })
    },
  })

  // ----- Upload handlers -----

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      const newUploads: UploadItem[] = Array.from(files)
        .filter((f) => f.type === "application/pdf" || f.name.endsWith(".pdf"))
        .map((f) => ({
          id: `${f.name}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          file: f,
          status: "pending" as const,
          progress: 0,
        }))

      if (newUploads.length === 0) {
        toast({ title: "Only PDF files are supported", variant: "destructive" })
        return
      }

      setUploads((prev) => [...prev, ...newUploads])
    },
    [toast],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragActive(false)
      if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files)
    },
    [handleFiles],
  )

  const removeUpload = (id: string) => setUploads((prev) => prev.filter((u) => u.id !== id))

  const clearCompleted = () =>
    setUploads((prev) => prev.filter((u) => u.status !== "done" && u.status !== "error"))

  const startUpload = async () => {
    const pending = uploads.filter((u) => u.status === "pending")
    if (pending.length === 0) return

    for (const item of pending) {
      setUploads((prev) =>
        prev.map((u) => (u.id === item.id ? { ...u, status: "uploading" as const, progress: 10 } : u)),
      )

      try {
        const formData = new FormData()
        formData.append("file", item.file)
        formData.append("doc_type", selectedDocType)

        const { data } = await api.post("/assets/", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        })

        setUploads((prev) =>
          prev.map((u) =>
            u.id === item.id ? { ...u, status: "done" as const, progress: 100, result: data } : u,
          ),
        )
      } catch (error: any) {
        setUploads((prev) =>
          prev.map((u) =>
            u.id === item.id
              ? { ...u, status: "error" as const, error: error.response?.data?.detail || "Upload failed" }
              : u,
          ),
        )
      }
    }

    queryClient.invalidateQueries({ queryKey: ["assets"] })
    toast({ title: `Uploaded ${pending.length} file(s)` })
  }

  // ----- Tag handlers -----

  const handleAddTag = useCallback(() => {
    if (!newTagInput.trim() || !tagTargetId) return
    const asset = assets.find((a) => a.id === tagTargetId)
    if (!asset) return
    const updatedTags = [...new Set([...asset.tags, newTagInput.trim()])]
    updateAssetMutation.mutate({ id: tagTargetId, data: { tags: updatedTags } })
    setNewTagInput("")
    toast({ title: `Tag "${newTagInput.trim()}" added` })
  }, [newTagInput, tagTargetId, assets, updateAssetMutation, toast])

  const handleRemoveTag = useCallback(
    (tagToRemove: string) => {
      if (!tagTargetId) return
      const asset = assets.find((a) => a.id === tagTargetId)
      if (!asset) return
      const updatedTags = asset.tags.filter((t) => t !== tagToRemove)
      updateAssetMutation.mutate({ id: tagTargetId, data: { tags: updatedTags } })
      toast({ title: `Tag "${tagToRemove}" removed` })
    },
    [tagTargetId, assets, updateAssetMutation, toast],
  )

  // ----- Search handler -----

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      searchMutation.mutate(searchQuery)
    }
  }

  // ----- Source filter toggle -----

  const toggleSource = (value: string) => {
    setSelectedSources((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value],
    )
  }

  // ----- Render -----

  return (
    <div className="space-y-6">
      {/* ── Page Header ── */}
      <PageHeader
        title="Paper Library"
        description="Your collection of papers, analyses, and academic resources"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSettingsModalOpen(true)}
              className="border-border/50"
            >
              <SettingsIcon className="mr-1.5 h-4 w-4" />
              Settings
            </Button>
            <Button
              className="bg-gradient-to-r from-primary to-primary text-primary-foreground hover:from-primary/90 hover:to-primary/80 shadow-lg shadow-primary/20"
              onClick={() => setDialogOpen(true)}
            >
              <Upload className="mr-2 h-4 w-4" />
              Upload
            </Button>
          </div>
        }
      />

      {/* ── Stats Row ── */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { icon: Library, label: "Total Papers", value: stats.total, color: "text-primary" },
          {
            icon: BookmarkCheck,
            label: "Analyzed",
            value: `${stats.analyzed} / ${stats.total}`,
            color: "text-emerald-500",
          },
          { icon: Tags, label: "Unique Tags", value: stats.uniqueTags, color: "text-sky-500" },
          { icon: Globe, label: "Active Sources", value: stats.activeSources, color: "text-amber-500" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="group relative overflow-hidden rounded-xl border border-border/40 bg-card/60 p-4 backdrop-blur-xl transition-all duration-200 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5"
          >
            <div className="absolute inset-x-0 top-0 h-0.5 scale-x-0 bg-gradient-to-r from-transparent via-primary/40 to-transparent transition-transform duration-300 group-hover:scale-x-100" />
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <stat.icon className={cn("h-5 w-5", stat.color)} />
              </div>
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-muted-foreground">{stat.label}</p>
                <p className="text-lg font-semibold text-foreground tabular-nums">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Search + Filters ── */}
      <div className="space-y-3">
        <form onSubmit={handleSearch} className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by title, author, or topic…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 focus-visible:ring-primary/50 pr-20"
          />
          <Button
            type="submit"
            size="sm"
            variant="secondary"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 h-7"
            disabled={searchMutation.isPending}
          >
            {searchMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Search"}
          </Button>
        </form>

        <div className="flex flex-wrap items-center gap-2">
          {/* Status filter chips */}
          {STATUS_FILTERS.map((filter) => (
            <button
              key={filter.value}
              onClick={() => setActiveFilter(filter.value)}
              className={cn(
                "inline-flex items-center rounded-full px-3.5 py-1.5 text-xs font-medium transition-all duration-200",
                activeFilter === filter.value
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "bg-primary/10 text-muted-foreground hover:bg-primary/20 hover:text-foreground",
              )}
            >
              {filter.label}
            </button>
          ))}

          {/* Tag filter chip — show active tag if any */}
          {tagFilter && (
            <button
              onClick={() => setTagFilter(null)}
              className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary transition-all hover:bg-primary/20"
            >
              <Tag className="h-3 w-3" />
              {tagFilter}
              <X className="h-3 w-3 ml-0.5" />
            </button>
          )}

          {/* Source filter — Popover multi-select */}
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className={cn(
                  "border-border/50 text-xs",
                  selectedSources.length > 0 && "border-primary/50 text-primary",
                )}
              >
                <SlidersHorizontal className="mr-1.5 h-3.5 w-3.5" />
                Sources
                {selectedSources.length > 0 && (
                  <span className="ml-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary/20 text-[10px] font-bold">
                    {selectedSources.length}
                  </span>
                )}
                <ChevronDown className="ml-1.5 h-3 w-3 text-muted-foreground" />
              </Button>
            </PopoverTrigger>
            <PopoverContent align="start" className="w-56 p-2">
              <div className="space-y-1">
                <p className="px-2 py-1 text-xs font-medium text-muted-foreground">Filter by source</p>
                {SOURCE_OPTIONS.map((source) => {
                  const selected = selectedSources.includes(source.value)
                  const Icon = source.icon
                  return (
                    <button
                      key={source.value}
                      onClick={() => toggleSource(source.value)}
                      className={cn(
                        "flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
                        selected
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-primary/10 hover:text-foreground",
                      )}
                    >
                      <div
                        className={cn(
                          "flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors",
                          selected
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border",
                        )}
                      >
                        {selected && <CheckCircle className="h-3 w-3" />}
                      </div>
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                      {source.label}
                    </button>
                  )
                })}
                {selectedSources.length > 0 && (
                  <button
                    onClick={() => setSelectedSources([])}
                    className="mt-1 w-full rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Clear filters
                  </button>
                )}
              </div>
            </PopoverContent>
          </Popover>

          {/* Tag manager button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setTagModalOpen(true)
              if (mappedPapers.length > 0) setTagTargetId(mappedPapers[0].id)
            }}
            className="border-border/50 text-xs"
          >
            <Tags className="mr-1.5 h-3.5 w-3.5" />
            Tags
          </Button>
        </div>
      </div>

      {/* ── Paper Grid / Loading / Empty ── */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="group relative overflow-hidden rounded-xl border border-border/40 bg-card/60 backdrop-blur-xl p-5 animate-pulse"
            >
              <div className="absolute inset-x-0 top-0 h-0.5 scale-x-0 bg-gradient-to-r from-transparent via-primary/40 to-transparent transition-transform duration-300" />
              <div className="h-4 bg-muted/30 rounded w-3/4 mb-3" />
              <div className="h-3 bg-muted/20 rounded w-1/2 mb-4" />
              <div className="h-3 bg-muted/20 rounded w-full mb-2" />
              <div className="h-3 bg-muted/20 rounded w-2/3 mb-4" />
              <div className="flex gap-2">
                <div className="h-6 bg-muted/20 rounded-full w-16" />
                <div className="h-6 bg-muted/20 rounded-full w-12" />
              </div>
            </div>
          ))}
        </div>
      ) : mappedPapers.length === 0 ? (
        <EmptyState
          icon={ArrowUpFromLine}
          title="No papers yet"
          description="Upload your first paper to get started with analysis and insights."
          action={{
            label: "Upload Paper",
            onClick: () => setDialogOpen(true),
          }}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {mappedPapers.map((paper) => (
            <div key={paper.id} className="group/card relative">
              <PaperCard
                variant="stored"
                paper={paper}
                onClick={() => {
                  setSelectedPaperId(paper.id)
                  setDetailModalOpen(true)
                }}
              />

              {/* Action buttons — visible on hover */}
              <div className="mt-2 flex items-center justify-end gap-1 opacity-0 transition-opacity duration-200 group-hover/card:opacity-100">
                <button
                  onClick={() => {
                    setAnalyzing(paper.id)
                    analyzeMutation.mutate(paper.id)
                  }}
                  disabled={analyzing === paper.id}
                  className="inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                  title="Analyze paper"
                >
                  {analyzing === paper.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                </button>
                <button
                  onClick={() => deleteMutation.mutate(paper.id)}
                  className="inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors"
                  title="Delete paper"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Modal: Upload ── */}
      <ModalShell
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Upload Research Asset"
        description="Upload PDF files to your library for analysis and management"
        size="xl"
        footer={
          <div className="flex w-full items-center justify-between">
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={startUpload}
              disabled={!uploads.some((u) => u.status === "pending")}
              className="bg-gradient-to-r from-primary to-primary text-primary-foreground hover:from-primary/90 hover:to-primary/80"
            >
              <FileUp className="mr-2 h-4 w-4" />
              Upload All
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          {/* Drop zone */}
          <div
            className={cn(
              "relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-colors",
              dragActive
                ? "border-primary bg-primary/5"
                : "border-border/40 hover:border-border/60",
            )}
            onDrop={handleDrop}
            onDragOver={(e) => {
              e.preventDefault()
              setDragActive(true)
            }}
            onDragLeave={() => setDragActive(false)}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              multiple
              className="hidden"
              onChange={(e) => e.target.files && handleFiles(e.target.files)}
            />
            <UploadCloud
              className={cn("mb-3 h-10 w-10", dragActive ? "text-primary" : "text-muted-foreground/50")}
            />
            <p className="text-sm font-medium">Drop PDFs here or click to browse</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Upload papers, proposals, reviews, and more
            </p>
          </div>

          {/* URL input */}
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <Input
                placeholder="Or paste a URL / DOI to import…"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
              />
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (urlInput.trim()) {
                  searchMutation.mutate(urlInput)
                  toast({ title: "Searching for paper…" })
                }
              }}
            >
              Fetch
            </Button>
          </div>

          {/* Document type selector */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Type:</span>
            {DOC_TYPES.map((dt) => (
              <button
                key={dt.value}
                onClick={() => setSelectedDocType(dt.value)}
                className={cn(
                  "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                  selectedDocType === dt.value
                    ? "bg-primary/10 text-primary"
                    : "bg-primary/10 text-muted-foreground hover:text-foreground",
                )}
              >
                {dt.icon} {dt.label}
              </button>
            ))}
          </div>

          {/* Upload queue */}
          {uploads.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">
                  Queue ({uploads.length})
                </span>
                {uploads.some((u) => u.status === "done" || u.status === "error") && (
                  <button onClick={clearCompleted} className="text-xs text-muted-foreground hover:text-foreground">
                    Clear completed
                  </button>
                )}
              </div>
              {uploads.map((item) => (
                <div key={item.id} className="flex items-center gap-3 rounded-lg border bg-muted/30 p-3">
                  <div className="shrink-0">
                    {item.status === "pending" && <FileText className="h-4 w-4 text-muted-foreground" />}
                    {item.status === "uploading" && (
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    )}
                    {item.status === "done" && <CheckCircle className="h-4 w-4 text-emerald-500" />}
                    {item.status === "error" && <AlertCircle className="h-4 w-4 text-red-500" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{item.file.name}</p>
                    <div className="mt-0.5 flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {(item.file.size / 1024 / 1024).toFixed(1)} MB
                      </span>
                      {item.status === "uploading" && (
                        <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted/30">
                          <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${item.progress}%` }}
                          />
                        </div>
                      )}
                      {item.status === "error" && <span className="text-xs text-red-500">{item.error}</span>}
                      {item.status === "done" && item.result && (
                        <span className="text-xs text-emerald-500">Uploaded</span>
                      )}
                    </div>
                  </div>
                  {item.status === "pending" && (
                    <button
                      onClick={() => removeUpload(item.id)}
                      className="shrink-0 text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </ModalShell>

      {/* ── Modal: Paper Detail ── */}
      <ModalShell
        open={detailModalOpen}
        onOpenChange={(open) => {
          setDetailModalOpen(open)
          if (!open) setSelectedPaperId(null)
        }}
        title={selectedPaper?.title || "Paper Details"}
        size="lg"
      >
        {selectedPaper && (
          <div className="space-y-5">
            {/* Authors + Year */}
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              {selectedPaper.authors && selectedPaper.authors.length > 0 && (
                <span className="inline-flex items-center gap-1">
                  <span>By</span>
                  <span className="font-medium text-foreground">
                    {selectedPaper.authors.slice(0, 3).join(", ")}
                    {selectedPaper.authors.length > 3 && " et al."}
                  </span>
                </span>
              )}
              {selectedPaper.year && (
                <span className="inline-flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  {selectedPaper.year}
                </span>
              )}
              {selectedPaper.venue && (
                <span className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs">
                  {selectedPaper.venue}
                </span>
              )}
            </div>

            {/* Scores */}
            {selectedPaper.analysis?.strengths_weaknesses?.quality_score && (
              <div>
                <h4 className="mb-3 text-sm font-semibold text-foreground">Quality Scores</h4>
                <ScoreDisplay
                  scores={extractScores(selectedPaper)!}
                  size="sm"
                />
              </div>
            )}

            {/* Abstract */}
            {selectedPaper.abstract && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-foreground">Abstract</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">{selectedPaper.abstract}</p>
              </div>
            )}

            {/* Analysis details */}
            {selectedPaper.analysis && (
              <>
                {selectedPaper.analysis.field_of_study && (
                  <div className="flex flex-wrap gap-2">
                    <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                      {selectedPaper.analysis.field_of_study}
                    </span>
                    {selectedPaper.analysis.subfield && (
                      <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                        {selectedPaper.analysis.subfield}
                      </span>
                    )}
                    {selectedPaper.analysis.scientific_areas?.map((area) => (
                      <span
                        key={area}
                        className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
                      >
                        {area}
                      </span>
                    ))}
                  </div>
                )}

                {/* Strengths & Weaknesses */}
                {selectedPaper.analysis.strengths_weaknesses && (
                  <div className="grid gap-4 sm:grid-cols-2">
                    {selectedPaper.analysis.strengths_weaknesses.strengths.length > 0 && (
                      <div>
                        <h4 className="mb-2 text-xs font-semibold text-emerald-500">Strengths</h4>
                        <ul className="space-y-1">
                          {selectedPaper.analysis.strengths_weaknesses.strengths.map((s, i) => (
                            <li key={i} className="text-xs text-muted-foreground">
                              {s.point}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {selectedPaper.analysis.strengths_weaknesses.weaknesses.length > 0 && (
                      <div>
                        <h4 className="mb-2 text-xs font-semibold text-amber-500">Weaknesses</h4>
                        <ul className="space-y-1">
                          {selectedPaper.analysis.strengths_weaknesses.weaknesses.map((w, i) => (
                            <li key={i} className="text-xs text-muted-foreground">
                              {w.point}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Tags */}
            {selectedPaper.tags.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-foreground">Tags</h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedPaper.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-muted-foreground"
                    >
                      <Tag className="mr-1 h-3 w-3" />
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata */}
            <div className="border-t border-border/30 pt-4">
              <h4 className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Metadata
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {selectedPaper.doi && (
                  <div>
                    <span className="text-muted-foreground">DOI:</span>{" "}
                    <span className="font-mono text-foreground">{selectedPaper.doi}</span>
                  </div>
                )}
                {selectedPaper.arxiv_id && (
                  <div>
                    <span className="text-muted-foreground">arXiv:</span>{" "}
                    <span className="font-mono text-foreground">{selectedPaper.arxiv_id}</span>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">Type:</span>{" "}
                  <span className="text-foreground capitalize">{selectedPaper.doc_type}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Created:</span>{" "}
                  <span className="text-foreground">
                    {new Date(selectedPaper.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </ModalShell>

      {/* ── Modal: Tag Manager ── */}
      <ModalShell
        open={tagModalOpen}
        onOpenChange={setTagModalOpen}
        title="Tag Manager"
        description="Browse, add, and remove tags across your paper library"
        size="lg"
      >
        <div className="space-y-5">
          {/* Select paper */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
              Select paper
            </label>
            <div className="flex flex-wrap gap-1.5">
              {mappedPapers.slice(0, 20).map((p) => (
                <button
                  key={p.id}
                  onClick={() => setTagTargetId(p.id)}
                  className={cn(
                    "truncate max-w-[200px] rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                    tagTargetId === p.id
                      ? "bg-primary/10 text-primary border border-primary/30"
                      : "bg-primary/10 text-muted-foreground hover:text-foreground border border-transparent",
                  )}
                >
                  {p.title}
                </button>
              ))}
              {mappedPapers.length > 20 && (
                <span className="inline-flex items-center text-xs text-muted-foreground px-1">
                  +{mappedPapers.length - 20} more
                </span>
              )}
            </div>
          </div>

          {/* Current tags */}
          {tagTargetId && (
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                Current tags
              </label>
              <div className="flex flex-wrap gap-1.5">
                {(() => {
                  const asset = assets.find((a) => a.id === tagTargetId)
                  if (!asset || asset.tags.length === 0)
                    return (
                      <span className="text-xs text-muted-foreground italic">
                        No tags — add one below
                      </span>
                    )
                  return asset.tags.map((tag) => (
                    <span
                      key={tag}
                      className="group/tag inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-muted-foreground"
                    >
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
                        className="ml-0.5 rounded-full p-0.5 text-muted-foreground opacity-0 transition-opacity hover:bg-red-500/20 hover:text-red-500 group-hover/tag:opacity-100"
                      >
                        <X className="h-2.5 w-2.5" />
                      </button>
                    </span>
                  ))
                })()}
              </div>
            </div>
          )}

          {/* Add tag */}
          <div className="flex items-center gap-2">
            <Input
              placeholder="New tag name…"
              value={newTagInput}
              onChange={(e) => setNewTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault()
                  handleAddTag()
                }
              }}
              className="flex-1"
            />
            <Button
              size="sm"
              onClick={handleAddTag}
              disabled={!newTagInput.trim() || !tagTargetId}
              className="bg-primary text-primary-foreground hover:bg-primary/90 shrink-0"
            >
              <Plus className="mr-1 h-3.5 w-3.5" />
              Add
            </Button>
          </div>

          {/* All tags in library */}
          {allTags.length > 0 && (
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                All tags in library
              </label>
              <div className="flex flex-wrap gap-1.5">
                {allTags.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => {
                      setTagFilter(tag === tagFilter ? null : tag)
                      setTagModalOpen(false)
                    }}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                      tagFilter === tag
                        ? "bg-primary text-primary-foreground"
                        : "bg-primary/10 text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {tag}
                    <span className="ml-0.5 text-[10px] opacity-70">({tagCounts[tag]})</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </ModalShell>

      {/* ── Modal: Settings ── */}
      <ModalShell
        open={settingsModalOpen}
        onOpenChange={setSettingsModalOpen}
        title="Source Settings"
        description="Configure your academic data sources and providers"
        size="md"
        footer={
          <Button variant="outline" onClick={() => setSettingsModalOpen(false)}>
            Close
          </Button>
        }
      >
        <div className="space-y-5">
          {/* Health status */}
          <div>
            <h4 className="mb-3 text-sm font-semibold text-foreground">Provider Status</h4>
            {providers.length > 0 ? (
              <HealthStatus providers={providers} variant="compact" />
            ) : (
              <p className="text-sm text-muted-foreground">No providers configured</p>
            )}
          </div>

          {/* Source list */}
          <div>
            <h4 className="mb-3 text-sm font-semibold text-foreground">Available Sources</h4>
            <div className="space-y-2">
              {SOURCE_OPTIONS.map((source) => {
                const Icon = source.icon
                return (
                  <div
                    key={source.value}
                    className="flex items-center justify-between rounded-lg border border-border/30 bg-card/40 px-4 py-3 backdrop-blur-xl"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                        <Icon className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground">{source.label}</p>
                        <p className="text-xs text-muted-foreground capitalize">{source.value}</p>
                      </div>
                    </div>
                    <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-500">
                      Available
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Navigate to full settings */}
          <div className="border-t border-border/30 pt-4">
            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                setSettingsModalOpen(false)
                navigate("/settings")
              }}
            >
              <SettingsIcon className="mr-2 h-4 w-4" />
              Open full settings
            </Button>
          </div>
        </div>
      </ModalShell>
    </div>
  )
}
