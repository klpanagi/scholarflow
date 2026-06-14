import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  ArrowRight,
  BookOpen,
  ChevronDown,
  FileText,
  FlaskConical,
  Loader2,
  Play,
  Search,
  Shield,
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

interface Paper {
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

function PaperSelector({
  papers,
  selectedPaperId,
  onSelect,
}: {
  papers: Paper[];
  selectedPaperId: string | null;
  onSelect: (paper: Paper | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const selectedPaper = papers.find((p) => p.id === selectedPaperId);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
      >
        <span className="truncate">
          {selectedPaper ? selectedPaper.title : "Select an uploaded paper..."}
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
          {papers.map((paper) => (
            <button
              key={paper.id}
              type="button"
              onClick={() => {
                onSelect(paper);
                setOpen(false);
              }}
              className={`w-full text-left rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground ${
                paper.id === selectedPaperId ? "bg-accent" : ""
              }`}
            >
              <div className="font-medium">{paper.title}</div>
              {paper.authors && paper.authors.length > 0 && (
                <div className="text-xs text-muted-foreground truncate">
                  {paper.authors.slice(0, 3).join(", ")}
                  {paper.year ? ` (${paper.year})` : ""}
                </div>
              )}
            </button>
          ))}
          {papers.length === 0 && (
            <div className="px-2 py-1.5 text-sm text-muted-foreground">
              No papers uploaded yet
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
  papers,
  userConfigs,
  onExecute,
  isExecuting,
}: {
  workflow: Workflow;
  papers: Paper[];
  userConfigs: AgentConfig[];
  onExecute: (id: string, input: string, paperId?: string, assignments?: Record<string, string>) => void;
  isExecuting: boolean;
}) {
  const [input, setInput] = useState("");
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
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

  const handlePaperSelect = (paper: Paper | null) => {
    setSelectedPaperId(paper?.id || null);
    if (paper?.abstract) {
      setInput(paper.abstract);
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
    
    onExecute(workflow.id, input, selectedPaperId || undefined, assignments);
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
          <label className="text-sm font-medium">Select Paper (optional)</label>
          <PaperSelector
            papers={papers}
            selectedPaperId={selectedPaperId}
            onSelect={handlePaperSelect}
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
  const [result, setResult] = useState<any>(null);

  const { data: papersData } = useQuery({
    queryKey: ["papers"],
    queryFn: async () => {
      const { data } = await api.get("/papers/");
      return (data.items || []) as Paper[];
    },
  });
  const papers = papersData || [];

  const { data: userConfigs = [] } = useQuery<AgentConfig[]>({
    queryKey: ["agent-configs"],
    queryFn: async () => {
      const { data } = await api.get("/agents/configs");
      return data || [];
    },
  });

  const executeMutation = useMutation({
    mutationFn: async ({
      workflowId,
      input,
      paperId,
      agentAssignments,
    }: {
      workflowId: string;
      input: string;
      paperId?: string;
      agentAssignments?: Record<string, string>;
    }) => {
      const { data } = await api.post("/workflows/execute", {
        workflow_id: workflowId,
        input,
        paper_id: paperId,
        agent_assignments: agentAssignments,
      });
      return data;
    },
    onSuccess: (data) => {
      setResult(data);
      toast({ title: "Workflow completed", description: "Check the results below." });
    },
    onError: (error: any) => {
      toast({
        title: "Workflow failed",
        description: error.response?.data?.detail || "Something went wrong",
        variant: "destructive",
      });
    },
  });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Multi-Agent Workflows</h1>
        <p className="text-muted-foreground mt-2">
          Orchestrate multiple specialized agents to accomplish complex academic tasks. Each workflow
          chains agents with distinct expertise for end-to-end results.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {WORKFLOWS.map((workflow) => (
          <WorkflowCard
            key={workflow.id}
            workflow={workflow}
            papers={papers}
            userConfigs={userConfigs}
            onExecute={(id, input, paperId, assignments) =>
              executeMutation.mutate({ workflowId: id, input, paperId, agentAssignments: assignments })
            }
            isExecuting={executeMutation.isPending && executeMutation.variables?.workflowId === workflow.id}
          />
        ))}
      </div>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Workflow Result</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-muted p-4 rounded-lg overflow-auto text-sm max-h-[500px]">
              {JSON.stringify(result, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
