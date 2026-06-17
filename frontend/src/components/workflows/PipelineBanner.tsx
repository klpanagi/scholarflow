import { getStageMetaByIndex } from "@/constants/workflows";
import { ArrowRight, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatDuration, getStatusConfig } from "./workflow-helpers";

export interface StageBlockData {
  index: number;
  agentName: string;
  agentRole: string;
  status: string;
  duration?: number;
}

interface PipelineBannerProps {
  stages: StageBlockData[];
  workflowId: string;
  selectedIndex: number | null;
  onStageClick: (index: number) => void;
}

function PipelineBanner({
  stages,
  workflowId,
  selectedIndex,
  onStageClick,
}: PipelineBannerProps) {
  return (
    <div className="w-full overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent">
      <div className="flex items-center gap-0 min-w-max px-1">
        {stages.map((stage, idx) => {
          const meta = getStageMetaByIndex(workflowId, stage.index);
          const statusConfig = getStatusConfig(stage.status);
          const StatusIcon = statusConfig.icon;
          const isSelected = selectedIndex === stage.index;
          const displayName = stage.agentName || stage.agentRole;

          return (
            <div key={`${workflowId}-${stage.index}`} className="flex items-center">
              <button
                type="button"
                onClick={() => onStageClick(stage.index)}
                className={cn(
                  "rounded-lg border bg-card p-3 min-w-[130px] flex flex-col items-center gap-1.5 cursor-pointer transition-all duration-200",
                  "hover:shadow-md hover:border-primary/20",
                  isSelected &&
                    "ring-2 ring-primary ring-offset-2 shadow-md bg-accent/30"
                )}
              >
                <div className="relative">
                  <div
                    className={cn(
                      "h-12 w-12 rounded-full flex items-center justify-center text-white shrink-0",
                      meta.color
                    )}
                  >
                    {meta.icon}
                  </div>
                  <div
                    className={cn(
                      "absolute -bottom-0.5 -right-0.5 rounded-full bg-background p-0.5"
                    )}
                  >
                    <StatusIcon
                      className={cn(
                        "h-4 w-4",
                        statusConfig.iconClass,
                        statusConfig.icon === Loader2 && "animate-spin"
                      )}
                    />
                  </div>
                </div>

                <span className="text-sm font-semibold text-foreground text-center leading-tight">
                  {displayName}
                </span>

                <Badge
                  variant="outline"
                  className={cn(
                    "text-[10px] font-medium px-2 py-0 leading-relaxed",
                    statusConfig.badgeClass
                  )}
                >
                  {statusConfig.label}
                </Badge>

                {stage.duration !== undefined && (
                  <span className="text-[11px] text-muted-foreground font-mono">
                    {formatDuration(stage.duration)}
                  </span>
                )}
              </button>

              {idx < stages.length - 1 && (
                <div className="flex items-center shrink-0 px-1">
                  <ArrowRight className="h-5 w-5 text-muted-foreground/30" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export { PipelineBanner };
export type { PipelineBannerProps };
