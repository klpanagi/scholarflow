import { useState, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  FlaskConical,
  LayoutGrid,
  Loader2,
  Play,
  Trash2,
  XCircle,
  Zap,
  X,
  Settings2,
  Activity,
  Layers,
  Search,
  RotateCcw,
  Coins,
  FileText,
} from "lucide-react";
import {
  WORKFLOWS,
  type Workflow,
  type WorkflowStage,
  type WorkflowExecution,
  getStageMetaByIndex,
} from "@/constants/workflows";
import { ExecutionResultCard } from "@/components/workflows/ExecutionResultCard";
import { useWorkflowStream } from "@/hooks/useWorkflowStream";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge, type StatusType } from "@/components/shared/StatusBadge";
import { WorkflowStageStatus } from "@/components/shared/WorkflowStageStatus";
import { EmptyState } from "@/components/shared/EmptyState";
import { ModalShell } from "@/components/shared/ModalShell";
import { formatDuration } from "@/components/workflows/workflow-helpers";
import { cn } from "@/lib/utils";

// ----- Types -----

interface AgentConfig {
  id: string;
  name: string;
  role: string;
  is_default?: boolean;
}

interface Asset {
  id: string;
  title: string;
  abstract?: string;
  authors?: string[];
  year?: number;
}

// ----- Role compatibility -----

const ROLE_COMPATIBILITY: Record<string, string[]> = {
  reviewer: ["reviewer", "deep_reviewer"],
  writer: ["writer", "manager"],
  researcher: ["researcher"],
  recommender: ["recommender"],
  review_writer: ["review_writer"],
  debater: ["debater"],
  manager: ["manager", "writer"],
  revision: ["revision"],
  deep_reviewer: ["deep_reviewer", "reviewer"],
};

function isRoleCompatible(configRole: string, stageRole: string): boolean {
  const allowed = ROLE_COMPATIBILITY[stageRole] ?? [stageRole];
  return allowed.includes(configRole);
}

// ----- Helpers -----

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

function mapStageStatus(status: string): StatusType {
  switch (status) {
    case "in_progress":
      return "running";
    case "error":
    case "timeout":
      return "failed";
    case "skipped":
      return "cancelled";
    default:
      return status as StatusType;
  }
}

// ----- AssetSelector (unchanged) -----

function AssetSelector({
  assets,
  selectedAssetId,
  onSelect,
}: {
  assets: Asset[];
  selectedAssetId: string | null;
  onSelect: (asset: Asset | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const selectedAsset = assets.find((a) => a.id === selectedAssetId);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
      >
        <span className="truncate">
          {selectedAsset ? selectedAsset.title : "Select an uploaded asset..."}
        </span>
        <ChevronDown className="h-4 w-4 ml-2 shrink-0 opacity-50" />
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full max-h-60 overflow-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md">
          <button
            type="button"
            onClick={() => {
              onSelect(null);
              setOpen(false);
            }}
            className="w-full text-left rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
          >
            None — use manual input
          </button>
          {assets.map((asset) => (
            <button
              key={asset.id}
              type="button"
              onClick={() => {
                onSelect(asset);
                setOpen(false);
              }}
              className={`w-full text-left rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground ${
                asset.id === selectedAssetId ? "bg-accent" : ""
              }`}
            >
              <div className="font-medium">{asset.title}</div>
              {asset.authors && asset.authors.length > 0 && (
                <div className="text-xs text-muted-foreground truncate">
                  {asset.authors.slice(0, 3).join(", ")}
                  {asset.year ? ` (${asset.year})` : ""}
                </div>
              )}
            </button>
          ))}
          {assets.length === 0 && (
            <div className="px-2 py-1.5 text-sm text-muted-foreground">
              No assets uploaded yet
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ----- PipelineDiagram (unchanged, used in WorkflowDialog) -----

function PipelineDiagram({ stages }: { stages: WorkflowStage[] }) {
  return (
    <div className="flex items-start gap-2 overflow-x-auto py-4">
      {stages.map((stage, i) => (
        <div key={i} className="flex items-start">
          <div className="flex flex-col items-center min-w-[140px]">
            <div className={`${stage.color} text-white rounded-full p-3 mb-2 shadow-lg`}>
              {stage.icon}
            </div>
            <span className="font-semibold text-sm">{stage.agent}</span>
            <Badge variant="outline" className="mt-1 text-xs">
              {stage.role}
            </Badge>
            <p className="text-xs text-muted-foreground mt-2 text-center px-2">
              {stage.description}
            </p>
          </div>
          {i < stages.length - 1 && (
            <div className="flex items-center pt-6">
              <ArrowRight className="h-6 w-6 text-muted-foreground mx-1" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ----- Stats Card (new) -----

function StatsCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div className="group relative overflow-hidden rounded-xl border border-border/50 bg-card/60 p-4 backdrop-blur-xl transition-all duration-300 hover:shadow-lg hover:border-gold-500/20">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <p className="mt-1.5 text-2xl font-bold tabular-nums text-foreground">
            {value}
          </p>
        </div>
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-full",
            color,
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-transparent via-gold-500/20 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
    </div>
  );
}

// ----- WorkflowCardCompact (redesigned with visual pipeline) -----

function MiniPipeline({ stages }: { stages: WorkflowStage[] }) {
  return (
    <div className="flex items-center gap-0">
      {stages.map((stage, i) => (
        <div key={stage.id} className="flex items-center">
          <div
            className={cn(
              "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-white text-[10px]",
              stage.color,
            )}
          >
            {stage.icon}
          </div>
          {i < stages.length - 1 && (
            <div className="mx-0.5 h-px w-5 bg-border" />
          )}
        </div>
      ))}
    </div>
  );
}

function WorkflowCardCompact({
  workflow,
  onConfigure,
}: {
  workflow: Workflow;
  onConfigure: () => void;
}) {
  return (
    <Card
      className="group overflow-hidden border-border/50 bg-card/60 backdrop-blur-xl transition-all duration-300 hover:shadow-lg hover:border-gold-500/30 cursor-pointer"
      onClick={onConfigure}
    >
      <CardContent className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-gold-500 shrink-0" />
              <h3 className="font-semibold text-foreground truncate">
                {workflow.name}
              </h3>
            </div>
            <p className="mt-1 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
              {workflow.description}
            </p>
          </div>
          <Badge
            variant="outline"
            className="shrink-0 text-[10px] px-2 py-0 h-5 border-gold-500/20 text-gold-500"
          >
            {workflow.stages.length} stages
          </Badge>
        </div>

        {/* Visual Pipeline */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Pipeline
            </span>
            <span className="text-[10px] text-muted-foreground">
              {workflow.stages.length} agents
            </span>
          </div>
          <MiniPipeline stages={workflow.stages} />
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            {workflow.stages.map((stage) => (
              <span
                key={stage.id}
                className="text-[10px] text-muted-foreground/70 capitalize"
              >
                {stage.agent}
                {workflow.stages.indexOf(stage) < workflow.stages.length - 1 && (
                  <span className="ml-1 text-border">→</span>
                )}
              </span>
            ))}
          </div>
        </div>

        {/* Use case hint */}
        <p className="mt-3 text-[11px] text-muted-foreground/60 italic leading-relaxed line-clamp-2">
          {workflow.useCase}
        </p>

        {/* Action */}
        <Button
          variant="default"
          size="sm"
          className="w-full mt-4 gap-1.5 bg-gold-500 text-white hover:bg-gold-600 shadow-sm"
          onClick={(e) => {
            e.stopPropagation();
            onConfigure();
          }}
        >
          <Settings2 className="h-3.5 w-3.5" />
          Configure & Run
        </Button>
      </CardContent>
    </Card>
  );
}

// ----- ExecutionDetailModal (new, reuses WorkflowStageStatus) -----

function ExecutionDetailModal({
  execution,
  open,
  onOpenChange,
}: {
  execution: WorkflowExecution | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  if (!execution) return null;

  return (
    <ModalShell
      open={open}
      onOpenChange={onOpenChange}
      title={
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-gold-500" />
          <span>Pipeline: {execution.workflow_name}</span>
        </div>
      }
      description={
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatTime(execution.created_at)}
          </span>
          {execution.duration_seconds && (
            <span className="tabular-nums">{formatDuration(execution.duration_seconds)}</span>
          )}
          <StatusBadge status={mapStageStatus(execution.status)} />
        </div>
      }
      size="xl"
      footer={
        <div className="flex items-center gap-2">
          {execution.status === "completed" && (
            <Button
              variant="default"
              size="sm"
              className="gap-1.5 bg-gold-500 text-white hover:bg-gold-600"
              onClick={() => onOpenChange(false)}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Re-run Workflow
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            Close
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Input */}
        {execution.input_text && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-2">Input</h4>
            <p className="text-sm text-muted-foreground bg-muted/30 rounded-lg p-3 border border-border/30 italic leading-relaxed">
              &ldquo;{execution.input_text}&rdquo;
            </p>
          </div>
        )}

        {/* Pipeline Stages */}
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-3">Pipeline Stages</h4>
          <div className="space-y-3">
            {execution.stages.map((stage, i) => {
              const meta = getStageMetaByIndex(execution.workflow_id, i);
              const duration = stage.metadata?.duration_seconds
                ? formatDuration(stage.metadata.duration_seconds)
                : null;
              const usage = stage.metadata?.usage;

              return (
                <div
                  key={i}
                  className="group rounded-lg border border-border/40 bg-muted/20 p-4 transition-colors hover:border-gold-500/20"
                >
                  <div className="flex items-start justify-between gap-4">
                    <WorkflowStageStatus
                      status={mapStageStatus(stage.status) as any}
                      name={stage.agent_name || stage.agent_role || `Stage ${i + 1}`}
                      size="md"
                      className="min-w-0"
                    />
                    <div className="flex shrink-0 items-center gap-3 text-xs text-muted-foreground">
                      {duration && (
                        <span className="tabular-nums flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {duration}
                        </span>
                      )}
                      {usage && usage.total_tokens > 0 && (
                        <span className="tabular-nums flex items-center gap-1">
                          <Coins className="h-3 w-3" />
                          {usage.total_tokens >= 1000
                            ? `${(usage.total_tokens / 1000).toFixed(1)}K`
                            : usage.total_tokens}{" "}
                          tok
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Stage description */}
                  {meta.description && (
                    <p className="mt-2 text-xs text-muted-foreground/70 leading-relaxed">
                      {meta.description}
                    </p>
                  )}

                  {/* Output snippet */}
                  {stage.output && stage.output.trim().length > 0 && (
                    <details className="group mt-2">
                      <summary className="flex items-center gap-1 text-[11px] text-muted-foreground cursor-pointer hover:text-foreground transition-colors list-none">
                        <ChevronDown className="h-3 w-3 transition-transform group-open:rotate-0 -rotate-90" />
                        View output
                      </summary>
                      <div className="mt-2 rounded-md border border-border/30 bg-card p-3 text-xs leading-relaxed max-h-32 overflow-y-auto">
                        {stage.output.substring(0, 500)}
                        {stage.output.length > 500 && "…"}
                      </div>
                    </details>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Stage flow diagram */}
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-3">Flow Diagram</h4>
          <div className="flex items-center justify-center gap-0 overflow-x-auto py-4 px-2 rounded-lg border border-border/30 bg-muted/10">
            {execution.stages.map((stage, i) => {
              const meta = getStageMetaByIndex(execution.workflow_id, i);
              const isActive = mapStageStatus(stage.status);
              return (
                <div key={i} className="flex items-center">
                  <div className="flex flex-col items-center min-w-[80px]">
                    <div
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-full text-white text-sm shadow-sm transition-all",
                        meta.color || "bg-navy-500",
                        isActive === "completed" && "ring-2 ring-emerald-500/30 ring-offset-2 ring-offset-card",
                        isActive === "running" && "ring-2 ring-gold-500/30 ring-offset-2 ring-offset-card animate-pulse",
                        isActive === "failed" && "ring-2 ring-red-500/30 ring-offset-2 ring-offset-card",
                      )}
                    >
                      {meta.icon || <FileText className="h-4 w-4" />}
                    </div>
                    <span className="mt-1.5 text-[10px] font-medium text-foreground capitalize text-center">
                      {stage.agent_name || stage.agent_role || `S${i + 1}`}
                    </span>
                    <StatusBadge
                      status={mapStageStatus(stage.status)}
                      variant="outline"
                      className="mt-1 text-[9px] px-1.5 py-0 h-4"
                    />
                  </div>
                  {i < execution.stages.length - 1 && (
                    <div className="flex items-center mx-2">
                      <ArrowRight className="h-4 w-4 text-muted-foreground/40" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </ModalShell>
  );
}

// ----- WorkflowDialog (kept, with glassmorphism styling) -----

function WorkflowDialog({
  workflow,
  assets,
  userConfigs,
  configsError,
  configsLoading,
  open,
  onOpenChange,
  onExecute,
  isExecuting,
}: {
  workflow: Workflow;
  assets: Asset[];
  userConfigs: AgentConfig[];
  configsError: unknown | null;
  configsLoading: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onExecute: (id: string, customPrompt: string, assetId?: string, assignments?: Record<string, string>, includeFullPaper?: boolean, rubricStandard?: string) => void;
  isExecuting: boolean;
}) {
  const [customPrompt, setCustomPrompt] = useState("");
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [includeFullPaper, setIncludeFullPaper] = useState(true);
  const [rubricStandard, setRubricStandard] = useState("general");
  useEffect(() => {
    if (open) {
      setCustomPrompt("");
      setSelectedAssetId(null);
    }
  }, [open, workflow.id]);

  useEffect(() => {
    const newAssignments = { ...assignments };
    let changed = false;
    workflow.stages.forEach((stage) => {
      if (!newAssignments[stage.id]) {
        const availableConfigs = userConfigs.filter((c) => isRoleCompatible(c.role, stage.role));
        if (availableConfigs.length > 0) {
          const nameMatch = availableConfigs.find(
            (c) => c.name.toLowerCase() === stage.agent.toLowerCase()
          );
          const defaultCfg = nameMatch
            || availableConfigs.find((c) => c.is_default)
            || availableConfigs[0];
          newAssignments[stage.id] = defaultCfg.id;
          changed = true;
        }
      }
    });
    if (changed) {
      setAssignments(newAssignments);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow.stages, userConfigs, open]);

  const handleAssetSelect = (asset: Asset | null) => {
    setSelectedAssetId(asset?.id || null);
  };

  const handleAssignmentChange = (stageId: string, configId: string) => {
    setAssignments((prev) => ({ ...prev, [stageId]: configId }));
  };

  const handleExecute = () => {
    const missingStages = workflow.stages
      .map((s) => s.id)
      .filter((stageId) => !assignments[stageId]);

    if (missingStages.length > 0) {
      return;
    }

    onExecute(workflow.id, customPrompt, selectedAssetId || undefined, assignments, includeFullPaper, rubricStandard);
    onOpenChange(false);
  };

  const isMissingAssignments = workflow.stages.some((stage) => !assignments[stage.id]);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-full max-w-3xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-border/50 bg-card/60 p-6 shadow-2xl backdrop-blur-xl data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]">
          <Dialog.Title className="sr-only">{workflow.name}</Dialog.Title>

          <div className="flex items-start justify-between mb-6">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-gold-500" />
                <h2 className="text-xl font-bold text-foreground">{workflow.name}</h2>
                <Badge variant="outline" className="text-[10px] px-2 py-0 h-5 border-gold-500/20 text-gold-500">
                  {workflow.stages.length} agents
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-1">{workflow.description}</p>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
                <X className="h-4 w-4" />
              </Button>
            </Dialog.Close>
          </div>

          <div className="bg-muted/30 rounded-lg border border-border/30 p-4 mb-6">
            <p className="text-sm font-medium text-foreground mb-1">When to use:</p>
            <p className="text-sm text-muted-foreground">{workflow.useCase}</p>
          </div>

          <div className="mb-6">
            <p className="text-sm font-medium text-foreground mb-3">Pipeline:</p>
            <PipelineDiagram stages={workflow.stages} />
          </div>

          <div className="space-y-4 mb-6">
            <p className="text-sm font-medium text-foreground">Agent Assignments</p>
            <div className="grid gap-3">
              {workflow.stages.map((stage, index) => {
                const availableConfigs = userConfigs.filter((c) => isRoleCompatible(c.role, stage.role));
                return (
                  <div key={stage.id} className="flex items-center justify-between gap-4">
                    <div className="text-sm font-medium min-w-24 capitalize text-foreground">Step {index + 1} ({stage.agent}):</div>
                    <div className="flex-1">
                      <select
                        className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                        value={assignments[stage.id] || ""}
                        onChange={(e) => handleAssignmentChange(stage.id, e.target.value)}
                      >
                        <option value="" disabled>
                          Select {stage.agent} agent for step {index + 1}...
                        </option>
                        {availableConfigs.map((config) => (
                          <option key={config.id} value={config.id}>
                            {config.name}
                          </option>
                        ))}
                      </select>
                      {availableConfigs.length === 0 && (
                        <p className="text-xs text-destructive mt-1">
                          {configsError
                            ? `Cannot load agents: ${(configsError as any)?.message || 'backend unavailable'}`
                            : configsLoading
                              ? "Loading agents..."
                              : `No ${stage.agent} agents configured. Create one in Agents settings.`}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            {isMissingAssignments && (
              <p className="text-xs text-destructive">
                * Please assign an agent for each required step to run this workflow.
              </p>
            )}
          </div>

          <div className="space-y-3 border-t border-border/50 pt-4">
            <label className="text-sm font-medium text-foreground">Select Asset (optional)</label>
            <AssetSelector
              assets={assets}
              selectedAssetId={selectedAssetId}
              onSelect={handleAssetSelect}
            />

            {selectedAssetId && (
              <div className="flex items-center gap-2 mt-2">
                <input
                  type="checkbox"
                  id="include-full-paper"
                  checked={includeFullPaper}
                  onChange={(e) => setIncludeFullPaper(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <label htmlFor="include-full-paper" className="text-sm text-muted-foreground">
                  Include full paper text in review (slower, more thorough)
                </label>
              </div>
            )}

            {workflow.id === "paper-review" && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">Rating Rubric Standard</label>
                <select
                  className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  value={rubricStandard}
                  onChange={(e) => setRubricStandard(e.target.value)}
                >
                  <option value="general">General (balanced)</option>
                  <option value="ieee">IEEE (CS/Engineering)</option>
                  <option value="acm">ACM (Software focus)</option>
                  <option value="nature">Nature/Science (High-impact)</option>
                  <option value="medical">Medical (CONSORT)</option>
                </select>
                <p className="text-xs text-muted-foreground">
                  Determines the scoring criteria and weights for the Overall Manuscript Rating.
                </p>
              </div>
            )}

            <label className="text-sm font-medium text-foreground">Custom Instructions (optional)</label>
            <p className="text-xs text-muted-foreground -mt-2">
              Add specific instructions for the agents. If an asset is selected, these instructions will be
              appended to its content.
            </p>
            <Textarea
              placeholder="E.g., Focus on novelty assessment, check for reproducibility, compare against recent tools..."
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              rows={3}
            />

            <Button
              onClick={handleExecute}
              disabled={isExecuting || isMissingAssignments}
              className="w-full bg-gold-500 text-white hover:bg-gold-600"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Executing Pipeline...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Workflow
                </>
              )}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}



// ----- LiveExecutionCard (unchanged) -----

function LiveExecutionCard({
  execution,
  onDelete,
}: {
  execution: WorkflowExecution;
  onDelete?: (id: string) => void;
}) {
  const isRunning =
    execution.status === "running" ||
    execution.status === "pending" ||
    execution.status === "cancelling";
  const { events } = useWorkflowStream(execution.id, { enabled: isRunning });
  return (
    <ExecutionResultCard
      execution={execution}
      events={events}
      onDelete={onDelete}
    />
  );
}

// ===== Main Page Component =====

type StatusFilter = "all" | "active" | "completed" | "failed";

const STATUS_FILTERS: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "completed", label: "Completed" },
  { key: "failed", label: "Failed" },
];

export default function WorkflowsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("execute");
  const [dialogWorkflow, setDialogWorkflow] = useState<Workflow | null>(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [detailExecution, setDetailExecution] = useState<WorkflowExecution | null>(null);

  // ----- Data fetching -----

  const { data: assetsData } = useQuery({
    queryKey: ["assets"],
    queryFn: async () => {
      const { data } = await api.get("/assets");
      return (data.items || []) as Asset[];
    },
  });
  const assets = assetsData || [];

  const { data: userConfigs = [], error: configsError, isLoading: configsLoading } = useQuery<AgentConfig[]>({
    queryKey: ["agent-configs"],
    queryFn: async () => {
      const { data } = await api.get("/agents/configs");
      return data || [];
    },
  });

  useEffect(() => {
    if (configsError) {
      toast({
        title: "Failed to load agents",
        description: (configsError as any)?.message || "Could not load agent configurations",
        variant: "destructive",
      });
    }
  }, [configsError, toast]);

  const { data: pastExecutions = [] } = useQuery<WorkflowExecution[]>({
    queryKey: ["workflow-results"],
    queryFn: async () => {
      const { data } = await api.get("/workflows/results");
      return data || [];
    },
    refetchInterval: (query) => {
      const executions = query.state.data as WorkflowExecution[] | undefined;
      if (!executions) return false;
      const hasRunning = executions.some(
        (e) => e.status === "running" || e.status === "pending" || e.status === "cancelling"
      );
      return hasRunning ? 3000 : false;
    },
  });

  // ----- Mutations -----

  const deleteMutation = useMutation({
    mutationFn: async (executionId: string) => {
      await api.delete(`/workflows/results/${executionId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflow-results"] });
      toast({ title: "Result deleted" });
    },
    onError: (error: any) => {
      toast({
        title: "Delete failed",
        description: error.response?.data?.detail || "Something went wrong",
        variant: "destructive",
      });
    },
  });

  const deleteAllMutation = useMutation({
    mutationFn: async () => {
      await api.delete("/workflows/results");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflow-results"] });
      toast({ title: "All results cleared" });
    },
    onError: (error: any) => {
      toast({
        title: "Clear failed",
        description: error.response?.data?.detail || "Something went wrong",
        variant: "destructive",
      });
    },
  });

  const executeMutation = useMutation({
    mutationFn: async ({
      workflowId,
      customPrompt,
      assetId,
      agentAssignments,
      includeFullPaper,
      rubricStandard,
      reviewText,
    }: {
      workflowId: string;
      customPrompt: string;
      assetId?: string;
      agentAssignments?: Record<string, string>;
      includeFullPaper?: boolean;
      rubricStandard?: string;
      reviewText?: string;
    }) => {
      const { data } = await api.post("/workflows/execute", {
        workflow_id: workflowId,
        input: customPrompt || null,
        paper_id: assetId || null,
        agent_assignments: agentAssignments,
        include_full_paper: includeFullPaper ?? true,
        rubric_standard: rubricStandard || "general",
        review_text: reviewText || null,
      });
      return data;
    },
    onSuccess: () => {
      setActiveTab("results");
      queryClient.invalidateQueries({ queryKey: ["workflow-results"] });
      toast({ title: "Workflow started", description: "Progress is shown in the Results tab." });
    },
    onError: (error: any) => {
      toast({
        title: "Workflow failed to start",
        description: error.response?.data?.detail || "Something went wrong",
        variant: "destructive",
      });
    },
  });

  // ----- Computed stats -----

  const totalExecutions = pastExecutions.length;
  const activeExecutions = pastExecutions.filter(
    (e) => e.status === "running" || e.status === "pending" || e.status === "cancelling"
  ).length;
  const completedExecutions = pastExecutions.filter((e) => e.status === "completed").length;
  const failedExecutions = pastExecutions.filter(
    (e) => e.status === "failed" || e.status === "error"
  ).length;

  // ----- Sorting & filtering -----

  const sortedExecutions = [...pastExecutions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const filteredExecutions = sortedExecutions.filter((exec) => {
    if (statusFilter === "active") {
      if (!["running", "pending", "cancelling"].includes(exec.status)) return false;
    } else if (statusFilter === "completed") {
      if (exec.status !== "completed") return false;
    } else if (statusFilter === "failed") {
      if (!["failed", "error", "timeout"].includes(exec.status)) return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchesName = exec.workflow_name?.toLowerCase().includes(q);
      const matchesInput = exec.input_text?.toLowerCase().includes(q);
      if (!matchesName && !matchesInput) return false;
    }
    return true;
  });

  const ITEMS_PER_PAGE = 5;
  const totalPages = Math.max(1, Math.ceil(filteredExecutions.length / ITEMS_PER_PAGE));
  const safePage = Math.min(page, totalPages);
  const paginatedExecutions = filteredExecutions.slice(
    (safePage - 1) * ITEMS_PER_PAGE,
    safePage * ITEMS_PER_PAGE
  );

  useEffect(() => {
    setPage(1);
  }, [statusFilter, searchQuery]);

  return (
    <div className="space-y-8">
      {/* Hero */}
      <PageHeader
        title="Workflows"
        description="Orchestrate specialized AI agents to accomplish complex academic tasks. Each workflow chains agents with distinct expertise for end-to-end results."
        actions={
          <Button
            className="bg-gold-500 text-white hover:bg-gold-600 shadow-sm gap-1.5"
            onClick={() => {
              const el = document.getElementById("workflows-grid");
              if (el) el.scrollIntoView({ behavior: "smooth" });
            }}
          >
            <Zap className="h-4 w-4" />
            New Workflow
          </Button>
        }
      />

      {/* Stats Row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatsCard
          label="Total"
          value={totalExecutions}
          icon={Activity}
          color="bg-gold-500/10 text-gold-500"
        />
        <StatsCard
          label="Active"
          value={activeExecutions}
          icon={Loader2}
          color="bg-blue-500/10 text-blue-500"
        />
        <StatsCard
          label="Completed"
          value={completedExecutions}
          icon={CheckCircle2}
          color="bg-emerald-500/10 text-emerald-500"
        />
        <StatsCard
          label="Failed"
          value={failedExecutions}
          icon={XCircle}
          color="bg-red-500/10 text-red-500"
        />
      </div>

      {/* Tabs */}
      <div className="space-y-6">
        {/* Tab bar */}
        <div className="flex items-center gap-1 rounded-lg border border-border/50 bg-card/30 p-1 backdrop-blur-xl w-fit">
          <button
            type="button"
            onClick={() => setActiveTab("execute")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all",
              activeTab === "execute"
                ? "bg-gold-500 text-white shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
            )}
          >
            <Play className="h-3.5 w-3.5" />
            Execute
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("results")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all",
              activeTab === "results"
                ? "bg-gold-500 text-white shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
            )}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            Results
            {totalExecutions > 0 && (
              <span className="ml-1 rounded-full bg-muted-foreground/20 px-1.5 py-0 text-[10px] tabular-nums">
                {totalExecutions}
              </span>
            )}
          </button>
        </div>

        {/* ── Execute Tab ── */}
        {activeTab === "execute" && (
          <div id="workflows-grid" className="grid gap-6 lg:grid-cols-2">
            {WORKFLOWS.map((workflow) => (
              <WorkflowCardCompact
                key={workflow.id}
                workflow={workflow}
                onConfigure={() => setDialogWorkflow(workflow)}
              />
            ))}
          </div>
        )}

        {/* ── Results Tab ── */}
        {activeTab === "results" && (
          <div className="space-y-5">
            {/* Filter bar */}
            {totalExecutions > 0 && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                {/* Status filter pills */}
                <div className="flex items-center gap-1 rounded-lg border border-border/50 bg-card/30 p-1 backdrop-blur-xl">
                  {STATUS_FILTERS.map((f) => (
                    <button
                      key={f.key}
                      type="button"
                      onClick={() => setStatusFilter(f.key)}
                      className={cn(
                        "rounded-md px-3 py-1 text-xs font-medium transition-all",
                        statusFilter === f.key
                          ? "bg-gold-500 text-white shadow-sm"
                          : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                      )}
                    >
                      {f.label}
                      {f.key === "all" && ` (${totalExecutions})`}
                      {f.key === "active" && activeExecutions > 0 && ` (${activeExecutions})`}
                      {f.key === "completed" && completedExecutions > 0 && ` (${completedExecutions})`}
                      {f.key === "failed" && failedExecutions > 0 && ` (${failedExecutions})`}
                    </button>
                  ))}
                </div>

                {/* Search */}
                <div className="relative w-full sm:w-64">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                  <input
                    type="text"
                    placeholder="Search by name or input..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full rounded-lg border border-border/50 bg-card/30 py-1.5 pl-8 pr-3 text-sm text-foreground placeholder:text-muted-foreground/50 backdrop-blur-xl focus:outline-none focus:ring-2 focus:ring-gold-500/30 focus:border-gold-500/50 transition-all"
                  />
                </div>
              </div>
            )}

            {/* Execution list */}
            {filteredExecutions.length === 0 ? (
              <EmptyState
                icon={FlaskConical}
                title={
                  totalExecutions === 0
                    ? "No results yet"
                    : "No matching executions"
                }
                description={
                  totalExecutions === 0
                    ? "Run a workflow to see your results here. Each execution shows the full pipeline with per-stage status and outputs."
                    : "Try adjusting the filters or search query."
                }
                action={
                  totalExecutions === 0
                    ? { label: "Go to Execute", onClick: () => setActiveTab("execute") }
                    : undefined
                }
              />
            ) : (
              <div className="space-y-4">
                {/* Summary + Clear All */}
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Showing {paginatedExecutions.length} of {filteredExecutions.length} result
                    {filteredExecutions.length !== 1 ? "s" : ""}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs gap-1.5 text-destructive hover:text-destructive hover:bg-destructive/10 border-destructive/20 hover:border-destructive/30"
                    onClick={() => deleteAllMutation.mutate()}
                    disabled={deleteAllMutation.isPending}
                  >
                    {deleteAllMutation.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5" />
                    )}
                    Clear All
                  </Button>
                </div>

                {/* Cards */}
                <div className="space-y-3">
                  {paginatedExecutions.map((exec) => (
                    <div key={exec.id} className="group relative">
                      <LiveExecutionCard
                        execution={exec}
                        onDelete={(id) => deleteMutation.mutate(id)}
                      />
                      {/* Pipeline detail button */}
                      <button
                        type="button"
                        onClick={() => setDetailExecution(exec)}
                        className="absolute top-3 right-12 z-10 flex items-center gap-1 rounded-md border border-border/40 bg-card/80 px-2 py-1 text-[11px] font-medium text-muted-foreground backdrop-blur-sm opacity-0 transition-opacity group-hover:opacity-100 hover:text-gold-500 hover:border-gold-500/30"
                      >
                        <Layers className="h-3 w-3" />
                        Pipeline
                      </button>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 gap-1"
                      disabled={safePage <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      <ChevronLeft className="h-3.5 w-3.5" />
                      Prev
                    </Button>
                    <span className="text-sm text-muted-foreground tabular-nums px-2">
                      Page {safePage} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 gap-1"
                      disabled={safePage >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Configure & Run Dialog */}
      {dialogWorkflow && (
        <WorkflowDialog
          key={dialogWorkflow.id}
          workflow={dialogWorkflow}
          assets={assets}
          userConfigs={userConfigs}
          configsError={configsError}
          configsLoading={configsLoading}
          open={!!dialogWorkflow}
          onOpenChange={(open) => { if (!open) setDialogWorkflow(null); }}
          onExecute={(id, customPrompt, assetId, assignments, includeFullPaper, rubricStandard) =>
            executeMutation.mutate({
              workflowId: id,
              customPrompt,
              assetId,
              agentAssignments: assignments,
              includeFullPaper,
              rubricStandard,
            })
          }
          isExecuting={
            executeMutation.isPending &&
            executeMutation.variables?.workflowId === dialogWorkflow.id
          }
        />
      )}

      {/* Pipeline Detail Modal */}
      <ExecutionDetailModal
        execution={detailExecution}
        open={!!detailExecution}
        onOpenChange={(open) => { if (!open) setDetailExecution(null); }}
      />
    </div>
  );
}
