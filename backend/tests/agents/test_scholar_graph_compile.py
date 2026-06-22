"""Regression tests for SearchAgent graph compilation and execution.

Verifies the 5-node linear chain can be built and compiled, that the
topology remains a simple chain (no diamond / duplicate edges), and that
end-to-end execution populates ``methodology_table`` and ``gaps``.

These tests catch the original bug (``ValueError: Already found path for
node 'deduplicate'``) if it is ever reintroduced.
"""

from __future__ import annotations

from collections import Counter
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit_db

from langchain_core.messages import AIMessage

from app.agents.base import AgentState
from app.agents.dossier import MethodologyEntry, ResearchGap
from app.agents.search_agent import SearchAgent


async def _mock_search_papers(state: AgentState) -> AgentState:
    """Populate ``raw_search_results`` without real API calls."""
    state["context"]["raw_search_results"] = [
        {
            "paper_id": "p1",
            "title": "Attention Is All You Need",
            "doi": "10.48550/arXiv.1706.03762",
            "arxiv_id": None,
            "authors": ["Vaswani et al."],
            "year": 2017,
            "venue": "NeurIPS",
            "citation_count": 95000,
            "abstract": "We propose a new network architecture, the Transformer.",
            "source": "semantic_scholar",
            "url": None,
            "external_id": "abc",
            "primary_source": "semantic_scholar",
            "matched_in": ["title"],
            "merged_sources": ["semantic_scholar"],
            "final_rank": 0,
        },
        {
            "paper_id": "p2",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "doi": "10.48550/arXiv.1810.04805",
            "arxiv_id": None,
            "authors": ["Devlin et al."],
            "year": 2019,
            "venue": "NAACL",
            "citation_count": 75000,
            "abstract": "We introduce BERT for language understanding.",
            "source": "semantic_scholar",
            "url": None,
            "external_id": "def",
            "primary_source": "semantic_scholar",
            "matched_in": ["title"],
            "merged_sources": ["semantic_scholar"],
            "final_rank": 1,
        },
    ]
    state["context"]["search_metadata"] = {
        "sources_failed": [],
        "total_fetched": 2,
    }
    state["context"]["search_queries"] = ["transformer models"]
    return state


async def _mock_deduplicate(state: AgentState) -> AgentState:
    """Copy raw results to ``deduplicated_results``."""
    state["context"]["deduplicated_results"] = state["context"]["raw_search_results"]
    state["context"]["deduplication_log"] = []
    return state


async def _mock_evaluate_methods(state: AgentState) -> AgentState:
    """Populate ``methodology_table`` directly."""
    state["context"]["methodology_table"] = [
        MethodologyEntry(
            paper_id="p1",
            method_name="Transformer",
            dataset="WMT 2014 EN-DE",
            metrics=["BLEU"],
            baseline_methods=["LSTM"],
            result="BLEU 41.8",
            confidence="high",
        ),
    ]
    return state


async def _mock_identify_gaps(state: AgentState) -> AgentState:
    """Populate ``gaps`` directly."""
    state["context"]["gaps"] = [
        ResearchGap(
            concept_a="Attention",
            concept_b="Efficiency",
            description=("Research gap between attention mechanisms and efficiency."),
            gap_score=0.85,
            confidence="high",
            supporting_papers=["p1"],
        ),
    ]
    return state


def test_graph_compiles_without_error(mock_llm):
    """Building and compiling the graph must not raise (regression for duplicate-edge bug)."""
    agent = SearchAgent(llm=mock_llm)
    graph = agent.build_graph()
    compiled = graph.compile()
    assert compiled is not None


def test_compiled_graph_has_five_user_nodes(mock_llm):
    """The compiled graph must contain exactly 5 user-defined nodes."""
    agent = SearchAgent(llm=mock_llm)
    compiled = agent.build_graph().compile()
    node_names = [
        n for n in compiled.get_graph().nodes.keys() if not n.startswith("__")
    ]
    expected = {
        "search_papers",
        "deduplicate",
        "evaluate_methods",
        "identify_gaps",
        "synthesize",
    }
    assert set(node_names) == expected, (
        f"Expected {sorted(expected)}, got {sorted(node_names)}"
    )
    assert len(node_names) == len(expected), (
        f"Expected {len(expected)} user nodes, got {len(node_names)}"
    )


def test_sequential_topology(mock_llm):
    """The graph must be a simple chain — no node may have >1 outgoing edge."""
    agent = SearchAgent(llm=mock_llm)
    graph = agent.build_graph()

    outgoing = Counter(src for src, _ in graph.edges if not src.startswith("__"))
    user_nodes = (
        "search_papers",
        "deduplicate",
        "evaluate_methods",
        "identify_gaps",
        "synthesize",
    )
    for node in user_nodes:
        assert outgoing[node] == 1, (
            f"Node {node!r} has {outgoing[node]} outgoing edge(s); "
            f"expected exactly 1 for a chain topology"
        )

    chain = list(user_nodes)
    for i in range(len(chain) - 1):
        assert (chain[i], chain[i + 1]) in graph.edges, (
            f"Missing edge ({chain[i]!r} -> {chain[i + 1]!r})"
        )


@pytest.mark.asyncio
async def test_end_to_end_ainvoke_populates_methodology_and_gaps(mock_llm):
    """Full graph ainvoke must populate methodology_table and gaps in final state."""
    agent = SearchAgent(llm=mock_llm)

    agent.search_papers = _mock_search_papers
    agent.deduplicate = _mock_deduplicate
    agent.evaluate_methods = _mock_evaluate_methods
    agent.identify_gaps = _mock_identify_gaps

    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Synthesis complete."))

    compiled = agent.build_graph().compile()

    initial = AgentState(
        messages=[],
        context={},
        output=None,
        metadata={"agent": "search"},
    )

    with patch(
        "app.agents.search_agent.verify_paper_exists",
        new_callable=AsyncMock,
    ) as mock_verify:
        mock_verify.return_value = {
            "verified": True,
            "source": "mock",
            "url": None,
            "title": "Mock Paper",
        }
        result = await compiled.ainvoke(initial)

    ctx = result["context"]
    assert "methodology_table" in ctx, (
        f"Missing 'methodology_table' in final context; keys: {sorted(ctx)}"
    )
    assert len(ctx["methodology_table"]) > 0, "methodology_table is empty"
    assert "gaps" in ctx, f"Missing 'gaps' in final context; keys: {sorted(ctx)}"
    assert len(ctx["gaps"]) > 0, "gaps is empty"
    assert result["output"] is not None, "output should be populated"
