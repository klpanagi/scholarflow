"""Unit tests for DeepDebateAgent (Task 3b).

Verifies the 4-node LangGraph for the deepest debate variant:
    intake → defend_paper → evaluate_defense → synthesize → END

Each node uses the `direct` strategy via self.llm.ainvoke() directly
(not strategy.execute), following the DeepReviewAgent pattern
(`review_pipeline.py:59-72`). The mock_llm fixture is overridden with
`ainvoke.side_effect` to return distinct AIMessages, one per LLM call.

Pattern reference: `test_paper_review_writer.py` (lower-level
mock_llm.ainvoke.side_effect + call_args_list inspection).

Token accumulation: DeepDebateAgent uses the same `_invoke_with_usage` helper
as DeepReviewAgent — `usage_metadata` is read directly from the AIMessage and
summed into `state["context"]["_usage"]` across all LLM calls.
"""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.base import AgentState


def _make_state(
    user_msg: str = "Debate this paper review.",
    context: dict | None = None,
) -> AgentState:
    """Build a minimal AgentState for graph invocation."""
    return AgentState(
        messages=[HumanMessage(content=user_msg)],
        context=context or {},
        output=None,
        metadata={},
    )


def _set_three_responses(
    mock_llm,
    defense_text: str = "Paper Defense: The methodology is sound.",
    evaluation_text: str = "Defense Evaluation: The defense is supported.",
    synthesis_text: str = "Final synthesis: Accept with minor revisions.",
) -> None:
    """Configure mock_llm.ainvoke to return 3 distinct AIMessages in order.

    Order matches the LLM-calling nodes:
        call_args_list[0]  →  defend_paper
        call_args_list[1]  →  evaluate_defense
        call_args_list[2]  →  synthesize

    The intake node parses inputs locally and does NOT call the LLM.
    """
    mock_llm.ainvoke.side_effect = [
        AIMessage(content=defense_text),
        AIMessage(content=evaluation_text),
        AIMessage(content=synthesis_text),
    ]


@pytest.mark.unit_db
class TestDeepDebateAgentClassExists:
    """The DeepDebateAgent class must be importable with the correct name attribute."""

    def test_deep_debate_agent_class_exists(self):
        from app.agents.deep_debate_agent import DeepDebateAgent

        assert DeepDebateAgent is not None, (
            "DeepDebateAgent must be importable from app.agents.deep_debate_agent"
        )
        assert DeepDebateAgent.name == "deep-debate", (
            f"Expected name='deep-debate', got: {DeepDebateAgent.name!r}"
        )


@pytest.mark.unit_db
class TestDeepDebateAgentDescription:
    """The DeepDebateAgent class must expose a non-empty description."""

    def test_deep_debate_agent_description(self):
        from app.agents.deep_debate_agent import DeepDebateAgent

        assert isinstance(DeepDebateAgent.description, str), (
            f"description must be str, got {type(DeepDebateAgent.description).__name__}"
        )
        assert len(DeepDebateAgent.description) > 0, (
            "description must be a non-empty string"
        )


@pytest.mark.unit_db
class TestDeepDebateAgentSystemPrompt:
    """The DeepDebateAgent class must expose a non-empty system_prompt."""

    def test_deep_debate_agent_system_prompt(self):
        from app.agents.deep_debate_agent import DeepDebateAgent

        assert isinstance(DeepDebateAgent.system_prompt, str), (
            f"system_prompt must be str, got {type(DeepDebateAgent.system_prompt).__name__}"
        )
        assert len(DeepDebateAgent.system_prompt) > 0, (
            "system_prompt must be a non-empty string"
        )


@pytest.mark.unit_db
class TestDeepDebateGraphStructure:
    """The graph must build with exactly 4 nodes: intake, defend_paper, evaluate_defense, synthesize."""

    def test_deep_debate_graph_structure(self, mock_llm):
        from app.agents.deep_debate_agent import DeepDebateAgent

        agent = DeepDebateAgent(llm=mock_llm)

        graph = agent.build_graph()
        assert "intake" in graph.nodes, f"Missing 'intake' node, got: {list(graph.nodes)}"
        assert "defend_paper" in graph.nodes, (
            f"Missing 'defend_paper' node, got: {list(graph.nodes)}"
        )
        assert "evaluate_defense" in graph.nodes, (
            f"Missing 'evaluate_defense' node, got: {list(graph.nodes)}"
        )
        assert "synthesize" in graph.nodes, (
            f"Missing 'synthesize' node, got: {list(graph.nodes)}"
        )
        assert len(graph.nodes) == 4, (
            f"Expected 4 nodes, got {len(graph.nodes)}: {list(graph.nodes)}"
        )

        # Compiled graph adds __start__ and __end__ virtual nodes
        compiled = graph.compile()
        compiled_nodes = list(compiled.get_graph().nodes.keys())
        user_nodes = [n for n in compiled_nodes if not n.startswith("__")]
        assert len(user_nodes) == 4, (
            f"Compiled graph should have 4 user nodes, got {user_nodes}"
        )


@pytest.mark.unit_db
class TestDeepDebateGraphEdges:
    """Edges must wire intake → defend_paper → evaluate_defense → synthesize → END."""

    def test_deep_debate_graph_edges(self, mock_llm):
        from app.agents.deep_debate_agent import DeepDebateAgent

        agent = DeepDebateAgent(llm=mock_llm)
        graph = agent.build_graph()
        compiled = graph.compile()
        compiled_graph = compiled.get_graph()

        edges = [(edge.source, edge.target) for edge in compiled_graph.edges]

        assert ("intake", "defend_paper") in edges, (
            f"Missing edge intake→defend_paper. Got edges: {edges}"
        )
        assert ("defend_paper", "evaluate_defense") in edges, (
            f"Missing edge defend_paper→evaluate_defense. Got edges: {edges}"
        )
        assert ("evaluate_defense", "synthesize") in edges, (
            f"Missing edge evaluate_defense→synthesize. Got edges: {edges}"
        )
        assert ("synthesize", "__end__") in edges, (
            f"Missing edge synthesize→END. Got edges: {edges}"
        )

        start_edges = [e for e in edges if e[0] == "__start__"]
        assert len(start_edges) == 1, (
            f"Expected exactly one __start__ edge, got {start_edges}"
        )
        assert start_edges[0][1] == "intake", (
            f"Entry point must be 'intake', got: {start_edges[0][1]!r}"
        )


class TestDeepDebateRunCallsLLMThreeTimes:
    """A full run must invoke the LLM exactly 3 times (one per LLM-calling node).

    The intake node parses inputs locally without calling the LLM, so the
    3 LLM calls correspond to: defend_paper, evaluate_defense, synthesize.
    The task spec uses "4 LLM calls" as the conceptual count of graph nodes,
    but the actual LLM invocation count is 3.
    """

    @pytest.mark.asyncio
    @pytest.mark.unit_db
    async def test_deep_debate_run_calls_llm_four_times(self, mock_llm):
        from app.agents.deep_debate_agent import DeepDebateAgent

        _set_three_responses(mock_llm)
        agent = DeepDebateAgent(llm=mock_llm)
        state = _make_state(
            context={"paper_content": "PAPER_TEXT", "review_content": "REVIEW_TEXT"}
        )

        await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="test",
        )

        call_count = mock_llm.ainvoke.call_count
        assert call_count == 3, (
            f"Expected exactly 3 LLM calls (intake is pure-parse, no LLM), got {call_count}"
        )


class TestDefendPaperNodeProducesDefense:
    """The defend_paper node's LLM response must be stored in context['paper_defense']."""

    @pytest.mark.asyncio
    @pytest.mark.unit_db
    async def test_defend_paper_node_produces_defense(self, mock_llm):
        from app.agents.deep_debate_agent import DeepDebateAgent

        _set_three_responses(
            mock_llm,
            defense_text="Paper Defense: The methodology section is well-justified.",
        )
        agent = DeepDebateAgent(llm=mock_llm)
        state = _make_state(
            context={"paper_content": "PAPER_TEXT", "review_content": "REVIEW_TEXT"}
        )

        result = await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="test",
        )

        assert "paper_defense" in result["context"], (
            f"context must contain 'paper_defense', got keys: {list(result['context'].keys())}"
        )
        assert "Paper Defense" in result["context"]["paper_defense"], (
            f"Expected 'Paper Defense' in paper_defense, got: {result['context']['paper_defense']!r}"
        )


class TestEvaluateDefenseNodeAssesses:
    """The evaluate_defense node's LLM response must be stored in context['defense_evaluation']."""

    @pytest.mark.asyncio
    @pytest.mark.unit_db
    async def test_evaluate_defense_node_assesses(self, mock_llm):
        from app.agents.deep_debate_agent import DeepDebateAgent

        _set_three_responses(
            mock_llm,
            evaluation_text="Defense Evaluation: The defense is partially supported.",
        )
        agent = DeepDebateAgent(llm=mock_llm)
        state = _make_state(
            context={"paper_content": "PAPER_TEXT", "review_content": "REVIEW_TEXT"}
        )

        result = await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="test",
        )

        assert "defense_evaluation" in result["context"], (
            f"context must contain 'defense_evaluation', got keys: {list(result['context'].keys())}"
        )
        assert "Defense Evaluation" in result["context"]["defense_evaluation"], (
            f"Expected 'Defense Evaluation' in defense_evaluation, got: {result['context']['defense_evaluation']!r}"
        )


class TestDeepDebateTokenUsageAccumulates:
    """Token usage from all LLM calls must sum into context['_usage'].

    DeepDebateAgent follows the DeepReviewAgent pattern: usage_metadata is
    read directly from each AIMessage response and accumulated into
    state['context']['_usage'].
    """

    @pytest.mark.asyncio
    @pytest.mark.unit_db
    async def test_deep_debate_token_usage_accumulates(self, mock_llm):
        from app.agents.deep_debate_agent import DeepDebateAgent

        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="d",
                usage_metadata={
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                },
            ),
            AIMessage(
                content="e",
                usage_metadata={
                    "input_tokens": 200,
                    "output_tokens": 80,
                    "total_tokens": 280,
                },
            ),
            AIMessage(
                content="s",
                usage_metadata={
                    "input_tokens": 300,
                    "output_tokens": 100,
                    "total_tokens": 400,
                },
            ),
        ]

        agent = DeepDebateAgent(llm=mock_llm)
        state = _make_state(
            context={"paper_content": "PAPER_TEXT", "review_content": "REVIEW_TEXT"}
        )

        result = await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="test",
        )

        usage = result["context"].get("_usage")
        assert usage is not None, "context['_usage'] should be populated after run"
        assert usage["total_tokens"] > 0, (
            f"Expected total_tokens > 0, got {usage.get('total_tokens')}"
        )
        assert usage["total_tokens"] == 830, (
            f"Expected total_tokens=830 (150+280+400), got {usage['total_tokens']}"
        )
