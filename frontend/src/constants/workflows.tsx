import {
  Search,
  Shield,
  FileText,
  FlaskConical,
  Users,
  BookOpen,
  MessageSquare,
} from "lucide-react";

export interface WorkflowStage {
  id: string;
  agent: string;
  role: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  useCase: string;
  stages: WorkflowStage[];
  inputPlaceholder: string;
  inputLabel: string;
}

export interface StageUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  model: string;
  cost_usd: number;
}

export interface RubricCriterion {
  name: string;
  weight: number;
  score: number;
  justification: string;
}

export interface ManuscriptRating {
  overall_score: number;
  confidence: "high" | "medium" | "low";
  confidence_reason?: string;
  rubric_standard: string;
  criteria: RubricCriterion[];
  scoring_notes?: string;
}

export interface WorkflowExecutionStage {
  agent_role?: string;
  agent_name?: string;
  status: string;
  output: string;
  rating?: ManuscriptRating;
  metadata?: Record<string, any> & {
    usage?: StageUsage;
    duration_seconds?: number;
  };
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  input_text?: string;
  paper_id?: string;
  agent_assignments?: Record<string, string>;
  stages: WorkflowExecutionStage[];
  status: string;
  duration_seconds?: number;
  created_at: string;
}

export const WORKFLOWS: Workflow[] = [
  {
    id: "paper-review",
    name: "Paper Review Pipeline",
    description:
      "A rigorous 4-stage review process: literature search, in-depth review, structured debate between paper and review, and final polished peer review document.",
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
        id: "debate-review",
        agent: "Debate Agent",
        role: "debater",
        description:
          "Run a structured debate: defend the paper against criticisms, evaluate each defense, and produce a balanced synthesis with final recommendation.",
        icon: <MessageSquare className="h-5 w-5" />,
        color: "bg-amber-500",
      },
      {
        id: "refine-review",
        agent: "Paper Review Writer",
        role: "writer",
        description:
          "Produce the final polished peer review document with reviewer summary, related work analysis, and response to authors with recommendation.",
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
        role: "manager",
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
        role: "manager",
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
        role: "manager",
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
  {
    id: "review-debate",
    name: "Review Debate",
    description:
      "Debate a paper review: defend the paper against criticisms, evaluate defenses, and synthesize a balanced verdict.",
    useCase:
      "Use when you have a paper and a review, and want to systematically debate the review's criticisms before deciding on revisions.",
    inputPlaceholder: "Paste the paper content or provide a paper ID...",
    inputLabel: "Paper & Review",
    stages: [
      {
        id: "defend-paper",
        agent: "Debater",
        role: "debater",
        description:
          "Defend the paper against each criticism with evidence from the paper.",
        icon: <Shield className="h-5 w-5" />,
        color: "bg-blue-500",
      },
      {
        id: "defend-review",
        agent: "Debater",
        role: "debater",
        description:
          "Evaluate whether each defense is substantiated by the paper's evidence.",
        icon: <MessageSquare className="h-5 w-5" />,
        color: "bg-amber-500",
      },
      {
        id: "synthesize-debate",
        agent: "Debater",
        role: "debater",
        description:
          "Neutral synthesis of both positions into a balanced final recommendation.",
        icon: <FileText className="h-5 w-5" />,
        color: "bg-green-500",
      },
    ],
  },
];

export interface StageMeta {
  icon: React.ReactNode;
  color: string;
  description: string;
}

const defaultMeta: StageMeta = {
  icon: <FileText className="h-5 w-5" />,
  color: "bg-slate-500",
  description: "",
};

export function getStageMetaByIndex(workflowId: string, index: number): StageMeta {
  const workflow = WORKFLOWS.find((w) => w.id === workflowId);
  if (!workflow) return defaultMeta;
  const stage = workflow.stages[index];
  if (!stage) return defaultMeta;
  return { icon: stage.icon, color: stage.color, description: stage.description };
}
