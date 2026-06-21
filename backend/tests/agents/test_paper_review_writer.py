"""Unit tests for PaperReviewWriterAgent (Task 10).

Verifies the 3-node self-critiquing LangGraph:
    draft → self_review → finalize → END

Each node uses the `direct` strategy (3 LLM calls total). The mock_llm fixture
from conftest.py is overridden with `ainvoke.side_effect` to return distinct
AIMessages for each of the 3 LLM invocations.

Pattern reference: `test_paper_review_with_dossier.py` (capturing_execute on
agent.strategy.execute). Here we use the lower-level mock_llm.ainvoke.side_effect
+ call_args_list inspection pattern because we need to verify both (a) the
content of each LLM call's input messages and (b) the flow of state between
the 3 nodes.
"""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.base import AgentState
from app.agents.paper_review_writer_agent import PaperReviewWriterAgent
from app.agents.strategies import DirectStrategy


def _make_state(
    user_msg: str = "Please review this paper on transformers.",
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
    draft_text: str = "draft text",
    critique_text: str = "critique text",
    final_text: str = (
        "## Response to Authors\nPublic response.\n\n"
        "## Response to Editor\nConfidential response."
    ),
) -> None:
    """Configure mock_llm.ainvoke to return 3 distinct AIMessages in order.

    The 3-node graph calls the LLM exactly 3 times (one per node), so a
    3-element side_effect list is sufficient. Tests that inspect call_args_list
    can use the same order to correlate inputs with the corresponding node:
        call_args_list[0]  →  draft
        call_args_list[1]  →  self_review
        call_args_list[2]  →  finalize
    """
    mock_llm.ainvoke.side_effect = [
        AIMessage(content=draft_text),
        AIMessage(content=critique_text),
        AIMessage(content=final_text),
    ]


class TestThreeNodeGraphCompiles:
    """The graph must build and compile with exactly 3 user-defined nodes."""

    def test_three_node_graph_compiles(self, mock_llm):
        agent = PaperReviewWriterAgent(llm=mock_llm)

        # build_graph() returns a StateGraph with exactly 3 nodes
        graph = agent.build_graph()
        assert "draft" in graph.nodes, f"Missing 'draft' node, got: {list(graph.nodes)}"
        assert "self_review" in graph.nodes, (
            f"Missing 'self_review' node, got: {list(graph.nodes)}"
        )
        assert "finalize" in graph.nodes, (
            f"Missing 'finalize' node, got: {list(graph.nodes)}"
        )
        assert len(graph.nodes) == 3, (
            f"Expected 3 nodes, got {len(graph.nodes)}: {list(graph.nodes)}"
        )

        # compile() must succeed (raises if the graph is malformed)
        compiled = graph.compile()
        compiled_nodes = list(compiled.get_graph().nodes.keys())
        # Compiled graph adds __start__ and __end__ virtual nodes
        user_nodes = [n for n in compiled_nodes if not n.startswith("__")]
        assert len(user_nodes) == 3, (
            f"Compiled graph should have 3 user nodes, got {user_nodes}"
        )


class TestDraftNodeProducesInitialDraft:
    """The draft node must write the first LLM response into state['context']['draft']."""

    @pytest.mark.asyncio
    async def test_draft_node_produces_initial_draft(self, mock_llm):
        _set_three_responses(mock_llm, draft_text="draft text")
        agent = PaperReviewWriterAgent(llm=mock_llm)
        state = _make_state()

        compiled = agent.build_graph().compile()
        final_state = await compiled.ainvoke(
            state, config={"configurable": {"thread_id": "test"}}
        )

        # The first LLM response must land in context["draft"]
        assert final_state["context"]["draft"] == "draft text", (
            f"Expected draft=='draft text', got: {final_state['context'].get('draft')!r}"
        )
        # The third LLM response must land in state["output"]
        assert "## Response to Authors" in final_state["output"]
        assert "## Response to Editor" in final_state["output"]
        # The LLM was called exactly 3 times (once per node)
        assert mock_llm.ainvoke.call_count == 3, (
            f"Expected 3 LLM calls (one per node), got {mock_llm.ainvoke.call_count}"
        )


class TestSelfReviewIncludesDraft:
    """The self_review node's prompt must reference the draft content."""

    @pytest.mark.asyncio
    async def test_self_review_node_includes_draft_in_prompt(self, mock_llm):
        _set_three_responses(
            mock_llm, draft_text="UNIQUE_DRAFT_MARKER_12345"
        )
        agent = PaperReviewWriterAgent(llm=mock_llm)
        state = _make_state()

        compiled = agent.build_graph().compile()
        await compiled.ainvoke(
            state, config={"configurable": {"thread_id": "test"}}
        )

        assert mock_llm.ainvoke.call_count == 3, (
            f"Expected 3 LLM calls, got {mock_llm.ainvoke.call_count}"
        )
        # The 2nd call (self_review) must include the draft text in its prompt.
        # call_args[0] is the positional args tuple: (messages_list,).
        # messages_list is [SystemMessage, HumanMessage] — the HumanMessage
        # content is the full self_review prompt including the draft.
        second_call = mock_llm.ainvoke.call_args_list[1]
        messages_list = second_call.args[0]
        human_msg = messages_list[-1]  # last message is the HumanMessage
        assert isinstance(human_msg, HumanMessage), (
            f"Expected HumanMessage as last message, got {type(human_msg)}"
        )
        assert "UNIQUE_DRAFT_MARKER_12345" in human_msg.content, (
            f"self_review prompt should include draft content; got: {human_msg.content[:200]}"
        )


class TestFinalizeIncludesDraftAndCritique:
    """The finalize node's prompt must include BOTH the draft and the critique."""

    @pytest.mark.asyncio
    async def test_finalize_node_includes_draft_and_critique(self, mock_llm):
        _set_three_responses(
            mock_llm,
            draft_text="DRAFT_MARKER_AAA",
            critique_text="CRITIQUE_MARKER_BBB",
        )
        agent = PaperReviewWriterAgent(llm=mock_llm)
        state = _make_state()

        compiled = agent.build_graph().compile()
        await compiled.ainvoke(
            state, config={"configurable": {"thread_id": "test"}}
        )

        assert mock_llm.ainvoke.call_count == 3
        # The 3rd call (finalize) must include BOTH the draft and the critique
        third_call = mock_llm.ainvoke.call_args_list[2]
        messages_list = third_call.args[0]
        human_msg = messages_list[-1]
        prompt = human_msg.content
        assert "DRAFT_MARKER_AAA" in prompt, (
            f"finalize prompt missing draft marker; got: {prompt[:300]}"
        )
        assert "CRITIQUE_MARKER_BBB" in prompt, (
            f"finalize prompt missing critique marker; got: {prompt[:300]}"
        )
        # The prompt also retains the original user input
        assert "Please review this paper" in prompt, (
            f"finalize prompt missing original input; got: {prompt[:300]}"
        )


class TestOutputContainsBothSectionHeadings:
    """The final state['output'] must contain both H2 section headings."""

    @pytest.mark.asyncio
    async def test_output_contains_both_section_headings(self, mock_llm):
        _set_three_responses(mock_llm)
        agent = PaperReviewWriterAgent(llm=mock_llm)
        state = _make_state()

        compiled = agent.build_graph().compile()
        final_state = await compiled.ainvoke(
            state, config={"configurable": {"thread_id": "test"}}
        )

        output = final_state["output"]
        assert isinstance(output, str), f"output must be str, got {type(output)}"
        # Case-insensitive substring match (the agent's validation also does this)
        output_lower = output.lower()
        assert "## response to authors" in output_lower, (
            f"Missing '## Response to Authors' heading in output: {output!r}"
        )
        assert "## response to editor" in output_lower, (
            f"Missing '## Response to Editor' heading in output: {output!r}"
        )


class TestUsesDirectStrategy:
    """The agent must be configured with the DirectStrategy (one LLM call per node)."""

    def test_uses_direct_strategy(self, mock_llm):
        agent = PaperReviewWriterAgent(llm=mock_llm)
        assert isinstance(agent.strategy, DirectStrategy), (
            f"Expected DirectStrategy, got {type(agent.strategy).__name__}"
        )


class TestTokenUsageAccumulatedAcrossNodes:
    """Token usage from all 3 LLM calls must be summed into context['_usage'].

    DirectStrategy reads AIMessage.usage_metadata and stores it in
    response.additional_kwargs["usage"]. _accumulate_usage then sums these
    dicts across all 3 node invocations.
    """

    @pytest.mark.asyncio
    async def test_token_usage_accumulated_across_nodes(self, mock_llm):
        # usage_metadata flows: mock_llm → DirectStrategy._extract_usage →
        # response.additional_kwargs["usage"] → _accumulate_usage
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
                content="c",
                usage_metadata={
                    "input_tokens": 200,
                    "output_tokens": 80,
                    "total_tokens": 280,
                },
            ),
            AIMessage(
                content="f",
                usage_metadata={
                    "input_tokens": 300,
                    "output_tokens": 100,
                    "total_tokens": 400,
                },
            ),
        ]

        agent = PaperReviewWriterAgent(llm=mock_llm)
        state = _make_state()

        compiled = agent.build_graph().compile()
        final_state = await compiled.ainvoke(
            state, config={"configurable": {"thread_id": "test"}}
        )

        usage = final_state["context"].get("_usage")
        assert usage is not None, "context['_usage'] should be populated after run"
        assert usage["input_tokens"] == 600, (
            f"Expected input_tokens=600 (100+200+300), got {usage['input_tokens']}"
        )
        assert usage["output_tokens"] == 230, (
            f"Expected output_tokens=230 (50+80+100), got {usage['output_tokens']}"
        )
        assert usage["total_tokens"] == 830, (
            f"Expected total_tokens=830 (150+280+400), got {usage['total_tokens']}"
        )


class TestHandlesMissingSectionsInDraft:
    """If the draft is missing a required section, the self_review prompt must mention it.

    The self_review prompt template explicitly lists both required H2 headings
    ('## Response to Authors' and '## Response to Editor') as a checklist item
    ("Section completeness"). This test verifies that the prompt surfaces the
    missing section name so the LLM can flag it.
    """

    @pytest.mark.asyncio
    async def test_handles_missing_sections_in_draft(self, mock_llm):
        # Draft intentionally omits the '## Response to Editor' section
        partial_draft = "## Response to Authors\nOnly the public-facing part is present."
        _set_three_responses(mock_llm, draft_text=partial_draft)
        agent = PaperReviewWriterAgent(llm=mock_llm)
        state = _make_state()

        compiled = agent.build_graph().compile()
        await compiled.ainvoke(
            state, config={"configurable": {"thread_id": "test"}}
        )

        assert mock_llm.ainvoke.call_count == 3
        # self_review prompt must mention the missing section
        second_call = mock_llm.ainvoke.call_args_list[1]
        messages_list = second_call.args[0]
        human_msg = messages_list[-1]
        prompt = human_msg.content
        assert "## Response to Editor" in prompt, (
            f"self_review prompt should mention the missing '## Response to Editor' "
            f"section; got prompt start: {prompt[:200]}"
        )
        assert "## Response to Authors" in prompt, (
            f"self_review prompt should also mention '## Response to Authors'; "
            f"got prompt start: {prompt[:200]}"
        )
        # The prompt must also include the actual draft content so the LLM
        # can see what's there (and what's missing).
        assert "Only the public-facing part is present." in prompt, (
            f"self_review prompt should include draft text; got: {prompt[:300]}"
        )
