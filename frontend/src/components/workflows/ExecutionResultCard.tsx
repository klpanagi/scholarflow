import { useState } from "react";
import {
  ChevronDown,
  Clock,
  Download,
  FileText,
  Loader2,
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
  getStageMetaByIndex,
} from "@/constants/workflows";
import { PipelineBanner, type StageBlockData } from "./PipelineBanner";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import {
  formatDuration,
  getStatusConfig,
  executionStatusStyles,
} from "./workflow-helpers";

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
        Object.keys(stage.metadata).filter((k) => k !== "duration_seconds")
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
                    ([k]) => k !== "duration_seconds"
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

/* ── main card ──────────────────────────────────────────── */

interface ExecutionResultCardProps {
  execution: WorkflowExecution;
  onDelete?: (id: string) => void;
}

export function ExecutionResultCard({
  execution,
  onDelete,
}: ExecutionResultCardProps) {
  const [selectedStage, setSelectedStage] = useState<number | null>(null);
  const [downloading, setDownloading] = useState<"pdf" | "markdown" | null>(
    null
  );

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
    } catch {
      //
    } finally {
      setDownloading(null);
    }
  };

  const stageBlocks: StageBlockData[] = execution.stages.map((stage, i) => ({
    index: i,
    agentName: stage.agent_name || stage.agent_role || `Step ${i + 1}`,
    agentRole: stage.agent_role || "",
    status: stage.status,
    duration: stage.metadata?.duration_seconds,
  }));

  const statusStyle =
    executionStatusStyles[execution.status] ||
    "bg-muted text-muted-foreground border-border";

  return (
    <Card className="overflow-hidden transition-all duration-200 hover:shadow-md">
      <CardContent className="p-5 space-y-4">
        {/* ── Summary Header ── */}
        <div className="flex items-start justify-between gap-4">
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
            </div>
            {execution.input_text && (
              <p className="text-xs text-muted-foreground/70 mt-1.5 truncate max-w-xl italic">
                &ldquo;
                {execution.input_text.substring(0, 120)}
                {execution.input_text.length > 120 ? "..." : ""}&rdquo;
              </p>
            )}
          </div>
        </div>

        {/* ── Pipeline Visualization ── */}
        <PipelineBanner
          stages={stageBlocks}
          workflowId={execution.workflow_id}
          selectedIndex={selectedStage}
          onStageClick={(index) =>
            setSelectedStage(selectedStage === index ? null : index)
          }
        />

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
          </div>
          {onDelete && (
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
      </CardContent>
    </Card>
  );
}
