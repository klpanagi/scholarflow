import { useState } from "react";
import { ChevronDown, Clock, AlertTriangle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import {
  type TimelineStage,
  type WorkflowExecutionStage,
} from "@/constants/workflows";
import {
  formatDuration,
  getStatusConfig,
} from "./workflow-helpers";
import NodeItem from "./NodeItem";

interface StageTimelineProps {
  stage: TimelineStage;
  sourceStage?: WorkflowExecutionStage;
}

function formatMs(durationMs: number | undefined): string | null {
  if (durationMs === undefined) return null;
  if (durationMs < 1000) return `${durationMs}ms`;
  return formatDuration(durationMs / 1000);
}

function StageTimeline({ stage, sourceStage }: StageTimelineProps) {
  const [outputOpen, setOutputOpen] = useState(true);
  const cfg = getStatusConfig(stage.status);
  const StatusIcon = cfg.icon;
  const showSpinner = StatusIcon === Loader2;

  const durationLabel = formatMs(stage.durationMs);
  const stageOutput = sourceStage?.output ?? "";
  const hasOutput = stageOutput.trim().length > 0;

  return (
    <Card
      data-testid={`stage-timeline-${stage.stageIndex}`}
      className="border bg-muted/15 animate-slide-in-from-top"
    >
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-semibold truncate" data-testid="stage-timeline-name">
              {stage.agentName || stage.agentRole || `Step ${stage.stageIndex + 1}`}
            </p>
            {stage.agentRole && (
              <p className="text-xs text-muted-foreground capitalize">
                {stage.agentRole}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {stage.strategyIterations > 0 && (
              <Badge
                variant="outline"
                data-testid="stage-timeline-strategy-badge"
                className="text-[11px] px-2 py-0 font-medium"
              >
                {stage.strategyIterations} iteration{stage.strategyIterations === 1 ? "" : "s"}
              </Badge>
            )}
            {durationLabel && (
              <span className="text-xs text-muted-foreground tabular-nums flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {durationLabel}
              </span>
            )}
            <Badge
              variant="outline"
              className={`text-[11px] px-2 py-0 font-medium ${cfg.badgeClass}`}
            >
              <StatusIcon
                className={`h-3 w-3 mr-1 ${cfg.iconClass} ${
                  showSpinner ? "animate-spin" : ""
                }`}
              />
              {cfg.label}
            </Badge>
          </div>
        </div>

        {stage.error && (
          <div
            data-testid="stage-timeline-error"
            className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900 px-3 py-2 text-xs text-red-700 dark:text-red-300"
          >
            <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            <span className="break-words">{stage.error}</span>
          </div>
        )}

        {stage.nodes.length > 0 && (
          <div
            data-testid="stage-timeline-nodes"
            className="relative pl-3 space-y-0.5"
          >
            <span
              className="absolute left-1.5 top-1.5 bottom-1.5 w-px bg-border"
              aria-hidden="true"
            />
            {stage.nodes.map((node) => (
              <NodeItem key={node.id} node={node} />
            ))}
          </div>
        )}

        {hasOutput ? (
          <div>
            <button
              type="button"
              onClick={() => setOutputOpen(!outputOpen)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mb-1"
            >
              <ChevronDown
                className={`h-3 w-3 transition-transform duration-150 ${
                  outputOpen ? "" : "-rotate-90"
                }`}
              />
              Output
            </button>
            {outputOpen && (
              <div className="rounded-md border bg-card p-4 text-sm leading-relaxed overflow-auto max-h-[500px]">
                <MarkdownRenderer content={stageOutput} />
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground italic">No output</p>
        )}
      </CardContent>
    </Card>
  );
}

export default StageTimeline;
