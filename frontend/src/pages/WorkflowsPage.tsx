import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import {
  ArrowRight,
  BookOpen,
  ChevronDown,
  Clock,
  FileText,
  FlaskConical,
  LayoutGrid,
  Loader2,
  Play,
  Search,
  Shield,
  Trash2,
  Users,
  Zap,
} from "lucide-react";

interface AgentConfig {
  id: string;
  name: string;
  role: string;
  is_default?: boolean;
}

interface WorkflowStage {
  id: string;
  agent: string;
  role: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  useCase: string;
  stages: WorkflowStage[];
  inputPlaceholder: string;
  inputLabel: string;
}

interface Asset {
  id: string;
  title: string;
  abstract?: string;
  authors?: string[];
  year?: number;
}

const WORKFLOWS: Workflow[] = [
  {
    id: "paper-review",
    name: "Paper Review Pipeline",
    description:
      "A rigorous 7-stage review process that evaluates papers for novelty, technical rigor, reproducibility, and presentation quality.",
    useCase:
      "Use when you need a comprehensive review of a research paper before submission or to evaluate a paper for a journal/conference.",
    inputPlaceholder: "Paste the paper abstract or provide a brief description...",
    inputLabel: "Paper Content",
    stages: [
      {
        id: "search-related-work",
        agent: "Scholar",
        role: "researcher",
        description: "Search related work, verify citations, assess novelty against existing literature.",
        icon: <Search className="h-5 w-5" />,
        color: "bg-blue-500",
      },
      {
        id: "review-paper",
        agent: "Paper Reviewer",
        role: "reviewer",
        description:
          "Execute 7-stage pipeline: intake, structural analysis, claims, literature grounding, methodology, adversarial red team, synthesis.",
        icon: <Shield className="h-5 w-5" />,
        color: "bg-red-500",
      },
      {
        id: "refine-review",
        agent: "Academic Writer",
        role: "writer",
        description:
          "Refine review into constructive feedback. Generate response-to-authors.md with actionable suggestions.",
        icon: <FileText className="h-5 w-5" />,
        color: "bg-green-500",
      },
    ],
  },
  {
    id: "proposal-writing",
    name: "Proposal Writing Pipeline",
    description:
      "End-to-end grant proposal creation from literature review through final submission documents.",
    useCase:
      "Use when preparing an EU Horizon Europe, NSF, NIH, or ERC grant proposal from scratch.",
    inputPlaceholder: "Describe your research idea, target funder, and objectives...",
    inputLabel: "Research Idea",
    stages: [
      {
        id: "research-landscape",
        agent: "Scholar",
        role: "researcher",
        description:
          "Identify research gaps, verify novelty, find supporting literature, and assess methodology precedents.",
        icon: <Search className="h-5 w-5" />,
        color: "bg-blue-500",
      },
      {
        id: "design-methodology",
        agent: "Research Methodologist",
        role: "researcher",
        description:
          "Design experimental methodology, plan data collection, create FAIR data management plan.",
        icon: <FlaskConical className="h-5 w-5" />,
        color: "bg-purple-500",
      },
      {
        id: "write-proposal",
        agent: "Grant Writer",
        role: "writer",
        description:
          "Write proposal sections: Specific Aims, Research Plan, Budget, Biosketch. Align with evaluation criteria.",
        icon: <FileText className="h-5 w-5" />,
        color: "bg-orange-500",
      },
      {
        id: "create-artifacts",
        agent: "Project Manager",
        role: "researcher",
        description:
          "Create WBS, Gantt charts, risk register. Ensure EU compliance, IP strategy, exploitation plan.",
        icon: <Users className="h-5 w-5" />,
        color: "bg-teal-500",
      },
    ],
  },
  {
    id: "conference-prep",
    name: "Conference Preparation",
    description:
      "Prepare a complete conference submission: paper, slides, poster, and rehearsal feedback.",
    useCase:
      "Use when preparing for a conference submission including paper writing, presentation design, and practice.",
    inputPlaceholder: "Describe your research findings and target conference...",
    inputLabel: "Research Findings",
    stages: [
      {
        id: "write-paper",
        agent: "Academic Writer",
        role: "writer",
        description:
          "Write paper following IMRaD structure. Craft abstract, format for target venue (IEEE, ACM, Springer).",
        icon: <FileText className="h-5 w-5" />,
        color: "bg-green-500",
      },
      {
        id: "review-draft",
        agent: "Paper Reviewer",
        role: "reviewer",
        description:
          "Review draft for novelty, rigor, and presentation. Check claims, verify citations, assess methodology.",
        icon: <Shield className="h-5 w-5" />,
        color: "bg-red-500",
      },
      {
        id: "create-materials",
        agent: "Academic Writer",
        role: "writer",
        description:
          "Create conference slides with visual hierarchy. Design poster layout. Prepare pitch deck.",
        icon: <BookOpen className="h-5 w-5" />,
        color: "bg-green-500",
      },
    ],
  },
  {
    id: "eu-project",
    name: "EU Project Lifecycle",
    description:
      "Full EU Horizon Europe project management from proposal through periodic reporting and exploitation.",
    useCase:
      "Use when managing an EU-funded project: proposal writing, consortium coordination, deliverables, and reporting.",
    inputPlaceholder: "Describe the EU project scope, consortium, and objectives...",
    inputLabel: "Project Scope",
    stages: [
      {
        id: "write-proposal",
        agent: "Grant Writer",
        role: "writer",
        description:
          "Write EU Horizon proposal (RIA/IA/CSA). Structure Part B, budget, WP conventions.",
        icon: <FileText className="h-5 w-5" />,
        color: "bg-orange-500",
      },
      {
        id: "create-framework",
        agent: "Project Manager",
        role: "researcher",
        description:
          "Create WBS, Gantt, RACI. Track KPIs, milestones. Coordinate consortium. Handle periodic reporting.",
        icon: <Users className="h-5 w-5" />,
        color: "bg-teal-500",
      },
      {
        id: "review-deliverables",
        agent: "Paper Reviewer",
        role: "reviewer",
        description:
          "Review deliverables for quality. Ensure compliance with EU requirements. Check exploitation plans.",
        icon: <Shield className="h-5 w-5" />,
        color: "bg-red-500",
      },
    ],
  },
];

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
    if (asset?.abstract) {
      setInput(asset.abstract);
    }
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

interface WorkflowExecution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  input_text?: string;
  paper_id?: string;
  agent_assignments?: Record<string, string>;
  stages: {
    agent_role?: string;
    agent_name?: string;
    status: string;
    output: string;
    metadata?: Record<string, any>;
  }[];
  status: string;
  duration_seconds?: number;
  created_at: string;
}

function ExecutionCard({ execution, onDelete }: { execution: WorkflowExecution; onDelete?: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "--";
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString();
  };

  const statusStyle = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800";
      case "partial":
        return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border-amber-200 dark:border-amber-800";
      case "failed":
        return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300 border-red-200 dark:border-red-800";
      default:
        return "bg-muted text-muted-foreground";
    }
  };

  const stageStatusStyle = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800";
      case "in_progress":
      case "running":
        return "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-800";
      case "failed":
        return "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border-red-800";
      case "skipped":
        return "bg-muted text-muted-foreground border-border";
      default:
        return "bg-muted text-muted-foreground border-border";
    }
  };

  return (
    <Card className="overflow-hidden transition-shadow hover:shadow-md group relative">
      <CardContent className="pt-4">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-full text-left"
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-semibold text-sm">{execution.workflow_name}</h3>
                <span
                  className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${statusStyle(execution.status)}`}
                >
                  {execution.status}
                </span>
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDuration(execution.duration_seconds)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {formatTime(execution.created_at)}
                {execution.input_text &&
                  ` -- "${execution.input_text.substring(0, 80)}${execution.input_text.length > 80 ? "..." : ""}"`}
              </p>
            </div>
            <ChevronDown
              className={`h-4 w-4 text-muted-foreground shrink-0 transition-transform duration-200 ${
                expanded ? "rotate-180" : ""
              }`}
            />
          </div>
          {onDelete && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(execution.id);
              }}
              className="absolute top-3 right-3 p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors opacity-0 group-hover:opacity-100"
              title="Delete result"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </button>

        {expanded && (
          <div className="mt-4 space-y-4 border-t pt-4">
            {execution.input_text && (
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
                  Input
                </h4>
                <p className="text-sm bg-muted/50 rounded-md p-3 text-muted-foreground leading-relaxed">
                  {execution.input_text}
                </p>
              </div>
            )}

            {execution.agent_assignments &&
              Object.keys(execution.agent_assignments).length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
                    Agent Assignments
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(execution.agent_assignments).map(
                      ([stageId, configId]) => (
                        <Badge key={stageId} variant="outline" className="text-xs">
                          {stageId}: {configId.substring(0, 8)}...
                        </Badge>
                      )
                    )}
                  </div>
                </div>
              )}

            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Stages
              </h4>
              {execution.stages.map((stage, i) => (
                <div
                  key={i}
                  className="rounded-lg border bg-card p-4 space-y-3"
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    {stage.agent_role && (
                      <Badge variant="secondary" className="text-xs capitalize">
                        {stage.agent_role}
                      </Badge>
                    )}
                    {stage.agent_name && (
                      <span className="text-xs text-muted-foreground font-medium">
                        {stage.agent_name}
                      </span>
                    )}
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ml-auto ${stageStatusStyle(
                        stage.status
                      )}`}
                    >
                      {stage.status}
                    </span>
                  </div>

                  {stage.output ? (
                    <MarkdownRenderer content={stage.output} />
                  ) : (
                    <p className="text-sm text-muted-foreground italic">No output</p>
                  )}

                  {stage.metadata &&
                    Object.keys(stage.metadata).length > 0 && (
                      <details className="group">
                        <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                          Metadata
                        </summary>
                        <pre className="text-xs bg-muted rounded-md p-3 mt-2 overflow-auto max-h-[150px] leading-relaxed">
                          {JSON.stringify(stage.metadata, null, 2)}
                        </pre>
                      </details>
                    )}
                </div>
              ))}
            </div>
          </div>
        )}
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
            <Card>
              <CardContent className="py-12 text-center">
                <Clock className="h-10 w-10 text-muted-foreground/50 mx-auto mb-3" />
                <p className="text-muted-foreground">No workflow executions yet.</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Run a workflow from the Execute tab to see results here.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {sortedExecutions.length} result{sortedExecutions.length !== 1 ? "s" : ""}
                </p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  onClick={() => deleteAllMutation.mutate()}
                  disabled={deleteAllMutation.isPending}
                >
                  {deleteAllMutation.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                  )}
                  Clear All
                </Button>
              </div>
              {sortedExecutions.map((exec) => (
                <ExecutionCard
                  key={exec.id}
                  execution={exec}
                  onDelete={(id) => deleteMutation.mutate(id)}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
