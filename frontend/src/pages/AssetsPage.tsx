import { useState, useCallback, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import { Search, Upload, FileText, Trash2, X, CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronUp, Sparkles, Tag, BarChart3, FileUp, UploadCloud } from "lucide-react"

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

const DOC_TYPES = [
  { value: "paper", label: "Research Paper", icon: "📄" },
  { value: "proposal", label: "Grant Proposal", icon: "📋" },
  { value: "review", label: "Literature Review", icon: "📚" },
  { value: "report", label: "Technical Report", icon: "📊" },
  { value: "other", label: "Other", icon: "📎" },
]

export default function AssetsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get("tab") || "library"
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<Asset[]>([])
  const [uploads, setUploads] = useState<UploadItem[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [selectedDocType, setSelectedDocType] = useState("paper")
  const [expandedAsset, setExpandedAsset] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState<string | null>(null)

  const { data: assets = [] } = useQuery<Asset[]>({
    queryKey: ["assets"],
    queryFn: async () => {
      const { data } = await api.get("/assets")
      return data.items || []
    },
  })

  const searchMutation = useMutation({
    mutationFn: async (query: string) => {
      const { data } = await api.get(`/assets/search?q=${encodeURIComponent(query)}`)
      return data
    },
    onSuccess: (data) => setSearchResults(data),
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

  const handleFiles = useCallback((files: FileList | File[]) => {
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
  }, [toast])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const removeUpload = (id: string) => setUploads((prev) => prev.filter((u) => u.id !== id))

  const startUpload = async () => {
    const pending = uploads.filter((u) => u.status === "pending")
    if (pending.length === 0) return

    for (const item of pending) {
      setUploads((prev) => prev.map((u) => u.id === item.id ? { ...u, status: "uploading", progress: 10 } : u))

      try {
        const formData = new FormData()
        formData.append("file", item.file)
        formData.append("doc_type", selectedDocType)

        const { data } = await api.post("/assets/", formData, {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (e) => {
            const pct = Math.round((e.loaded * 100) / (e.total || 1))
            setUploads((prev) => prev.map((u) => u.id === item.id ? { ...u, progress: Math.min(pct, 90) } : u))
          },
        })

        setUploads((prev) => prev.map((u) => u.id === item.id ? { ...u, status: "done", progress: 100, result: data } : u))
      } catch (error: any) {
        setUploads((prev) => prev.map((u) => u.id === item.id ? { ...u, status: "error", error: error.response?.data?.detail || "Upload failed" } : u))
      }
    }

    queryClient.invalidateQueries({ queryKey: ["assets"] })
    toast({ title: `Uploaded ${pending.length} file(s)` })
  }

  const clearCompleted = () => setUploads((prev) => prev.filter((u) => u.status !== "done" && u.status !== "error"))

  const getDocTypeBadge = (docType: string) => {
    const dt = DOC_TYPES.find((d) => d.value === docType)
    return dt ? `${dt.icon} ${dt.label}` : docType
  }

  const renderAnalysis = (asset: Asset) => {
    if (!asset.analysis) {
      return (
        <div className="mt-4 border-t pt-4">
          <p className="text-sm text-muted-foreground">No analysis available. Click the sparkle button to analyze this asset.</p>
        </div>
      )
    }

    const a = asset.analysis
    const sw = a.strengths_weaknesses
    const hasStrengths = sw && sw.strengths && sw.strengths.length > 0
    const hasWeaknesses = sw && sw.weaknesses && sw.weaknesses.length > 0
    const hasSW = hasStrengths || hasWeaknesses

    return (
      <div className="mt-4 space-y-4 border-t pt-4">
        {a.summary && (
          <div>
            <h4 className="text-sm font-semibold mb-1 flex items-center gap-1"><Sparkles className="h-3 w-3" /> Summary</h4>
            <p className="text-sm text-muted-foreground">{a.summary}</p>
          </div>
        )}

        {a.methodology && (
          <div>
            <h4 className="text-sm font-semibold mb-1">Methodology</h4>
            <p className="text-sm text-muted-foreground">{a.methodology}</p>
          </div>
        )}

        {a.key_findings && a.key_findings.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-1">Key Findings</h4>
            <ul className="text-sm text-muted-foreground list-disc pl-4 space-y-1">
              {a.key_findings.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        )}

        {a.contributions && a.contributions.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-1">Contributions</h4>
            <ul className="text-sm text-muted-foreground list-disc pl-4 space-y-1">
              {a.contributions.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          </div>
        )}

        {a.limitations && a.limitations.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-1">Limitations</h4>
            <ul className="text-sm text-muted-foreground list-disc pl-4 space-y-1">
              {a.limitations.map((l, i) => <li key={i}>{l}</li>)}
            </ul>
          </div>
        )}

        {a.auto_tags && a.auto_tags.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-1 flex items-center gap-1"><Tag className="h-3 w-3" /> Auto Tags</h4>
            <div className="flex flex-wrap gap-1">
              {a.auto_tags.map((t, i) => <Badge key={i} variant="secondary" className="text-xs">{t}</Badge>)}
            </div>
          </div>
        )}

        {a.keywords && a.keywords.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-1">Keywords</h4>
            <div className="flex flex-wrap gap-1">
              {a.keywords.map((k, i) => <Badge key={i} variant="outline" className="text-xs">{k}</Badge>)}
            </div>
          </div>
        )}

        {(a.scientific_areas && a.scientific_areas.length > 0 || a.field_of_study) && (
          <div>
            <h4 className="text-sm font-semibold mb-1">Scientific Areas</h4>
            <div className="flex flex-wrap gap-1">
              {a.field_of_study && <Badge key="fos" variant="default" className="text-xs">{a.field_of_study}</Badge>}
              {a.subfield && <Badge key="sub" variant="default" className="text-xs">{a.subfield}</Badge>}
              {a.scientific_areas?.map((s, i) => <Badge key={i} variant="secondary" className="text-xs">{s}</Badge>)}
            </div>
          </div>
        )}

        {sw && (sw.quality_score > 0 || hasSW) && (
          <div>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-1"><BarChart3 className="h-3 w-3" /> Critical Analysis</h4>
            {sw.quality_score > 0 && (
              <div className="mb-3 flex items-center gap-2">
                <span className="text-2xl font-bold">{sw.quality_score}/10</span>
                {sw.quality_rationale && sw.quality_rationale !== "Analysis failed" && (
                  <span className="text-xs text-muted-foreground">{sw.quality_rationale}</span>
                )}
              </div>
            )}
            {hasSW ? (
              <div className="grid grid-cols-2 gap-4">
                {hasStrengths && (
                  <div>
                    <h5 className="text-xs font-medium text-green-600 mb-1">Strengths</h5>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      {sw.strengths.map((s, i) => (
                        <li key={i} className="flex gap-1"><CheckCircle className="h-3 w-3 text-green-500 shrink-0 mt-0.5" /><span>{s.point}</span></li>
                      ))}
                    </ul>
                  </div>
                )}
                {hasWeaknesses && (
                  <div>
                    <h5 className="text-xs font-medium text-red-600 mb-1">Weaknesses</h5>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      {sw.weaknesses.map((w, i) => (
                        <li key={i} className="flex gap-1"><AlertCircle className="h-3 w-3 text-red-500 shrink-0 mt-0.5" /><span>{w.point}</span></li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Strength/weakness analysis did not produce results. Click the sparkle button to retry.</p>
            )}
            {sw.suggestions && sw.suggestions.length > 0 && (
              <div className="mt-3">
                <h5 className="text-xs font-medium mb-1">Suggestions</h5>
                <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-1">
                  {sw.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Assets</h1>
        <div className="flex gap-2">
          <Button variant={activeTab === "library" ? "default" : "outline"} size="sm" onClick={() => setSearchParams({ tab: "library" })}>
            <FileText className="mr-2 h-4 w-4" /> Library
          </Button>
          <Button variant={activeTab === "upload" ? "default" : "outline"} size="sm" onClick={() => setSearchParams({ tab: "upload" })}>
            <Upload className="mr-2 h-4 w-4" /> Upload
          </Button>
          <Button variant={activeTab === "search" ? "default" : "outline"} size="sm" onClick={() => setSearchParams({ tab: "search" })}>
            <Search className="mr-2 h-4 w-4" /> Search
          </Button>
        </div>
      </div>

      {activeTab === "upload" && (
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-6">
              <div
                className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer ${
                  dragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-muted-foreground/50"
                }`}
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
                onDragLeave={(e) => { e.preventDefault(); setDragActive(false) }}
                onClick={() => fileInputRef.current?.click()}
              >
                <input ref={fileInputRef} type="file" accept=".pdf" multiple className="hidden" onChange={(e) => e.target.files && handleFiles(e.target.files)} />
                <UploadCloud className={`mx-auto h-12 w-12 mb-4 ${dragActive ? "text-primary" : "text-muted-foreground/50"}`} />
                <p className="text-lg font-medium">Drop PDFs here or click to browse</p>
                <p className="text-sm text-muted-foreground mt-1">Upload papers, proposals, reviews, deliverables, and more</p>
              </div>
            </CardContent>
          </Card>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium">Document type:</span>
            {DOC_TYPES.map((dt) => (
              <Button key={dt.value} variant={selectedDocType === dt.value ? "default" : "outline"} size="sm" onClick={() => setSelectedDocType(dt.value)}>
                {dt.icon} {dt.label}
              </Button>
            ))}
          </div>

          {uploads.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Upload Queue ({uploads.length})</CardTitle>
                  <div className="flex gap-2">
                    {uploads.some((u) => u.status === "done" || u.status === "error") && (
                      <Button variant="ghost" size="sm" onClick={clearCompleted}>Clear completed</Button>
                    )}
                    <Button size="sm" onClick={startUpload} disabled={!uploads.some((u) => u.status === "pending")}>
                      <FileUp className="mr-2 h-4 w-4" /> Upload All
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {uploads.map((item) => (
                  <div key={item.id} className="flex items-center gap-3 p-3 rounded-lg border bg-muted/30">
                    <div className="shrink-0">
                      {item.status === "pending" && <FileText className="h-5 w-5 text-muted-foreground" />}
                      {item.status === "uploading" && <Loader2 className="h-5 w-5 text-primary animate-spin" />}
                      {item.status === "done" && <CheckCircle className="h-5 w-5 text-green-500" />}
                      {item.status === "error" && <AlertCircle className="h-5 w-5 text-red-500" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{item.file.name}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-muted-foreground">{(item.file.size / 1024 / 1024).toFixed(1)} MB</span>
                        {item.status === "uploading" && (
                          <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${item.progress}%` }} />
                          </div>
                        )}
                        {item.status === "error" && <span className="text-xs text-red-500">{item.error}</span>}
                        {item.status === "done" && item.result && <span className="text-xs text-green-600">Uploaded &quot;{item.result.title}&quot;</span>}
                      </div>
                    </div>
                    {item.status === "pending" && (
                      <Button variant="ghost" size="sm" onClick={() => removeUpload(item.id)}><X className="h-4 w-4" /></Button>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {activeTab === "search" && (
        <div className="space-y-4">
          <form onSubmit={(e) => { e.preventDefault(); searchQuery.trim() && searchMutation.mutate(searchQuery) }} className="flex gap-2">
            <Input placeholder="Search assets by content, title, or topic..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="flex-1" />
            <Button type="submit" disabled={searchMutation.isPending}>
              {searchMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            </Button>
          </form>
          <div className="grid gap-3">
            {searchResults.map((asset: any) => (
              <Card key={asset.id || asset.asset_id}>
                <CardContent className="pt-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-medium">{asset.title || "Untitled"}</h3>
                      <p className="text-sm text-muted-foreground mt-1">{asset.content?.substring(0, 200)}...</p>
                    </div>
                    {asset.score && <Badge variant="outline">{(asset.score * 100).toFixed(0)}% match</Badge>}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {activeTab === "library" && (
        <div className="grid gap-3">
          {assets.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <FileUp className="mx-auto h-12 w-12 text-muted-foreground/30 mb-4" />
                <p className="text-muted-foreground">No assets yet. Upload some PDFs to get started.</p>
                <Button className="mt-4" onClick={() => setSearchParams({ tab: "upload" })}><Upload className="mr-2 h-4 w-4" /> Upload Assets</Button>
              </CardContent>
            </Card>
          ) : (
            assets.map((asset) => (
              <Card key={asset.id}>
                <CardContent className="pt-4">
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-medium">{asset.title}</h3>
                        <Badge variant="secondary" className="text-xs">{getDocTypeBadge(asset.doc_type)}</Badge>
                      </div>
                      {asset.authors && asset.authors.length > 0 && (
                        <p className="text-sm text-muted-foreground mt-1">{asset.authors.join(", ")}</p>
                      )}
                      <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                        {asset.year && <span className="text-xs text-muted-foreground">{asset.year}</span>}
                        {asset.venue && <span className="text-xs text-muted-foreground">{asset.venue}</span>}
                        {asset.doi && <span className="text-xs text-muted-foreground">DOI: {asset.doi}</span>}
                        {asset.arxiv_id && <span className="text-xs text-muted-foreground">arXiv: {asset.arxiv_id}</span>}
                        {asset.analysis?.references && asset.analysis.references.length > 0 && <span className="text-xs text-muted-foreground">{asset.analysis.references.length} refs</span>}
                      </div>
                      {asset.abstract && <p className="text-sm text-muted-foreground mt-2 line-clamp-3">{asset.abstract}</p>}
                      {asset.tags && asset.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {asset.tags.map((tag, i) => <Badge key={i} variant="outline" className="text-xs">{tag}</Badge>)}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button variant="ghost" size="sm" onClick={() => setExpandedAsset(expandedAsset === asset.id ? null : asset.id)}>
                        {expandedAsset === asset.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => { setAnalyzing(asset.id); analyzeMutation.mutate(asset.id) }} disabled={analyzing === asset.id} title={asset.analysis ? "Re-analyze asset" : "Analyze asset"}>
                        {analyzing === asset.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => deleteMutation.mutate(asset.id)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                    </div>
                  </div>
                  {expandedAsset === asset.id && renderAnalysis(asset)}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  )
}
