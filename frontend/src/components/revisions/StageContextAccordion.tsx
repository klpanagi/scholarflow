import { useState } from "react";
import { ChevronDown, Bot, FileText, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import type { WorkflowExecutionStage, ManuscriptRating } from "@/constants/workflows";

interface StageContextAccordionProps {
  stage: WorkflowExecutionStage;
  index: number;
  selected: boolean;
  onToggle: () => void;
}

function formatTokens(count: number): string {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return String(count);
}

function formatCost(usd: number): string {
  if (usd < 0.0001) return "<$0.0001";
  return `$${usd.toFixed(4)}`;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function getStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "completed":
      return "secondary";
    case "running":
      return "default";
    case "failed":
      return "destructive";
    default:
      return "outline";
  }
}

function getConfidenceBg(confidence: ManuscriptRating["confidence"]): string {
  switch (confidence) {
    case "high":
      return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300";
    case "medium":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300";
    case "low":
      return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
  }
}

export function StageContextAccordion({ stage, index, selected, onToggle }: StageContextAccordionProps) {
  const [expanded, setExpanded] = useState(false);
  const usage = stage.metadata?.usage;
  const duration = stage.metadata?.duration_seconds;

  return (
    <Card className="border-border/60 shadow-sm">
      <CardHeader
        className={cn(
          "flex flex-row items-center gap-3 p-3 cursor-pointer select-none",
          expanded && "border-b border-border/40"
        )}
        onClick={() => setExpanded((prev) => !prev)}
      >
        <Checkbox
          checked={selected}
          onCheckedChange={() => onToggle()}
          onClick={(e) => e.stopPropagation()}
          className="shrink-0"
        />
        <Bot className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="text-sm font-medium truncate flex-1">
          Stage {index + 1}: {stage.agent_name || "Unknown Agent"}
          <span className="text-muted-foreground font-normal">
            {(stage.agent_role || stage.status) && (
              <>
                {" — "}
                {stage.agent_role && (
                  <Badge
                    variant="outline"
                    className="text-[10px] px-1.5 py-0 font-normal align-middle"
                  >
                    {stage.agent_role}
                  </Badge>
                )}
                <Badge
                  variant={getStatusVariant(stage.status)}
                  className="text-[10px] px-1.5 py-0 font-normal align-middle ml-1"
                >
                  {stage.status}
                </Badge>
              </>
            )}
          </span>
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200",
            expanded && "rotate-180"
          )}
        />
      </CardHeader>
      {expanded && (
        <CardContent className="p-3 pt-2 space-y-3 animate-in">
          <div className="max-h-80 overflow-y-auto rounded-md border border-border/40 bg-muted/20 p-3">
            <MarkdownRenderer content={stage.output || "*No output*"} />
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
            {usage && (
              <>
                <span className="inline-flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  Tokens: {formatTokens(usage.total_tokens)}
                </span>
                <span className="inline-flex items-center gap-1">
                  <span>$</span>
                  Cost: {formatCost(usage.cost_usd)}
                </span>
              </>
            )}
            {duration != null && (
              <span className="inline-flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatDuration(duration)}
              </span>
            )}
            {stage.rating && (
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold",
                  getConfidenceBg(stage.rating.confidence)
                )}
              >
                Rating: {stage.rating.overall_score.toFixed(1)} ({stage.rating.confidence})
              </span>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
