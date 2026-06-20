import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ChevronDown,
  Clock,
  Coins,
  Download,
  FileText,
  Loader2,
  MessageSquare,
  Square,
  Trash2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import {
  type WorkflowExecution,
  type WorkflowExecutionStage,
  type StageMeta,
  type ManuscriptRating,
  getStageMetaByIndex,
} from "@/constants/workflows";
import { PipelineBanner, type StageBlockData } from "./PipelineBanner";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import {
  formatDuration,
  getStatusConfig,
  executionStatusStyles,
} from "./workflow-helpers";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";

import { type StageUsage } from "@/constants/workflows";

function formatCost(usd: number): string {
  if (usd === 0) return "Free";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function computeTotals(stages: WorkflowExecutionStage[]) {
  let input = 0, output = 0, total = 0, cost = 0;
  for (const s of stages) {
    const u = s.metadata?.usage;
    if (u) {
      input += u.input_tokens || 0;
      output += u.output_tokens || 0;
      total += u.total_tokens || 0;
      cost += u.cost_usd || 0;
    }
  }
  return { input, output, total, cost };
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

/* ── StageDetail props & sub-component ──────────────────── */

interface StageDetailProps {
  stage: WorkflowExecutionStage;
  meta: StageMeta | null;
  index: number;
}

function StageDetail({ stage, meta, index }: StageDetailProps) {
  const [outputOpen, setOutputOpen] = useState(true);
  const hasOutput = stage.output?.trim().length > 0;
  const duration = stage.metadata?.duration_seconds
    ? formatDuration(stage.metadata.duration_seconds)
    : null;
  const cfg = getStatusConfig(stage.status);
  const StatusIcon = cfg.icon;
  const statusIconClass = cfg.iconClass;

  const usage: StageUsage | undefined = stage.metadata?.usage;

  return (
    <div className="animate-slide-in-from-top border rounded-lg p-4 bg-muted/15 space-y-3">
      {/* Detail header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          {meta?.icon && (
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center ${meta.color} text-white shrink-0`}
            >
              <span className="h-4 w-4">{meta.icon}</span>
            </div>
          )}
          <div className="min-w-0">
            <p className="text-sm font-semibold capitalize truncate">
              {stage.agent_name || stage.agent_role || `Step ${index + 1}`}
            </p>
            {stage.agent_role && (
              <p className="text-xs text-muted-foreground capitalize">
                {stage.agent_role}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {usage && usage.total_tokens > 0 && (
            <span className="text-xs text-muted-foreground tabular-nums flex items-center gap-1">
              <Coins className="h-3 w-3" />
              {formatTokens(usage.total_tokens)} tokens &middot; {formatCost(usage.cost_usd)}
            </span>
          )}
          {duration && (
            <span className="text-xs text-muted-foreground tabular-nums">
              {duration}
            </span>
          )}
          <Badge
            variant="outline"
            className={`text-[11px] px-2 py-0 font-medium ${cfg.badgeClass}`}
          >
            <StatusIcon className={`h-3 w-3 mr-1 ${statusIconClass}`} />
            {stage.status}
          </Badge>
        </div>
      </div>

      {/* Output */}
      {hasOutput && (
        <div>
          <button
            type="button"
            onClick={() => setOutputOpen(!outputOpen)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mb-1"
          >
            <ChevronDown
              className={`h-3 w-3 transition-transform duration-150 ${outputOpen ? "" : "-rotate-90"}`}
            />
            Output
          </button>
          {outputOpen && (
            <div className="rounded-md border bg-card p-4 text-sm leading-relaxed overflow-auto max-h-[500px]">
              <MarkdownRenderer content={stage.output} />
            </div>
          )}
        </div>
      )}

      {/* Metadata */}
      {stage.metadata &&
        Object.keys(stage.metadata).filter((k) => !["duration_seconds", "usage", "agent_role", "agent_name"].includes(k))
          .length > 0 && (
          <details className="group">
            <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors list-none flex items-center gap-1">
              <ChevronDown className="h-3 w-3 transition-transform group-open:rotate-0 -rotate-90" />
              Metadata
            </summary>
            <pre className="text-xs bg-muted rounded-md p-3 mt-2 overflow-auto max-h-[150px] leading-relaxed">
              {JSON.stringify(
                Object.fromEntries(
                  Object.entries(stage.metadata).filter(
                    ([k]) => !["duration_seconds", "usage", "agent_role", "agent_name"].includes(k)
                  )
                ),
                null,
                2
              )}
            </pre>
          </details>
        )}

      {!hasOutput && (
        <p className="text-xs text-muted-foreground italic">No output</p>
      )}
    </div>
  );
}

function getScoreColor(score: number): string {
  if (score >= 81) return "text-blue-600 bg-blue-50 border-blue-200";
  if (score >= 61) return "text-green-600 bg-green-50 border-green-200";
  if (score >= 41) return "text-yellow-600 bg-yellow-50 border-yellow-200";
  return "text-red-600 bg-red-50 border-red-200";
}

function getScoreBarColor(score: number): string {
  if (score >= 81) return "bg-blue-500";
  if (score >= 61) return "bg-green-500";
  if (score >= 41) return "bg-yellow-500";
  return "bg-red-500";
}

function getConfidenceBadge(confidence: string): string {
  switch (confidence) {
    case "high": return "bg-green-100 text-green-700 border-green-200";
    case "medium": return "bg-yellow-100 text-yellow-700 border-yellow-200";
    case "low": return "bg-red-100 text-red-700 border-red-200";
    default: return "bg-muted text-muted-foreground";
  }
}

function ManuscriptRatingCard({ rating }: { rating: ManuscriptRating }) {
  const [showRubric, setShowRubric] = useState(false);

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">Manuscript Rating</h4>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${getConfidenceBadge(rating.confidence)}`}>
            {rating.confidence} confidence
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground font-medium">
            {rating.rubric_standard}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className={`text-3xl font-bold px-4 py-2 rounded-lg border ${getScoreColor(rating.overall_score)}`}>
          {rating.overall_score}
        </div>
        <div className="flex-1">
          <div className="text-xs text-muted-foreground mb-1">out of 100</div>
          {rating.confidence_reason && (
            <div className="text-xs text-muted-foreground italic">{rating.confidence_reason}</div>
          )}
        </div>
      </div>

      {rating.criteria.length > 0 && (
        <>
          <button
            type="button"
            onClick={() => setShowRubric(!showRubric)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
          >
            <ChevronDown className={`h-3 w-3 transition-transform ${showRubric ? "rotate-0" : "-rotate-90"}`} />
            {showRubric ? "Hide" : "Show"} rubric breakdown
          </button>

          {showRubric && (
            <div className="space-y-2 pt-2">
              {rating.criteria.map((c) => (
                <div key={c.name} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium">{c.name}</span>
                    <span className="text-muted-foreground">{c.score}/100 ({Math.round(c.weight * 100)}%)</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${getScoreBarColor(c.score)}`}
                      style={{ width: `${c.score}%` }}
                    />
                  </div>
                  {c.justification && (
                    <div className="text-[11px] text-muted-foreground italic pl-1">{c.justification}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {rating.scoring_notes && (
        <div className="text-xs text-muted-foreground pt-2 border-t italic">{rating.scoring_notes}</div>
      )}
    </div>
  );
}

/* ── main card ──────────────────────────────────────────── */

interface ExecutionResultCardProps {
  execution: WorkflowExecution;
  onDelete?: (id: string) => void;
}

export function ExecutionResultCard({
  execution,
  onDelete,
}: ExecutionResultCardProps) {
  const isRunning = execution.status === "running" || execution.status === "pending" || execution.status === "cancelling";
  const [collapsed, setCollapsed] = useState(!isRunning);
  const [selectedStage, setSelectedStage] = useState<number | null>(null);
  const [downloading, setDownloading] = useState<"pdf" | "markdown" | null>(
    null
  );
  const [creatingRevision, setCreatingRevision] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const handleDownload = async (format: "pdf" | "markdown") => {
    setDownloading(format);
    try {
      const response = await api.get(
        `/workflows/results/${execution.id}/export/${format}`,
        { responseType: "blob" }
      );
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const ext = format === "pdf" ? "pdf" : "md";
      link.download = `${execution.workflow_name.toLowerCase().replace(/\s+/g, "_")}_${execution.id}.${ext}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        (format === "pdf"
          ? "PDF export failed. Please try again."
          : "Markdown export failed. Please try again.");
      toast({
        title: `Export failed (${format.toUpperCase()})`,
        description: detail,
        variant: "destructive",
      });
    } finally {
      setDownloading(null);
    }
  };

  const handleCreateRevision = async () => {
    setCreatingRevision(true);
    try {
      const response = await api.post("/revisions/sessions", {
        workflow_execution_id: execution.id,
      });
      navigate(`/revisions/${response.data.id}`);
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail || "Failed to create revision session.";
      toast({
        title: "Revision failed",
        description: detail,
        variant: "destructive",
      });
    } finally {
      setCreatingRevision(false);
    }
  };

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await api.post(`/workflows/cancel/${execution.id}`);
      queryClient.invalidateQueries({ queryKey: ["workflow-results"] });
      toast({ title: "Workflow cancelling", description: "The workflow is being stopped." });
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail || "Failed to cancel workflow.";
      toast({
        title: "Cancel failed",
        description: detail,
        variant: "destructive",
      });
    } finally {
      setCancelling(false);
    }
  };

  const stageBlocks: StageBlockData[] = execution.stages.map((stage, i) => ({
    index: i,
    agentName: stage.agent_name || stage.agent_role || `Step ${i + 1}`,
    agentRole: stage.agent_role || "",
    status: stage.status,
    duration: stage.metadata?.duration_seconds,
  }));

  const totals = computeTotals(execution.stages);

  const statusStyle =
    executionStatusStyles[execution.status] ||
    "bg-muted text-muted-foreground border-border";

  return (
    <Card className="overflow-hidden transition-all duration-200 hover:shadow-md">
      <CardContent className="p-5 space-y-4">
        {/* ── Clickable Summary Header ── */}
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-start justify-between gap-4 w-full text-left group"
        >
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base font-semibold">
                {execution.workflow_name}
              </h3>
              <Badge
                variant="outline"
                className={`text-[11px] px-2 py-0 font-medium ${statusStyle}`}
              >
                {execution.status}
              </Badge>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatTime(execution.created_at)}
              </span>
              {execution.duration_seconds && (
                <span className="tabular-nums">
                  {formatDuration(execution.duration_seconds)}
                </span>
              )}
              {totals.total > 0 && (
                <span className="tabular-nums flex items-center gap-1">
                  <Coins className="h-3 w-3" />
                  {formatTokens(totals.total)} tokens &middot; {formatCost(totals.cost)}
                </span>
              )}
            </div>
            {execution.input_text && (
              <p className="text-xs text-muted-foreground/70 mt-1.5 truncate max-w-xl italic">
                &ldquo;
                {execution.input_text.substring(0, 120)}
                {execution.input_text.length > 120 ? "..." : ""}&rdquo;
              </p>
            )}
          </div>
          <ChevronDown
            className={`h-5 w-5 mt-1 shrink-0 text-muted-foreground transition-transform duration-200 ${
              collapsed ? "" : "rotate-180"
            }`}
          />
        </button>

        {!collapsed && (
          <>
            {/* ── Pipeline Visualization ── */}
            <PipelineBanner
              stages={stageBlocks}
              workflowId={execution.workflow_id}
              selectedIndex={selectedStage}
              onStageClick={(index) =>
                setSelectedStage(selectedStage === index ? null : index)
              }
            />

            {/* ── Manuscript Rating ── */}
            {execution.stages.some((s) => s.rating && s.rating.overall_score > 0) && (
              <ManuscriptRatingCard
                rating={
                  execution.stages.find((s) => s.rating && s.rating.overall_score > 0)?.rating!
                }
              />
            )}

            {/* ── Stage Detail Panel ── */}
            {selectedStage !== null && execution.stages[selectedStage] && (
              <StageDetail
                stage={execution.stages[selectedStage]}
                meta={getStageMetaByIndex(execution.workflow_id, selectedStage)}
                index={selectedStage}
              />
            )}

            {/* ── Action Bar ── */}
            <div className="flex items-center justify-between pt-3 border-t">
              <div className="flex items-center gap-1">
                {!isRunning && (
                  <>
                    <span className="text-xs text-muted-foreground mr-1 font-medium">
                      Export
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs gap-1.5 px-2"
                      disabled={downloading === "markdown"}
                      onClick={() => handleDownload("markdown")}
                    >
                      {downloading === "markdown" ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Download className="h-3.5 w-3.5" />
                      )}
                      Markdown
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs gap-1.5 px-2"
                      disabled={downloading === "pdf"}
                      onClick={() => handleDownload("pdf")}
                    >
                      {downloading === "pdf" ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <FileText className="h-3.5 w-3.5" />
                      )}
                      PDF
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs gap-1.5 px-2"
                      disabled={creatingRevision}
                      onClick={handleCreateRevision}
                    >
                      {creatingRevision ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <MessageSquare className="h-3.5 w-3.5" />
                      )}
                      Discuss Review
                    </Button>
                  </>
                )}
              </div>
              <div className="flex items-center gap-1">
                {isRunning && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs gap-1.5 px-2 text-destructive hover:text-destructive hover:bg-destructive/10"
                    disabled={cancelling}
                    onClick={handleCancel}
                  >
                    {cancelling ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Square className="h-3.5 w-3.5" />
                    )}
                    Cancel
                  </Button>
                )}
                {onDelete && !isRunning && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs gap-1.5 px-2 text-destructive hover:text-destructive hover:bg-destructive/10"
                    onClick={() => onDelete(execution.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </Button>
                )}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
