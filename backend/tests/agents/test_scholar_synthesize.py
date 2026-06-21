"""Tests for SearchAgent.synthesize node."""
from __future__ import annotations

import math

import pytest
from langchain_core.messages import AIMessage

from app.agents.dossier import (
    Confidence,
    MethodologyEntry,
    ResearchDossier,
    ResearchGap,
)
from app.agents.search_agent import SearchAgent


def _make_state(context: dict | None = None) -> dict:
    return {
        "messages": [],
        "context": context or {},
        "output": None,
        "metadata": {"agent": "search"},
    }


def _make_paper_dict(
    paper_id: str,
    *,
    title: str = "Untitled",
    abstract: str | None = "Some abstract",
    year: int | None = 2020,
    citation_count: int = 10,
    doi: str | None = None,
    arxiv_id: str | None = None,
    venue: str | None = None,
    authors: list[str] | None = None,
    source: str = "semantic_scholar",
    url: str | None = None,
    final_rank: int = 0,
    matched_in: list[str] | None = None,
    merged_sources: list[str] | None = None,
) -> dict:
    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "authors": authors or ["Author A"],
        "year": year,
        "venue": venue,
        "citation_count": citation_count,
        "source": source,
        "url": url,
        "matched_in": matched_in or ["title"],
        "merged_sources": merged_sources or [source],
        "final_rank": final_rank,
    }


def _make_search_metadata(**overrides) -> dict:
    base = {
        "query": "test query",
        "seed_paper_id": None,
        "sources_queried": ["semantic_scholar", "arxiv"],
        "sources_succeeded": ["semantic_scholar", "arxiv"],
        "sources_failed": [],
        "total_papers_found": 10,
        "papers_after_dedup": 5,
        "execution_time_ms": 1234,
        "llm_tokens_used": 0,
        "estimated_cost_usd": 0.0,
    }
    base.update(overrides)
    return base


def _make_gap(
    concept_a: str = "alpha",
    concept_b: str = "beta",
    gap_score: float = 0.8,
    confidence: Confidence = "high",
) -> ResearchGap:
    return ResearchGap(
        concept_a=concept_a,
        concept_b=concept_b,
        gap_score=gap_score,
        supporting_papers=["p1"],
        confidence=confidence,
        description=f"Gap between {concept_a} and {concept_b}",
    )


def _make_methodology(paper_id: str = "p1") -> MethodologyEntry:
    return MethodologyEntry(
        paper_id=paper_id,
        method_name="TestMethod",
        dataset="TestDataset",
        metrics=["accuracy"],
        baseline_methods=["baseline"],
        result="95%",
        confidence="high",
    )


def _set_llm_synthesis_response(mock_llm, content: str = "## Synthesis\nSynthesized output.") -> None:
    existing = []
    if hasattr(mock_llm.ainvoke, "side_effect") and isinstance(mock_llm.ainvoke.side_effect, list):
        existing = list(mock_llm.ainvoke.side_effect)
    mock_llm.ainvoke.side_effect = existing + [AIMessage(content=content)]


@pytest.mark.asyncio
async def test_synthesize_creates_dossier(mock_llm):
    papers = [
        _make_paper_dict("p1", title="Paper One", citation_count=100, year=2023),
        _make_paper_dict("p2", title="Paper Two", citation_count=50, year=2022),
    ]
    context = {
        "deduplicated_results": papers,
        "gaps": [_make_gap()],
        "methodology_table": [_make_methodology()],
        "search_metadata": _make_search_metadata(),
        "search_results": papers,
        "search_queries": ["test query"],
        "expanded_queries": [],
        "recommendations_seed_id": None,
    }
    state = _make_state(context)
    _set_llm_synthesis_response(mock_llm)

    agent = SearchAgent(llm=mock_llm)
    state = await agent.synthesize(state)

    dossier = state["context"]["research_dossier"]
    assert isinstance(dossier, ResearchDossier)
    assert len(dossier.papers) == 2
    assert dossier.papers[0].title == "Paper One"
    assert dossier.search_metadata is not None
    assert dossier.search_metadata.query == "test query"


@pytest.mark.asyncio
async def test_synthesize_preserves_legacy_search_results(mock_llm):
    papers = [
        _make_paper_dict("p1", title="Paper One", citation_count=100, year=2023),
    ]
    context = {
        "deduplicated_results": papers,
        "gaps": [],
        "methodology_table": [],
        "search_metadata": _make_search_metadata(),
        "search_results": papers,
        "search_queries": ["test query"],
        "expanded_queries": [],
        "recommendations_seed_id": None,
    }
    state = _make_state(context)
    _set_llm_synthesis_response(mock_llm)

    agent = SearchAgent(llm=mock_llm)
    state = await agent.synthesize(state)

    search_results = state["context"]["search_results"]
    assert isinstance(search_results, list)
    assert len(search_results) >= 1
    first = search_results[0]
    assert isinstance(first, dict)
    for key in ("title", "authors", "year", "venue", "citation_count", "doi", "arxiv_id", "abstract", "source", "url"):
        assert key in first, f"Missing legacy key: {key}"


@pytest.mark.asyncio
async def test_synthesize_preserves_output_string(mock_llm):
    papers = [
        _make_paper_dict("p1", title="Paper One"),
    ]
    context = {
        "deduplicated_results": papers,
        "gaps": [],
        "methodology_table": [],
        "search_metadata": _make_search_metadata(),
        "search_results": papers,
        "search_queries": ["test query"],
        "expanded_queries": [],
        "recommendations_seed_id": None,
    }
    state = _make_state(context)
    _set_llm_synthesis_response(mock_llm, content="## Synthesis\nHere is the synthesis.")

    agent = SearchAgent(llm=mock_llm)
    state = await agent.synthesize(state)

    output = state["output"]
    assert isinstance(output, str)
    assert len(output) > 0
    assert "Synthesis" in output


@pytest.mark.asyncio
async def test_synthesize_applies_hybrid_ranking(mock_llm):
    paper_a = _make_paper_dict(
        "pa", title="Paper A", citation_count=150, year=2015, final_rank=0,
    )
    paper_b = _make_paper_dict(
        "pb", title="Paper B", citation_count=10, year=2025, final_rank=1,
    )
    paper_c = _make_paper_dict(
        "pc", title="Paper C", citation_count=80, year=2020, final_rank=2,
    )

    context = {
        "deduplicated_results": [paper_a, paper_b, paper_c],
        "gaps": [],
        "methodology_table": [],
        "search_metadata": _make_search_metadata(),
        "search_results": [paper_a, paper_b, paper_c],
        "search_queries": ["test query"],
        "expanded_queries": [],
        "recommendations_seed_id": None,
    }
    state = _make_state(context)
    _set_llm_synthesis_response(mock_llm)

    agent = SearchAgent(llm=mock_llm)
    state = await agent.synthesize(state)

    dossier = state["context"]["research_dossier"]
    assert isinstance(dossier, ResearchDossier)
    assert len(dossier.papers) == 3

    ranks = [p.final_rank for p in dossier.papers]
    assert ranks == [0, 1, 2], f"Expected ranks [0, 1, 2], got {ranks}"

    def _score(relevance: float, cite_count: int, year: int | None) -> float:
        cite_norm = min(cite_count / 100, 1.0)
        recency = math.exp(-0.1 * (2026 - year)) if year is not None else 0.0
        return 0.50 * relevance + 0.30 * cite_norm + 0.20 * recency

    n = 3
    scores = []
    for i, (title, cite, yr) in enumerate([
        ("Paper A", 150, 2015),
        ("Paper B", 10, 2025),
        ("Paper C", 80, 2020),
    ]):
        relevance = 1.0 - (i / max(n - 1, 1))
        s = _score(relevance, cite, yr)
        scores.append((title, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    expected_order = [s[0] for s in scores]
    actual_order = [p.title for p in dossier.papers]

    assert actual_order == expected_order, (
        f"Expected order {expected_order}, got {actual_order}. "
        f"Scores: {scores}"
    )
