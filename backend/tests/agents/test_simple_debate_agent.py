"""Unit tests for SimpleDebateAgent (Task 2).

Verifies the 2-node LangGraph:
    intake → respond → END

The intake node parses paper_content + review_content from state context
(0 LLM calls). The respond node makes 2 LLM calls using ``_invoke_with_usage``:
    - Call 1: Initial debate analysis (Paper Defense + Review Rebuttal)
    - Call 2: Synthesis (Balanced Synthesis with reflection)

Pattern reference: ``DeepReviewAgent._invoke_with_usage`` at
``app/agents/review_pipeline.py:59-72`` — reads ``usage_metadata`` directly.
"""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.base import AgentState
from app.agents.simple_debate_agent import SimpleDebateAgent


@pytest.mark.unit_db
def test_simple_debate_agent_class_exists():
    """SimpleDebateAgent is importable and has ``name == "simple-debate"``."""
    assert SimpleDebateAgent.name == "simple-debate", (
        f"Expected name='simple-debate', got {SimpleDebateAgent.name!r}"
    )


@pytest.mark.unit_db
def test_simple_debate_agent_description():
    """SimpleDebateAgent exposes a non-empty ``description`` string."""
    desc = SimpleDebateAgent.description
    assert isinstance(desc, str), f"description must be str, got {type(desc)}"
    assert len(desc) > 0, f"description must be non-empty, got {desc!r}"


@pytest.mark.unit_db
def test_simple_debate_agent_system_prompt():
    """SimpleDebateAgent exposes a non-empty ``system_prompt`` mentioning 'debate'."""
    prompt = SimpleDebateAgent.system_prompt
    assert isinstance(prompt, str), f"system_prompt must be str, got {type(prompt)}"
    assert len(prompt) > 0, "system_prompt must be non-empty"
    assert "debate" in prompt.lower(), (
        f"system_prompt should mention 'debate'; got: {prompt[:200]}"
    )


@pytest.mark.unit_db
def test_simple_debate_graph_structure(mock_llm):
    """``build_graph()`` returns a StateGraph with exactly 2 user nodes."""
    agent = SimpleDebateAgent(llm=mock_llm)
    graph = agent.build_graph()

    assert "intake" in graph.nodes, (
        f"Missing 'intake' node, got: {list(graph.nodes)}"
    )
    assert "respond" in graph.nodes, (
        f"Missing 'respond' node, got: {list(graph.nodes)}"
    )
    assert len(graph.nodes) == 2, (
        f"Expected 2 nodes, got {len(graph.nodes)}: {list(graph.nodes)}"
    )

    # Compiled graph adds __start__ and __end__ virtual nodes.
    compiled = graph.compile()
    compiled_nodes = list(compiled.get_graph().nodes.keys())
    user_nodes = [n for n in compiled_nodes if not n.startswith("__")]
    assert len(user_nodes) == 2, (
        f"Compiled graph should have 2 user nodes, got {user_nodes}"
    )


@pytest.mark.unit_db
def test_simple_debate_graph_edges(mock_llm):
    """The graph flow is ``intake → respond → END``."""
    agent = SimpleDebateAgent(llm=mock_llm)
    compiled = agent.build_graph().compile()

    user_nodes = [
        n for n in compiled.get_graph().nodes.keys()
        if not n.startswith("__")
    ]
    assert "intake" in user_nodes, "intake should be a node"
    assert "respond" in user_nodes, "respond should be a node"

    # Inspect edges. LangGraph ``Edge`` named tuples expose ``source``/``target``
    # attributes; fall back to positional indexing for plain tuples.
    edges = list(compiled.get_graph().edges)
    edge_set: set[tuple] = set()
    for e in edges:
        src = getattr(e, "source", None)
        if src is None and len(e) > 0:
            src = e[0]
        tgt = getattr(e, "target", None)
        if tgt is None and len(e) > 1:
            tgt = e[1]
        edge_set.add((src, tgt))

    assert ("intake", "respond") in edge_set, (
        f"Expected edge intake→respond, got edges: {edge_set}"
    )
    assert ("respond", "__end__") in edge_set, (
        f"Expected edge respond→__end__, got edges: {edge_set}"
    )


@pytest.mark.unit_db
@pytest.mark.asyncio
async def test_simple_debate_run_calls_llm_twice(mock_llm):
    """``SimpleDebateAgent.run()`` invokes the LLM exactly 2 times."""
    agent = SimpleDebateAgent(llm=mock_llm)
    state = AgentState(
        messages=[HumanMessage(content="Debate this paper")],
        context={"paper_content": "Paper text", "review_content": "Review text"},
        output=None,
        metadata={},
    )

    compiled = agent.build_graph().compile()
    await compiled.ainvoke(state, config={"configurable": {"thread_id": "test"}})

    assert mock_llm.ainvoke.call_count == 2, (
        f"Expected 2 LLM calls, got {mock_llm.ainvoke.call_count}"
    )


@pytest.mark.unit_db
@pytest.mark.asyncio
async def test_simple_debate_token_usage_accumulates(mock_llm):
    """Token usage from both LLM calls accumulates into ``context['_usage']``."""
    mock_llm.ainvoke.side_effect = [
        AIMessage(
            content="Initial analysis",
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        ),
        AIMessage(
            content="Synthesis",
            usage_metadata={
                "input_tokens": 200,
                "output_tokens": 80,
                "total_tokens": 280,
            },
        ),
    ]

    agent = SimpleDebateAgent(llm=mock_llm)
    state = AgentState(
        messages=[HumanMessage(content="Debate this paper")],
        context={"paper_content": "Paper text", "review_content": "Review text"},
        output=None,
        metadata={},
    )

    compiled = agent.build_graph().compile()
    final_state = await compiled.ainvoke(
        state, config={"configurable": {"thread_id": "test"}}
    )

    usage = final_state["context"].get("_usage")
    assert usage is not None, "context['_usage'] should be populated after run"
    assert usage["total_tokens"] > 0, (
        f"Expected total_tokens > 0, got {usage.get('total_tokens')}"
    )


@pytest.mark.unit_db
@pytest.mark.asyncio
async def test_simple_debate_output_format(mock_llm):
    """``state['output']`` contains Paper Defense, Review Rebuttal, Balanced Synthesis."""
    mock_llm.ainvoke.side_effect = [
        AIMessage(
            content=(
                "**Paper Defense**: The paper's strongest arguments...\n"
                "**Review Rebuttal**: However, the review overlooks..."
            ),
        ),
        AIMessage(
            content=(
                "**Paper Defense**: The paper presents valid evidence in Section 3.\n"
                "**Review Rebuttal**: The review raises valid concerns about methodology.\n"
                "**Balanced Synthesis**: Taking both perspectives into account, "
                "**Decision**: Minor Revision."
            ),
        ),
    ]

    agent = SimpleDebateAgent(llm=mock_llm)
    state = AgentState(
        messages=[HumanMessage(content="Debate this paper")],
        context={"paper_content": "Paper text", "review_content": "Review text"},
        output=None,
        metadata={},
    )

    compiled = agent.build_graph().compile()
    final_state = await compiled.ainvoke(
        state, config={"configurable": {"thread_id": "test"}}
    )

    output = final_state["output"]
    assert isinstance(output, str), f"output must be str, got {type(output)}"
    assert "Paper Defense" in output, f"Missing 'Paper Defense' in output: {output!r}"
    assert "Review Rebuttal" in output, (
        f"Missing 'Review Rebuttal' in output: {output!r}"
    )
    assert "Balanced Synthesis" in output, (
        f"Missing 'Balanced Synthesis' in output: {output!r}"
    )
