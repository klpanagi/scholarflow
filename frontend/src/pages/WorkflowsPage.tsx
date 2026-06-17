import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Clock,
  FlaskConical,
  LayoutGrid,
  Loader2,
  Play,
  Trash2,
  XCircle,
  Zap,
} from "lucide-react";
import { WORKFLOWS, type Workflow, type WorkflowStage, type WorkflowExecution } from "@/constants/workflows";
import { ExecutionResultCard } from "@/components/workflows/ExecutionResultCard";

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

function PipelineDiagram({ stages }: { stages: WorkflowStage[] }) {
  return (
    <div className="flex items-start gap-2 overflow-x-auto py-4">
      {stages.map((stage, i) => (
        <div key={i} className="flex items-start">
          <div className="flex flex-col items-center min-w-[140px]">
            <div
              className={`${stage.color} text-white rounded-full p-3 mb-2 shadow-lg`}
            >
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

function WorkflowCard({
  workflow,
  assets,
  userConfigs,
  onExecute,
  isExecuting,
}: {
  workflow: Workflow;
  assets: Asset[];
  userConfigs: AgentConfig[];
  onExecute: (id: string, input: string, assetId?: string, assignments?: Record<string, string>) => void;
  isExecuting: boolean;
}) {
  const [input, setInput] = useState("");
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [assignments, setAssignments] = useState<Record<string, string>>({});

  useEffect(() => {
    const newAssignments = { ...assignments };
    let changed = false;
    workflow.stages.forEach((stage) => {
      if (!newAssignments[stage.id]) {
        const availableConfigs = userConfigs.filter((c) => c.role === stage.role);
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
  }, [workflow.stages, userConfigs]);

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
    
    onExecute(workflow.id, input, selectedAssetId || undefined, assignments);
  };

  const isMissingAssignments = workflow.stages.some((stage) => !assignments[stage.id]);

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            {workflow.name}
          </CardTitle>
          <Badge variant="secondary">{workflow.stages.length} agents</Badge>
        </div>
        <CardDescription>{workflow.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="bg-muted/50 rounded-lg p-4">
          <p className="text-sm font-medium mb-1">When to use:</p>
          <p className="text-sm text-muted-foreground">{workflow.useCase}</p>
        </div>

        <div>
          <p className="text-sm font-medium mb-3">Pipeline:</p>
          <PipelineDiagram stages={workflow.stages} />
        </div>

        <div className="space-y-4 border-t pt-4">
          <p className="text-sm font-medium">Agent Assignments</p>
          <div className="grid gap-3">
            {workflow.stages.map((stage, index) => {
              const availableConfigs = userConfigs.filter((c) => c.role === stage.role);
              return (
                <div key={stage.id} className="flex items-center justify-between gap-4">
                  <div className="text-sm font-medium min-w-24 capitalize">Step {index + 1} ({stage.role}):</div>
                  <div className="flex-1">
                    <select
                      className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                      value={assignments[stage.id] || ""}
                      onChange={(e) => handleAssignmentChange(stage.id, e.target.value)}
                    >
                      <option value="" disabled>
                        Select {stage.role} agent for step {index + 1}...
                      </option>
                      {availableConfigs.map((config) => (
                        <option key={config.id} value={config.id}>
                          {config.name}
                        </option>
                      ))}
                    </select>
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

        <div className="space-y-3 border-t pt-4">
          <label className="text-sm font-medium">Select Asset (optional)</label>
          <AssetSelector
            assets={assets}
            selectedAssetId={selectedAssetId}
            onSelect={handleAssetSelect}
          />

          <label className="text-sm font-medium">{workflow.inputLabel}</label>
          <Textarea
            placeholder={workflow.inputPlaceholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={3}
          />
          <Button
            onClick={handleExecute}
            disabled={!input.trim() || isExecuting || isMissingAssignments}
            className="w-full"
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
      </CardContent>
    </Card>
  );
}



export default function WorkflowsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("execute");

  const { data: assetsData } = useQuery({
    queryKey: ["assets"],
    queryFn: async () => {
      const { data } = await api.get("/assets");
      return (data.items || []) as Asset[];
    },
  });
  const assets = assetsData || [];

  const { data: userConfigs = [] } = useQuery<AgentConfig[]>({
    queryKey: ["agent-configs"],
    queryFn: async () => {
      const { data } = await api.get("/agents/configs");
      return data || [];
    },
  });

  const { data: pastExecutions = [] } = useQuery<WorkflowExecution[]>({
    queryKey: ["workflow-results"],
    queryFn: async () => {
      const { data } = await api.get("/workflows/results");
      return data || [];
    },
  });

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
      input,
      assetId,
      agentAssignments,
    }: {
      workflowId: string;
      input: string;
      assetId?: string;
      agentAssignments?: Record<string, string>;
    }) => {
      const { data } = await api.post("/workflows/execute", {
        workflow_id: workflowId,
        input,
        paper_id: assetId,
        agent_assignments: agentAssignments,
      });
      return data as WorkflowExecution;
    },
    onSuccess: () => {
      setActiveTab("results");
      toast({ title: "Workflow completed", description: "View the results in the Results tab." });
    },
    onError: (error: any) => {
      toast({
        title: "Workflow failed",
        description: error.response?.data?.detail || "Something went wrong",
        variant: "destructive",
      });
    },
  });

  const sortedExecutions = [...pastExecutions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Multi-Agent Workflows</h1>
        <p className="text-muted-foreground mt-2">
          Orchestrate multiple specialized agents to accomplish complex academic tasks. Each workflow
          chains agents with distinct expertise for end-to-end results.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} defaultValue="execute">
        <TabsList>
          <TabsTrigger value="execute" className="gap-1.5">
            <Play className="h-3.5 w-3.5" />
            Execute
          </TabsTrigger>
          <TabsTrigger value="results" className="gap-1.5">
            <LayoutGrid className="h-3.5 w-3.5" />
            Results
            {sortedExecutions.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-[10px] px-1.5 py-0">
                {sortedExecutions.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="execute">
          <div className="grid gap-6 lg:grid-cols-2">
            {WORKFLOWS.map((workflow) => (
              <WorkflowCard
                key={workflow.id}
                workflow={workflow}
                assets={assets}
                userConfigs={userConfigs}
                onExecute={(id, input, assetId, assignments) =>
                  executeMutation.mutate({
                    workflowId: id,
                    input,
                    assetId,
                    agentAssignments: assignments,
                  })
                }
                isExecuting={
                  executeMutation.isPending &&
                  executeMutation.variables?.workflowId === workflow.id
                }
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="results">
          {sortedExecutions.length === 0 ? (
            <Card className="overflow-hidden">
              <CardContent className="py-16 text-center">
                <div className="mb-6">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/5 ring-1 ring-primary/10 mb-4">
                    <FlaskConical className="h-8 w-8 text-primary/40" />
                  </div>
                  <h3 className="text-lg font-semibold mb-1">No results yet</h3>
                  <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                    Run a workflow to see your results here. Each execution shows the full pipeline
                    with per-stage status and outputs.
                  </p>
                </div>
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => setActiveTab("execute")}
                  className="gap-1.5"
                >
                  <Play className="h-3.5 w-3.5" />
                  Go to Execute
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <p className="text-sm text-muted-foreground">
                    {sortedExecutions.length} result{sortedExecutions.length !== 1 ? "s" : ""}
                  </p>
                  {(() => {
                    const completed = sortedExecutions.filter((e) => e.status === "completed").length;
                    const failed = sortedExecutions.filter((e) => e.status === "failed").length;
                    const partial = sortedExecutions.filter((e) => e.status === "partial").length;
                    const other = sortedExecutions.length - completed - failed - partial;
                    return (
                      <div className="hidden sm:flex items-center gap-1.5">
                        {completed > 0 && (
                          <Badge variant="outline" className="gap-1 text-[11px] px-2 py-0 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30">
                            <CheckCircle2 className="h-3 w-3" />
                            {completed}
                          </Badge>
                        )}
                        {failed > 0 && (
                          <Badge variant="outline" className="gap-1 text-[11px] px-2 py-0 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30">
                            <XCircle className="h-3 w-3" />
                            {failed}
                          </Badge>
                        )}
                        {partial > 0 && (
                          <Badge variant="outline" className="gap-1 text-[11px] px-2 py-0 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30">
                            <Clock className="h-3 w-3" />
                            {partial}
                          </Badge>
                        )}
                        {other > 0 && (
                          <Badge variant="outline" className="gap-1 text-[11px] px-2 py-0 text-muted-foreground">
                            {other} other
                          </Badge>
                        )}
                      </div>
                    );
                  })()}
                </div>
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
              <div className="space-y-3">
                {sortedExecutions.map((exec) => (
                  <ExecutionResultCard
                    key={exec.id}
                    execution={exec}
                    onDelete={(id) => deleteMutation.mutate(id)}
                  />
                ))}
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
