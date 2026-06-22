"""Unit tests for DebateAgent (Task 3a).

Verifies the 3-node adversarial debate LangGraph:
    intake → debate → synthesize → END

Each node uses ``self.llm.ainvoke()`` directly (one LLM call per node), so
3 LLM calls total. The mock_llm fixture from conftest.py is configured with
``ainvoke.side_effect`` to return distinct AIMessages for each of the 3 LLM
invocations.

Pattern reference: ``review_pipeline.py`` (DeepReviewAgent uses the same
direct LLM call pattern with ``_invoke_with_usage`` for token tracking).
"""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.base import AgentState


def _make_state(
    user_msg: str = "Please debate this paper and review.",
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
    intake_text: str = "intake response",
    debate_text: str = (
        "**Paper Advocate**: defends the paper with evidence.\n"
        "**Review Advocate**: critiques the paper's methodology."
    ),
    synthesize_text: str = (
        "Points of agreement: methodology sound.\n"
        "**Final Synthesis**: Accept with Minor Revision."
    ),
) -> None:
    """Configure mock_llm.ainvoke to return 3 distinct AIMessages in order.

    The 3-node graph calls the LLM exactly 3 times (one per node), so a
    3-element side_effect list is sufficient. Tests that inspect call_args_list
    can use the same order to correlate inputs with the corresponding node:
        call_args_list[0]  →  intake
        call_args_list[1]  →  debate
        call_args_list[2]  →  synthesize
    """
    mock_llm.ainvoke.side_effect = [
        AIMessage(content=intake_text),
        AIMessage(content=debate_text),
        AIMessage(content=synthesize_text),
    ]


@pytest.mark.unit_db
class TestDebateAgentClassExists:
    """The DebateAgent class must be importable with correct metadata."""

    def test_debate_agent_class_exists(self):
        # Imported lazily so the test file itself imports cleanly even before
        # the module exists (this is the RED-phase guard).
        from app.agents.debate_agent import DebateAgent

        assert DebateAgent is not None, "DebateAgent must be importable from app.agents.debate_agent"
        assert DebateAgent.name == "debate", (
            f"Expected name='debate', got: {DebateAgent.name!r}"
        )


@pytest.mark.unit_db
class TestDebateAgentMetadata:
    """The class attributes (description, system_prompt) must be populated."""

    def test_debate_agent_description(self):
        from app.agents.debate_agent import DebateAgent

        assert isinstance(DebateAgent.description, str), (
            f"description must be a str, got {type(DebateAgent.description).__name__}"
        )
        assert len(DebateAgent.description) > 0, "description must be non-empty"

    def test_debate_agent_system_prompt(self):
        from app.agents.debate_agent import DebateAgent

        assert isinstance(DebateAgent.system_prompt, str), (
            f"system_prompt must be a str, got {type(DebateAgent.system_prompt).__name__}"
        )
        assert len(DebateAgent.system_prompt) > 0, "system_prompt must be non-empty"
        prompt_lower = DebateAgent.system_prompt.lower()
        assert "debate" in prompt_lower or "adversarial" in prompt_lower, (
            "system_prompt must mention 'debate' or 'adversarial'; got: "
            f"{DebateAgent.system_prompt[:200]!r}"
        )


@pytest.mark.unit_db
class TestDebateGraphStructure:
    """build_graph() must return a StateGraph with exactly 3 named nodes."""

    def test_debate_graph_structure(self, mock_llm):
        from app.agents.debate_agent import DebateAgent

        agent = DebateAgent(llm=mock_llm)
        graph = agent.build_graph()

        # Must have the 3 expected nodes
        assert "intake" in graph.nodes, f"Missing 'intake' node, got: {list(graph.nodes)}"
        assert "debate" in graph.nodes, f"Missing 'debate' node, got: {list(graph.nodes)}"
        assert "synthesize" in graph.nodes, (
            f"Missing 'synthesize' node, got: {list(graph.nodes)}"
        )
        # No extra user-defined nodes
        user_nodes = {n for n in graph.nodes if not n.startswith("__")}
        assert user_nodes == {"intake", "debate", "synthesize"}, (
            f"Expected exactly {{intake, debate, synthesize}}, got: {user_nodes}"
        )

        # compile() must succeed (raises if the graph is malformed)
        compiled = graph.compile()
        compiled_nodes = list(compiled.get_graph().nodes.keys())
        user_compiled = [n for n in compiled_nodes if not n.startswith("__")]
        assert len(user_compiled) == 3, (
            f"Compiled graph should have 3 user nodes, got {user_compiled}"
        )


@pytest.mark.unit_db
@pytest.mark.unit_db
class TestDebateGraphEdges:
    """Graph edges must be: intake → debate → synthesize → END."""

    def test_debate_graph_edges(self, mock_llm):
        from app.agents.debate_agent import DebateAgent

        agent = DebateAgent(llm=mock_llm)
        compiled = agent.build_graph().compile()
        langgraph = compiled.get_graph()

        # The compiled Graph object exposes edges as a list of Edge(source, target)
        # objects. Virtual __start__ and __end__ nodes bookend the user nodes.
        edges = [(e.source, e.target) for e in langgraph.edges]

        # Assert entry: __start__ → intake
        assert ("__start__", "intake") in edges, (
            f"Entry point must be 'intake' (edge from __start__ to intake). "
            f"Got edges: {edges}"
        )
        # Assert sequential flow
        assert ("intake", "debate") in edges, (
            f"Expected edge intake→debate. Got edges: {edges}"
        )
        assert ("debate", "synthesize") in edges, (
            f"Expected edge debate→synthesize. Got edges: {edges}"
        )
        assert ("synthesize", "__end__") in edges, (
            f"Expected edge synthesize→__end__. Got edges: {edges}"
        )


@pytest.mark.unit_db
class TestDebateAgentRunsThreeLLMCalls:
    """agent.run() must invoke the LLM exactly 3 times (one per node)."""

    @pytest.mark.asyncio
    async def test_debate_run_calls_llm_three_times(self, mock_llm):
        from app.agents.debate_agent import DebateAgent

        _set_three_responses(mock_llm)
        agent = DebateAgent(llm=mock_llm)
        state = _make_state(
            context={
                "paper_content": "This paper introduces a novel method.",
                "review_content": "The methodology is questionable.",
            }
        )

        result = await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="test-thread",
        )

        assert mock_llm.ainvoke.call_count == 3, (
            f"Expected 3 LLM calls (one per node), got {mock_llm.ainvoke.call_count}"
        )
        assert result is not None, "run() must return a result dict"


@pytest.mark.unit_db
class TestDebateNodeProducesProConPositions:
    """The debate node must capture Paper Advocate and Review Advocate content
    into ``state['context']['debate_positions']``."""

    @pytest.mark.asyncio
    async def test_debate_node_produces_pro_con_positions(self, mock_llm):
        from app.agents.debate_agent import DebateAgent

        debate_text = (
            "**Paper Advocate**: The paper's empirical results are robust.\n"
            "**Review Advocate**: The paper lacks comparison to recent baselines."
        )
        _set_three_responses(mock_llm, debate_text=debate_text)
        agent = DebateAgent(llm=mock_llm)
        state = _make_state(
            context={
                "paper_content": "This paper introduces a novel method.",
                "review_content": "The methodology is questionable.",
            }
        )

        result = await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="test-thread",
        )

        positions = result["context"].get("debate_positions", "")
        assert "Paper Advocate" in positions, (
            f"debate_positions must include 'Paper Advocate'; got: {positions!r}"
        )
        assert "Review Advocate" in positions, (
            f"debate_positions must include 'Review Advocate'; got: {positions!r}"
        )


@pytest.mark.unit_db
class TestDebateSynthesizeCombinesOutput:
    """The synthesize node must store its LLM output in ``state['output']``."""

    @pytest.mark.asyncio
    async def test_debate_synthesize_combines_output(self, mock_llm):
        from app.agents.debate_agent import DebateAgent

        synthesis_text = (
            "Points of agreement: methodology is reasonable.\n"
            "**Final Synthesis**: Accept with Minor Revision based on balanced debate."
        )
        _set_three_responses(mock_llm, synthesize_text=synthesis_text)
        agent = DebateAgent(llm=mock_llm)
        state = _make_state(
            context={
                "paper_content": "This paper introduces a novel method.",
                "review_content": "The methodology is questionable.",
            }
        )

        result = await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="test-thread",
        )

        output = result.get("output")
        assert output is not None, "state['output'] must be set by synthesize node"
        assert "Final Synthesis" in output, (
            f"output must contain 'Final Synthesis' from synthesize LLM call; got: {output!r}"
        )


@pytest.mark.unit_db
class TestDebateTokenUsageAccumulates:
    """Token usage from all 3 LLM calls must accumulate into context['_usage'].

    The agent uses the ``_invoke_with_usage()`` helper pattern from
    DeepReviewAgent (review_pipeline.py:59-72) which reads
    ``response.usage_metadata`` and sums input/output/total tokens.
    """

    @pytest.mark.asyncio
    async def test_token_usage_accumulates(self, mock_llm):
        from app.agents.debate_agent import DebateAgent

        # Each LLM call returns a distinct usage_metadata — total across the
        # 3 calls must sum to 1500 input / 480 output / 1980 total.
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="intake",
                usage_metadata={
                    "input_tokens": 500,
                    "output_tokens": 160,
                    "total_tokens": 660,
                },
            ),
            AIMessage(
                content="debate",
                usage_metadata={
                    "input_tokens": 500,
                    "output_tokens": 160,
                    "total_tokens": 660,
                },
            ),
            AIMessage(
                content="synthesize",
                usage_metadata={
                    "input_tokens": 500,
                    "output_tokens": 160,
                    "total_tokens": 660,
                },
            ),
        ]

        agent = DebateAgent(llm=mock_llm)
        state = _make_state(
            context={
                "paper_content": "Paper content",
                "review_content": "Review content",
            }
        )

        result = await agent.run(
            state["messages"],
            context=state["context"],
            thread_id="test-thread",
        )

        usage = result["context"].get("_usage")
        assert usage is not None, "context['_usage'] should be populated after run()"
        assert usage.get("total_tokens", 0) > 0, (
            f"_usage['total_tokens'] must be > 0; got: {usage.get('total_tokens')}"
        )
        # 3 calls × 660 tokens = 1980 total
        assert usage["total_tokens"] == 1980, (
            f"Expected total_tokens=1980 (3 × 660), got {usage['total_tokens']}"
        )
        assert usage["input_tokens"] == 1500, (
            f"Expected input_tokens=1500 (3 × 500), got {usage['input_tokens']}"
        )
        assert usage["output_tokens"] == 480, (
            f"Expected output_tokens=480 (3 × 160), got {usage['output_tokens']}"
        )
