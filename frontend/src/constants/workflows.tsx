import {
  Search,
  Shield,
  FileText,
  FlaskConical,
  Users,
  BookOpen,
  MessageSquare,
  PenLine,
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
      "A rigorous 4-stage review process: literature search, in-depth review, structured debate, and a single self-critiqued pass that produces BOTH the Response to Authors and Response to Editor documents.",
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
        id: "paper-review-writer",
        agent: "Review Writer",
        role: "review_writer",
        description: "Produce BOTH the Response to Authors (public peer review) and Response to Editor (confidential AE note) in a single self-critiqued pass with built-in quality review.",
        icon: <PenLine className="h-5 w-5" />,
        color: "bg-emerald-500",
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

/* ── Timeline view (live SSE + historical) ─────────────── */

import type { ExecutionEvent } from "@/hooks/useWorkflowStream";
export type { ExecutionEvent } from "@/hooks/useWorkflowStream";

export interface TimelineNode {
  id: string;
  name: string;
  type: "node" | "tool_call" | "strategy_iteration";
  status: string;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
}

export interface TimelineStage {
  stageIndex: number;
  stageId: string;
  agentName: string;
  agentRole: string;
  status: string;
  durationMs?: number;
  nodes: TimelineNode[];
  strategyIterations: number;
  error?: string;
}

function safeStr(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function safeNum(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function eventStageIndex(data: Record<string, unknown>): number | undefined {
  const idx = safeNum(data.stage_index);
  if (idx !== undefined) return idx;
  const id = safeStr(data.stage_id);
  if (!id) return undefined;
  return undefined;
}

function eventStageId(data: Record<string, unknown>, fallback: string): string {
  return safeStr(data.stage_id) ?? fallback;
}

function eventStageStatus(data: Record<string, unknown>, fallback: string): string {
  return safeStr(data.status) ?? fallback;
}

function eventError(data: Record<string, unknown>): string | undefined {
  const err = safeStr(data.error);
  if (err) return err;
  return undefined;
}

/**
 * Build a per-stage timeline view.
 *
 * - When `events` is provided, the timeline is augmented with the
 *   live `node.started`/`node.completed`, `tool.call`/`tool.complete`,
 *   and `strategy.iteration` events. Tool call/complete pairs are
 *   reconciled via a pending map; orphans flush at stage end.
 * - When `events` is absent, each stage yields a single timeline
 *   entry derived from the static stage metadata (backward compat).
 */
export function buildTimelineView(
  executionStages: WorkflowExecutionStage[],
  events?: ExecutionEvent[],
): TimelineStage[] {
  const eventsByStage = new Map<number, ExecutionEvent[]>();
  const stageInfoFromEvents = new Map<
    number,
    { stageId: string; agentName: string; agentRole: string; status: string; durationMs?: number; error?: string }
  >();

  if (events && events.length > 0) {
    for (const ev of events) {
      const idx = eventStageIndex(ev.data);
      if (idx === undefined) continue;
      if (!eventsByStage.has(idx)) eventsByStage.set(idx, []);
      eventsByStage.get(idx)!.push(ev);

      const data = ev.data;
      if (ev.event_type === "stage.started" || ev.event_type === "stage.completed") {
        const existing = stageInfoFromEvents.get(idx) ?? {
          stageId: eventStageId(data, `stage-${idx}`),
          agentName: safeStr(data.agent_name) ?? "",
          agentRole: safeStr(data.agent_role) ?? "",
          status: eventStageStatus(data, "pending"),
        };
        const stageId = safeStr(data.stage_id);
        const agentName = safeStr(data.agent_name);
        const agentRole = safeStr(data.agent_role);
        if (stageId) existing.stageId = stageId;
        if (agentName) existing.agentName = agentName;
        if (agentRole) existing.agentRole = agentRole;
        const status = safeStr(data.status);
        if (status) existing.status = status;
        const dur = safeNum(data.duration_ms);
        if (dur !== undefined) existing.durationMs = dur;
        const err = eventError(data);
        if (err) existing.error = err;
        stageInfoFromEvents.set(idx, existing);
      }
    }
  }

  return executionStages.map((s, i) => {
    const meta = s.metadata as Record<string, unknown> | undefined;
    const stageId = `stage-${i}`;
    const agentName = s.agent_name ?? "";
    const agentRole = s.agent_role ?? "";
    const status = s.status;
    const durationSeconds = meta && typeof meta.duration_seconds === "number"
      ? (meta.duration_seconds as number)
      : undefined;
    const durationMs = durationSeconds !== undefined
      ? Math.round(durationSeconds * 1000)
      : undefined;

    const baseStage: TimelineStage = {
      stageIndex: i,
      stageId,
      agentName,
      agentRole,
      status,
      durationMs,
      nodes: [],
      strategyIterations: 0,
    };

    if (!events || events.length === 0) {
      baseStage.nodes.push({
        id: `stage-${i}-root`,
        name: agentName || agentRole || `Step ${i + 1}`,
        type: "node",
        status,
        durationMs,
      });
      return baseStage;
    }

    const fromEvents = stageInfoFromEvents.get(i);
    if (fromEvents) {
      baseStage.stageId = fromEvents.stageId;
      if (fromEvents.agentName) baseStage.agentName = fromEvents.agentName;
      if (fromEvents.agentRole) baseStage.agentRole = fromEvents.agentRole;
      baseStage.status = fromEvents.status || baseStage.status;
      if (fromEvents.durationMs !== undefined) baseStage.durationMs = fromEvents.durationMs;
      if (fromEvents.error) baseStage.error = fromEvents.error;
    }

    const stageEvents = eventsByStage.get(i) ?? [];
    const nodeEntries = new Map<string, TimelineNode>();
    const toolEntries = new Map<string, TimelineNode>();
    let strategyIterations = 0;

    for (const ev of stageEvents) {
      const data = ev.data;
      switch (ev.event_type) {
        case "node.started": {
          const name = safeStr(data.node_name) ?? "<unknown>";
          const id = `node:${name}`;
          const existing = nodeEntries.get(id);
          if (existing) {
            existing.startedAt = ev.timestamp;
            if (existing.status === "completed") break;
            existing.status = "running";
          } else {
            nodeEntries.set(id, {
              id,
              name,
              type: "node",
              status: "running",
              startedAt: ev.timestamp,
            });
          }
          break;
        }
        case "node.completed": {
          const name = safeStr(data.node_name) ?? "<unknown>";
          const id = `node:${name}`;
          const dur = safeNum(data.duration_ms);
          const status = safeStr(data.status) ?? "completed";
          const existing = nodeEntries.get(id);
          if (existing) {
            existing.completedAt = ev.timestamp;
            existing.status = status;
            if (dur !== undefined) existing.durationMs = dur;
          } else {
            nodeEntries.set(id, {
              id,
              name,
              type: "node",
              status,
              startedAt: ev.timestamp,
              completedAt: ev.timestamp,
              durationMs: dur,
            });
          }
          break;
        }
        case "tool.call": {
          const name = safeStr(data.tool_name) ?? "<unknown>";
          const id = `tool:${name}:${ev.event_id}`;
          const node: TimelineNode = {
            id,
            name,
            type: "tool_call",
            status: "running",
            startedAt: ev.timestamp,
          };
          toolEntries.set(name, node);
          break;
        }
        case "tool.complete": {
          const name = safeStr(data.tool_name) ?? "<unknown>";
          const dur = safeNum(data.duration_ms);
          const status = safeStr(data.status) ?? "completed";
          const pending = toolEntries.get(name);
          if (pending) {
            pending.completedAt = ev.timestamp;
            pending.status = status;
            if (dur !== undefined) pending.durationMs = dur;
          } else {
            toolEntries.set(name, {
              id: `tool:${name}:${ev.event_id}`,
              name,
              type: "tool_call",
              status,
              startedAt: ev.timestamp,
              completedAt: ev.timestamp,
              durationMs: dur,
            });
          }
          break;
        }
        case "strategy.iteration": {
          strategyIterations += 1;
          const phase = safeStr(data.phase);
          const iteration = safeNum(data.iteration);
          const label = phase
            ? `Strategy: ${phase}${iteration !== undefined ? ` #${iteration}` : ""}`
            : "Strategy iteration";
          nodeEntries.set(`strategy:${ev.event_id}`, {
            id: `strategy:${ev.event_id}`,
            name: label,
            type: "strategy_iteration",
            status: "completed",
            startedAt: ev.timestamp,
            completedAt: ev.timestamp,
          });
          break;
        }
        default:
          break;
      }
    }

    const nodes: TimelineNode[] = [
      ...Array.from(nodeEntries.values()),
      ...Array.from(toolEntries.values()),
    ];

    baseStage.nodes = nodes;
    baseStage.strategyIterations = strategyIterations;
    return baseStage;
  });
}
