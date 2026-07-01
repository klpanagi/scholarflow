import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { LoadingState } from "@/components/shared/LoadingState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { PaperOutline } from "@/components/papers/PaperOutline"
import { PaperReferences } from "@/components/papers/PaperReferences"
import { ScoreDisplay } from "@/components/shared/ScoreDisplay"
import {
  BookOpen,
  BookMarked,
  BarChart3,
  ArrowLeft,
  Calendar,
  FileText,
  Globe,
  Tag,
  AlertCircle,
  CheckCircle2,
  Clock,
} from "lucide-react"

// ── Types ──────────────────────────────────────────────────────────────

interface PaperAsset {
  id: string
  title: string
  authors: string[]
  abstract: string
  year: number | null
  venue: string | null
  doi: string | null
  arxiv_id: string | null
  tags: string[]
  doc_type: string
  processing_status: string
  analysis: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

interface ExtractionMeta {
  source?: string
  sections?: { heading?: string; text?: string }[]
  references?: { raw_text?: string; title?: string; authors?: string; year?: string | number; doi?: string }[]
  page_count?: number
  extraction_time?: number
  doc_type?: string
}

// ── Helpers ────────────────────────────────────────────────────────────

function extractScores(paper: PaperAsset) {
  const sw = (paper.analysis as any)?.strengths_weaknesses
  if (!sw) return null
  return {
    quality: sw.quality_score,
    novelty: sw.novelty_score,
    rigor: sw.rigor_score,
    clarity: sw.clarity_score,
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case "completed":
      return (
        <Badge variant="outline" className="gap-1 border-emerald-500/30 text-emerald-500">
          <CheckCircle2 className="h-3 w-3" />
          Completed
        </Badge>
      )
    case "pending":
      return (
        <Badge variant="outline" className="gap-1 border-amber-500/30 text-amber-500">
          <Clock className="h-3 w-3" />
          Pending
        </Badge>
      )
    case "failed":
      return (
        <Badge variant="outline" className="gap-1 border-red-500/30 text-red-500">
          <AlertCircle className="h-3 w-3" />
          Failed
        </Badge>
      )
    default:
      return (
        <Badge variant="outline" className="gap-1">
          <Clock className="h-3 w-3" />
          {status}
        </Badge>
      )
  }
}

function getExtractionMethodBadge(source?: string) {
  if (!source) return null
  const colors: Record<string, string> = {
    grobid: "bg-violet-500/10 text-violet-500 border-violet-500/30",
    pymupdf: "bg-blue-500/10 text-blue-500 border-blue-500/30",
    tika: "bg-orange-500/10 text-orange-500 border-orange-500/30",
  }
  return (
    <Badge variant="outline" className={`gap-1 ${colors[source] || ""}`}>
      <FileText className="h-3 w-3" />
      {source}
    </Badge>
  )
}

type TabId = "outline" | "references" | "analysis"

const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "outline", label: "Outline", icon: BookOpen },
  { id: "references", label: "References", icon: BookMarked },
  { id: "analysis", label: "Analysis", icon: BarChart3 },
]

// ── Page ───────────────────────────────────────────────────────────────

export default function PaperDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabId>("outline")

  const { data: paper, isLoading, isError } = useQuery<PaperAsset>({
    queryKey: ["asset", id],
    queryFn: async () => {
      const { data } = await api.get(`/assets/${id}`)
      return data
    },
    enabled: !!id,
  })

  // Scroll to top on mount
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  // ── Loading / Error ──────────────────────────────────────────────

  if (isLoading) {
    return <LoadingState label="Loading paper details…" size="lg" className="py-24" />
  }

  if (isError || !paper) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24">
        <AlertCircle className="h-10 w-10 text-destructive" />
        <p className="text-sm text-muted-foreground">Could not load paper details.</p>
        <Button variant="outline" onClick={() => navigate("/assets")}>
          Back to Assets
        </Button>
      </div>
    )
  }

  const extractionMeta: ExtractionMeta | undefined = (paper.analysis as any)?.extraction_meta
  const scores = extractScores(paper)

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-6">
      {/* ── Back button ── */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate("/assets")}
        className="gap-1.5 text-muted-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Assets
      </Button>

      {/* ── Header ── */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1 space-y-2">
            <h1 className="text-2xl font-bold leading-tight tracking-tight">{paper.title}</h1>

            {/* Authors + Year + Venue */}
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              {paper.authors && paper.authors.length > 0 && (
                <span>
                  {paper.authors.slice(0, 5).join(", ")}
                  {paper.authors.length > 5 && " et al."}
                </span>
              )}
              {paper.year && (
                <span className="inline-flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  {paper.year}
                </span>
              )}
              {paper.venue && (
                <span className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs">
                  <Globe className="h-3 w-3" />
                  {paper.venue}
                </span>
              )}
            </div>
          </div>

          {/* Status + extraction badges */}
          <div className="flex shrink-0 flex-wrap gap-2">
            {getStatusBadge(paper.processing_status)}
            {getExtractionMethodBadge(extractionMeta?.source)}
          </div>
        </div>

        {/* Extraction meta summary */}
        {extractionMeta && (
          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            {extractionMeta.sections && (
              <span className="inline-flex items-center gap-1">
                <BookOpen className="h-3.5 w-3.5" />
                {extractionMeta.sections.length} sections
              </span>
            )}
            {extractionMeta.references && (
              <span className="inline-flex items-center gap-1">
                <BookMarked className="h-3.5 w-3.5" />
                {extractionMeta.references.length} references
              </span>
            )}
            {extractionMeta.page_count && (
              <span className="inline-flex items-center gap-1">
                <FileText className="h-3.5 w-3.5" />
                {extractionMeta.page_count} pages
              </span>
            )}
          </div>
        )}

        {/* Abstract */}
        {paper.abstract && (
          <div className="rounded-lg border border-border/40 bg-muted/20 p-4">
            <p className="text-sm leading-relaxed text-muted-foreground">{paper.abstract}</p>
          </div>
        )}
      </div>

      {/* ── Tabs ── */}
      <div className="border-b border-border/40">
        <nav className="flex gap-6">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Tab content ── */}
      <div>
        {activeTab === "outline" && (
          <PaperOutline sections={extractionMeta?.sections || []} />
        )}

        {activeTab === "references" && (
          <PaperReferences references={extractionMeta?.references || []} />
        )}

        {activeTab === "analysis" && (
          <div className="space-y-6">
            {/* Scores */}
            {scores ? (
              <div>
                <h3 className="mb-3 text-sm font-semibold text-foreground">Quality Scores</h3>
                <ScoreDisplay scores={scores} size="md" />
              </div>
            ) : (
              <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
                No analysis data available. The paper may not have been analyzed yet.
              </div>
            )}

            {/* Tags */}
            {paper.tags && paper.tags.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-foreground">Tags</h3>
                <div className="flex flex-wrap gap-1.5">
                  {paper.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-muted-foreground"
                    >
                      <Tag className="h-3 w-3" />
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Strengths & Weaknesses */}
            {(() => {
              const sw = (paper.analysis as any)?.strengths_weaknesses
              if (!sw) return null
              return (
                <div className="grid gap-4 sm:grid-cols-2">
                  {sw.strengths?.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-xs font-semibold text-emerald-500">Strengths</h4>
                      <ul className="space-y-1">
                        {sw.strengths.map((s: any, i: number) => (
                          <li key={i} className="text-xs text-muted-foreground">{s.point}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {sw.weaknesses?.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-xs font-semibold text-amber-500">Weaknesses</h4>
                      <ul className="space-y-1">
                        {sw.weaknesses.map((w: any, i: number) => (
                          <li key={i} className="text-xs text-muted-foreground">{w.point}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )
            })()}

            {/* DOI / arXiv */}
            {(paper.doi || paper.arxiv_id) && (
              <div className="space-y-1 border-t border-border/30 pt-4">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Identifiers
                </h3>
                <div className="flex flex-wrap gap-4 text-xs">
                  {paper.doi && (
                    <span>
                      <span className="text-muted-foreground">DOI:</span>{" "}
                      <code className="text-foreground">{paper.doi}</code>
                    </span>
                  )}
                  {paper.arxiv_id && (
                    <span>
                      <span className="text-muted-foreground">arXiv:</span>{" "}
                      <code className="text-foreground">{paper.arxiv_id}</code>
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
