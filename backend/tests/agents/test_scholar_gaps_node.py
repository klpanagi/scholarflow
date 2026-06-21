"""Tests for the SearchAgent.identify_gaps node (Task 8).

The gaps node reads context["deduplicated_results"], builds a concept
co-occurrence matrix, identifies low-co-occurrence similar pairs, and
asks the LLM for natural-language descriptions of the top 5 candidates.
It writes context["gaps"] = list[ResearchGap].

Tests:
1. test_gaps_node_finds_low_cooccurrence_pairs — 5 papers, 1 similar pair
   in 1 paper, common pair in 5 → exactly 1 gap
2. test_gaps_node_handles_papers_without_concepts — no fields_of_study →
   fallback to regex extraction from abstract → at least 1 gap
3. test_gaps_node_caps_at_5 — many candidate pairs → output has 5
4. test_gaps_node_assigns_confidence_levels — top 5 candidates get the
   expected {high, medium, medium, low, low} distribution by rank
"""
from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage

from app.agents.dossier import ResearchGap
from app.agents.search_agent import SearchAgent


def _make_state(context: dict | None = None) -> dict:
    """Build a minimal AgentState-like dict for node testing."""
    return {
        "messages": [],
        "context": context or {},
        "output": None,
        "metadata": {"agent": "search"},
    }


def _make_paper(
    paper_id: str,
    *,
    title: str = "Untitled",
    abstract: str | None = None,
    fields_of_study: list[str] | None = None,
    final_rank: int = 0,
) -> dict:
    """Build a paper dict matching the deduplicated_results shape."""
    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "doi": None,
        "arxiv_id": None,
        "authors": [],
        "year": 2020,
        "venue": None,
        "citation_count": 0,
        "source": "semantic_scholar",
        "url": None,
        "matched_in": ["title"],
        "merged_sources": ["semantic_scholar"],
        "final_rank": final_rank,
        "fields_of_study": fields_of_study,
    }


def _set_llm_responses(mock_llm, payloads: list[str]) -> None:
    """Configure mock_llm.ainvoke to return successive AIMessage responses."""
    responses = [AIMessage(content=p) for p in payloads]
    mock_llm.ainvoke.side_effect = responses


def _gap_descriptions_json(n: int) -> str:
    """Return a JSON object with keys '1'..'n' and stub descriptions."""
    return json.dumps({str(i + 1): f"Gap description {i + 1}" for i in range(n)})


@pytest.mark.asyncio
async def test_gaps_node_finds_low_cooccurrence_pairs(mock_llm):
    """Low-co-occurrence similar concept pair surfaces as a single gap.

    5 papers share [topic_alpha,topic_beta] (pair weight 5); the 1st also
    has the substring-similar [neural_net,neural_network] (pair weight 1).
    The 5th percentile of [1,1,1,1,1,5] is 1.0, so the 5 weight-1 pairs
    qualify the weight filter, and only the substring-similar pair passes
    the similarity filter → 1 gap.
    """
    agent = SearchAgent(llm=mock_llm)
    common = ["topic_alpha", "topic_beta"]
    papers = [
        _make_paper(f"p{i}", title=f"Paper {i}", fields_of_study=list(common))
        for i in range(5)
    ]
    papers[0]["fields_of_study"] = ["topic_alpha", "topic_beta", "neural_net", "neural_network"]
    state = _make_state(context={"deduplicated_results": papers})

    _set_llm_responses(mock_llm, [_gap_descriptions_json(1)])

    await agent.identify_gaps(state)

    gaps = state["context"].get("gaps", [])
    assert len(gaps) == 1, f"Expected 1 gap, got {len(gaps)}"
    g = gaps[0]
    assert isinstance(g, ResearchGap), f"Expected ResearchGap, got {type(g).__name__}"
    pair = {g.concept_a, g.concept_b}
    assert pair == {"neural_net", "neural_network"}, (
        f"Expected the substring-similar pair, got {pair}"
    )
    assert g.confidence in {"high", "medium", "low"}
    assert isinstance(g.description, str) and len(g.description) > 0


@pytest.mark.asyncio
async def test_gaps_node_handles_papers_without_concepts(mock_llm):
    """Papers without fields_of_study fall back to regex noun extraction.

    5 papers share an abstract containing Method/Methods, Layer/Layers,
    Model/Models. The regex extracts 9 unique capitalized nouns; three
    pairs differ by one character and pass the similarity filter.
    """
    agent = SearchAgent(llm=mock_llm)
    abstract = (
        "We propose a Method with Methods and apply Layer and Layers "
        "with Model and Models for Neural networks and Deep learning."
    )
    papers = [
        _make_paper(
            f"p{i}",
            title=f"Paper {i}",
            abstract=abstract,
            fields_of_study=None,
        )
        for i in range(5)
    ]
    state = _make_state(context={"deduplicated_results": papers})

    _set_llm_responses(mock_llm, [_gap_descriptions_json(5)])

    await agent.identify_gaps(state)

    gaps = state["context"].get("gaps", [])
    assert len(gaps) >= 1, (
        f"Expected at least 1 gap from regex extraction, got {len(gaps)}"
    )
    assert all(isinstance(g, ResearchGap) for g in gaps)
    for g in gaps:
        assert g.confidence in {"high", "medium", "low"}, (
            f"Invalid confidence: {g.confidence}"
        )
        assert isinstance(g.description, str) and len(g.description) > 0


@pytest.mark.asyncio
async def test_gaps_node_caps_at_5(mock_llm):
    """100+ candidate gaps are capped to 5; LLM is called exactly once.

    20 papers each carry 10 substring-similar concepts → 45 unique
    candidate pairs, all at weight 20, all similar. The 5-pair cap kicks
    in and the LLM is asked for descriptions exactly once.
    """
    agent = SearchAgent(llm=mock_llm)
    similar_concepts = [
        "neural_net", "neural_network",
        "graph_net", "graph_network",
        "deep_net", "deep_network",
        "transformer", "transformer_model",
        "attention", "attention_layer",
    ]
    papers = [
        _make_paper(
            f"p{i}",
            title=f"Paper {i}",
            fields_of_study=list(similar_concepts),
        )
        for i in range(20)
    ]
    state = _make_state(context={"deduplicated_results": papers})

    _set_llm_responses(mock_llm, [_gap_descriptions_json(5)])

    await agent.identify_gaps(state)

    gaps = state["context"].get("gaps", [])
    assert len(gaps) == 5, f"Expected 5 gaps (capped), got {len(gaps)}"
    assert mock_llm.ainvoke.call_count == 1, (
        f"LLM should be called exactly once, got {mock_llm.ainvoke.call_count}"
    )
    assert all(isinstance(g, ResearchGap) for g in gaps)


@pytest.mark.asyncio
async def test_gaps_node_assigns_confidence_levels(mock_llm):
    """Top-5 candidates get the {high, medium, medium, low, low} confidence distribution.

    5 papers each carry 10 concepts forming 5 substring-similar pairs,
    yielding 45 candidate pairs all at weight 5. The top 5 by weight
    become the returned gaps, with confidence assigned by rank: the
    lowest-weight candidate (rank 0) is 'high', ranks 1-2 are 'medium',
    ranks 3-4 are 'low'.
    """
    agent = SearchAgent(llm=mock_llm)
    concepts = [
        "neural_net", "neural_network",
        "graph_net", "graph_network",
        "deep_net", "deep_network",
        "transformer", "transformer_model",
        "attention", "attention_layer",
    ]
    papers = [
        _make_paper(
            f"p{i}",
            title=f"Paper {i}",
            fields_of_study=list(concepts),
        )
        for i in range(5)
    ]
    state = _make_state(context={"deduplicated_results": papers})

    _set_llm_responses(mock_llm, [_gap_descriptions_json(5)])

    await agent.identify_gaps(state)

    gaps = state["context"].get("gaps", [])
    assert len(gaps) == 5, f"Expected 5 gaps, got {len(gaps)}"

    confidences = [g.confidence for g in gaps]
    assert confidences.count("high") == 1, (
        f"Expected exactly 1 'high' confidence, got {confidences}"
    )
    assert confidences.count("medium") == 2, (
        f"Expected exactly 2 'medium' confidences, got {confidences}"
    )
    assert confidences.count("low") == 2, (
        f"Expected exactly 2 'low' confidences, got {confidences}"
    )

    expected_order = ["high", "medium", "medium", "low", "low"]
    assert confidences == expected_order, (
        f"Expected confidence order {expected_order}, got {confidences}"
    )
