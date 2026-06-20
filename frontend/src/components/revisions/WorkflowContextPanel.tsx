import { FileText, Bot } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { StageContextAccordion } from "@/components/revisions/StageContextAccordion";
import type { WorkflowExecution } from "@/constants/workflows";

interface WorkflowContextPanelProps {
  execution: WorkflowExecution;
  selectedStageIds: Set<string>;
  onToggleStage: (stageId: string) => void;
}

export function WorkflowContextPanel({ execution, selectedStageIds, onToggleStage }: WorkflowContextPanelProps) {
  const stages = execution.stages || [];
  const totalStages = stages.length;

  return (
    <div className="flex flex-col h-full">
      <div className="sticky top-0 z-10 bg-background border-b border-border/60 px-4 py-3">
        <div className="flex items-center gap-2 mb-1">
          <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="text-sm font-semibold truncate">{execution.workflow_name}</span>
        </div>
        {execution.input_text && (
          <p className="text-xs text-muted-foreground truncate mt-0.5" title={execution.input_text}>
            {execution.input_text}
          </p>
        )}
        <div className="flex items-center gap-2 mt-2">
          <Badge variant="secondary" className="text-[10px] px-2 py-0">
            {selectedStageIds.size} of {totalStages} stages included
          </Badge>
          <span className="text-[10px] text-muted-foreground/60">
            {execution.status}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {totalStages === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <Bot className="h-8 w-8 mb-2 opacity-40" />
            <p className="text-sm">No stages to display</p>
          </div>
        ) : (
          stages.map((stage, index) => {
            const stageId = `stage-${index}`;
            return (
              <StageContextAccordion
                key={stageId}
                stage={stage}
                index={index}
                selected={selectedStageIds.has(stageId)}
                onToggle={() => onToggleStage(stageId)}
              />
            );
          })
        )}
      </div>
    </div>
  );
}
