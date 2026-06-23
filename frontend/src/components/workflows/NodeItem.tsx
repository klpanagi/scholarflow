import { Loader2, Wrench, Activity } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { type TimelineNode } from "@/constants/workflows";
import { getStatusConfig, formatDuration } from "./workflow-helpers";
import { cn } from "@/lib/utils";

interface NodeItemProps {
  node: TimelineNode;
}

function formatNodeDuration(durationMs: number | undefined): string | null {
  if (durationMs === undefined) return null;
  if (durationMs < 1000) return `${durationMs}ms`;
  return formatDuration(durationMs / 1000);
}

function NodeTypeIcon({ type }: { type: TimelineNode["type"] }) {
  if (type === "tool_call") {
    return <Wrench className="h-3 w-3" aria-hidden="true" />;
  }
  if (type === "strategy_iteration") {
    return <Activity className="h-3 w-3" aria-hidden="true" />;
  }
  return null;
}

function NodeItem({ node }: NodeItemProps) {
  const cfg = getStatusConfig(node.status);
  const StatusIcon = cfg.icon;
  const durationLabel = formatNodeDuration(node.durationMs);
  const testId = `node-${node.name.replace(/\s+/g, "-").toLowerCase()}`;
  const showSpinner = cfg.icon === Loader2;

  return (
    <div
      data-testid={testId}
      className="flex items-center gap-2 py-1.5 pl-1 pr-2 text-xs"
    >
      <span
        className={cn(
          "h-5 w-5 rounded-full flex items-center justify-center shrink-0",
          cfg.badgeClass
        )}
      >
        <StatusIcon
          className={cn("h-3 w-3", cfg.iconClass, showSpinner && "animate-spin")}
        />
      </span>
      <span className="flex items-center gap-1.5 min-w-0 flex-1">
        <NodeTypeIcon type={node.type} />
        <span className="truncate text-foreground/90">{node.name}</span>
      </span>
      {durationLabel && (
        <Badge
          variant="outline"
          className="text-[10px] px-1.5 py-0 font-mono text-muted-foreground"
        >
          {durationLabel}
        </Badge>
      )}
    </div>
  );
}

export default NodeItem;
