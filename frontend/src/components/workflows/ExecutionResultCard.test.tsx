import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ExecutionResultCard } from "./ExecutionResultCard";
import {
  type WorkflowExecution,
} from "@/constants/workflows";
import { type ExecutionEvent } from "@/hooks/useWorkflowStream";

vi.mock("@/stores/auth", () => ({
  useAuthStore: {
    getState: () => ({ accessToken: "test-token" }),
  },
}));

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: new Blob([]) }),
    post: vi.fn().mockResolvedValue({ data: { id: "rev-1" } }),
  },
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

function makeExecution(overrides: Partial<WorkflowExecution> = {}): WorkflowExecution {
  return {
    id: "exec-1",
    workflow_id: "paper-review",
    workflow_name: "Paper Review Pipeline",
    input_text: "Some paper abstract",
    agent_assignments: {},
    status: "completed",
    duration_seconds: 12.4,
    created_at: new Date("2025-01-15T10:00:00Z").toISOString(),
    stages: [
      {
        agent_name: "SearchAgent",
        agent_role: "researcher",
        status: "completed",
        output: "Found 12 related papers",
        metadata: { duration_seconds: 5.2, usage: { input_tokens: 1000, output_tokens: 500, total_tokens: 1500, model: "gpt-4", cost_usd: 0.01 } },
      },
      {
        agent_name: "Paper Reviewer",
        agent_role: "reviewer",
        status: "failed",
        output: "",
        metadata: { duration_seconds: 3.1 },
      },
    ],
    ...overrides,
  };
}

function makeEvent(
  event_id: number,
  event_type: string,
  data: Record<string, unknown> = {},
): ExecutionEvent {
  return {
    event_id,
    execution_id: "exec-1",
    event_type,
    timestamp: new Date(2025, 0, 1, 0, 0, event_id).toISOString(),
    data,
  };
}

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

function expandCard() {
  fireEvent.click(screen.getByText("Paper Review Pipeline"));
}

describe("ExecutionResultCard", () => {
  it("renders static stages without events", () => {
    const execution = makeExecution();
    render(<ExecutionResultCard execution={execution} />, { wrapper: makeWrapper() });

    expandCard();

    expect(screen.getByText("SearchAgent")).toBeInTheDocument();
    expect(screen.getByText("Paper Reviewer")).toBeInTheDocument();
  });

  it("renders live timeline with events", () => {
    const execution = makeExecution();
    const events: ExecutionEvent[] = [
      makeEvent(1, "stage.started", {
        stage_id: "stage-0",
        stage_index: 0,
        agent_name: "SearchAgent",
        agent_role: "researcher",
      }),
      makeEvent(2, "node.started", {
        stage_index: 0,
        node_name: "search",
        agent_type: "SearchAgent",
      }),
      makeEvent(3, "node.completed", {
        stage_index: 0,
        node_name: "search",
        duration_ms: 1200,
        status: "completed",
      }),
      makeEvent(4, "stage.completed", {
        stage_id: "stage-0",
        stage_index: 0,
        status: "completed",
        duration_ms: 5200,
      }),
    ];

    render(
      <ExecutionResultCard execution={execution} events={events} />,
      { wrapper: makeWrapper() }
    );

    expandCard();
    fireEvent.click(screen.getByText("SearchAgent"));

    const timelineNodes = screen.getByTestId("stage-timeline-nodes");
    expect(timelineNodes).toBeInTheDocument();
    expect(within(timelineNodes).getByTestId("node-search")).toBeInTheDocument();
  });

  it("selecting a stage shows its timeline", () => {
    const execution = makeExecution();
    const events: ExecutionEvent[] = [
      makeEvent(1, "stage.started", {
        stage_index: 0,
        agent_name: "SearchAgent",
      }),
      makeEvent(2, "node.started", { stage_index: 0, node_name: "search" }),
      makeEvent(3, "node.completed", { stage_index: 0, node_name: "search", duration_ms: 800 }),
      makeEvent(4, "stage.completed", { stage_index: 0, status: "completed", duration_ms: 800 }),
      makeEvent(5, "stage.started", {
        stage_index: 1,
        agent_name: "Paper Reviewer",
      }),
      makeEvent(6, "stage.completed", { stage_index: 1, status: "failed", error: "boom" }),
    ];

    render(
      <ExecutionResultCard execution={execution} events={events} />,
      { wrapper: makeWrapper() }
    );

    expandCard();
    fireEvent.click(screen.getByText("Paper Reviewer"));

    expect(screen.getByTestId("stage-timeline-1")).toBeInTheDocument();
    expect(screen.getByTestId("stage-timeline-error")).toBeInTheDocument();
    expect(screen.getByTestId("stage-timeline-error")).toHaveTextContent("boom");
  });

  it("tool call nodes appear in timeline", () => {
    const execution = makeExecution();
    const events: ExecutionEvent[] = [
      makeEvent(1, "stage.started", { stage_index: 0, agent_name: "SearchAgent" }),
      makeEvent(2, "tool.call", { stage_index: 0, tool_name: "search_papers" }),
      makeEvent(3, "tool.complete", { stage_index: 0, tool_name: "search_papers", duration_ms: 300, status: "completed" }),
      makeEvent(4, "stage.completed", { stage_index: 0, status: "completed" }),
    ];

    render(
      <ExecutionResultCard execution={execution} events={events} />,
      { wrapper: makeWrapper() }
    );

    expandCard();
    fireEvent.click(screen.getByText("SearchAgent"));

    const nodes = screen.getByTestId("stage-timeline-nodes");
    expect(within(nodes).getByTestId("node-search_papers")).toBeInTheDocument();
  });

  it("shows strategy iterations badge", () => {
    const execution = makeExecution();
    const events: ExecutionEvent[] = [
      makeEvent(1, "stage.started", { stage_index: 0, agent_name: "SearchAgent" }),
      makeEvent(2, "strategy.iteration", { stage_index: 0, phase: "generate", iteration: 1 }),
      makeEvent(3, "strategy.iteration", { stage_index: 0, phase: "critique", iteration: 1 }),
      makeEvent(4, "strategy.iteration", { stage_index: 0, phase: "optimize", iteration: 1 }),
      makeEvent(5, "stage.completed", { stage_index: 0, status: "completed" }),
    ];

    render(
      <ExecutionResultCard execution={execution} events={events} />,
      { wrapper: makeWrapper() }
    );

    expandCard();
    fireEvent.click(screen.getByText("SearchAgent"));

    const badge = screen.getByTestId("stage-timeline-strategy-badge");
    expect(badge).toHaveTextContent("3 iterations");
  });

  it("error display on failed stage", () => {
    const execution = makeExecution({
      stages: [
        {
          agent_name: "SearchAgent",
          agent_role: "researcher",
          status: "failed",
          output: "",
          metadata: {},
        },
      ],
    });
    const events: ExecutionEvent[] = [
      makeEvent(1, "stage.started", { stage_index: 0, agent_name: "SearchAgent" }),
      makeEvent(2, "stage.completed", {
        stage_index: 0,
        status: "failed",
        error: "ConnectionTimeout: upstream API unreachable",
      }),
    ];

    render(
      <ExecutionResultCard execution={execution} events={events} />,
      { wrapper: makeWrapper() }
    );

    expandCard();
    fireEvent.click(screen.getByText("SearchAgent"));

    const error = screen.getByTestId("stage-timeline-error");
    expect(error).toBeInTheDocument();
    expect(error).toHaveTextContent("ConnectionTimeout");
  });
});
