"""Tests for the refactored ScholarAgent.search_papers node (Task 6)."""
import time
from unittest.mock import AsyncMock

import pytest

from app.agents.base import AgentState
from app.agents.scholar_agent import ScholarAgent
from app.services.academic_apis import (
    PaperResult,
    arxiv_api,
    crossref_api,
    openalex_api,
    semantic_scholar,
)
from app.utils import rate_limiters


def _make_state(context: dict | None = None) -> AgentState:
    """Build a minimal AgentState with a paper-like message."""
    from langchain_core.messages import HumanMessage

    return AgentState(
        messages=[HumanMessage(content=(
            "PAPER / INPUT:\n"
            "Title: Attention Is All You Need\n"
            "Authors: Ashish Vaswani, Noam Shazeer\n"
            "Abstract: The dominant sequence transduction models are based on "
            "complex recurrent or convolutional neural networks.\n"
            "Keywords: transformers, attention\n"
        ))],
        context=context or {},
        output=None,
        metadata={},
    )


@pytest.fixture
def scholar_agent(mock_llm):
    return ScholarAgent(llm=mock_llm)


@pytest.fixture
def fresh_arxiv_rate_limiter(mocker):
    """Replace the module-level arxiv_rate_limiter with a fresh instance per test.

    Avoids cross-test pollution of the singleton token bucket state.
    """
    from app.utils.rate_limiters import TokenBucketRateLimiter

    fresh = TokenBucketRateLimiter(rate_per_second=1 / 3, burst=1)
    mocker.patch.object(rate_limiters, "arxiv_rate_limiter", fresh)
    mocker.patch("app.agents.scholar_agent.arxiv_rate_limiter", fresh)
    return fresh


@pytest.fixture
def stub_s2_prequery(mocker):
    """Stub S2 pre-query strategies so the node never makes real network calls.

    The LLM-driven query expansion reads from self.llm.ainvoke, which mock_llm
    already provides. The S2 seed/recommendation path must be stubbed.
    """
    mocker.patch.object(
        semantic_scholar, "build_related_work", new=AsyncMock(return_value=[])
    )
    mocker.patch.object(
        semantic_scholar, "resolve_paper_id", new=AsyncMock(return_value=None)
    )
    mocker.patch.object(
        semantic_scholar, "get_recommendations", new=AsyncMock(return_value=[])
    )


class TestSearchPassesFiltersToSources:
    @pytest.mark.asyncio
    async def test_search_passes_filters_to_sources(
        self, mocker, scholar_agent, stub_s2_prequery, fresh_arxiv_rate_limiter
    ):
        s2_mock = mocker.patch.object(
            semantic_scholar, "search", new=AsyncMock(return_value=[])
        )
        arxiv_mock = mocker.patch.object(
            arxiv_api, "search", new=AsyncMock(return_value=[])
        )
        openalex_mock = mocker.patch.object(
            openalex_api, "search", new=AsyncMock(return_value=[])
        )
        crossref_mock = mocker.patch.object(
            crossref_api, "search", new=AsyncMock(return_value=[])
        )

        state = _make_state(context={
            "year": "2020-2023",
            "min_citation_count": 100,
            "venue": "NeurIPS",
        })
        await scholar_agent.search_papers(state)

        assert s2_mock.call_count > 0, "S2 should have been called"
        for call in s2_mock.call_args_list:
            assert call.kwargs.get("year") == "2020-2023", (
                f"S2 should receive year='2020-2023', got: {call.kwargs}"
            )
            assert call.kwargs.get("min_citations") == 100, (
                f"S2 should receive min_citations=100, got: {call.kwargs}"
            )
            assert call.kwargs.get("venue") == "NeurIPS", (
                f"S2 should receive venue='NeurIPS', got: {call.kwargs}"
            )

        assert openalex_mock.call_count > 0, "OpenAlex should have been called"
        for call in openalex_mock.call_args_list:
            assert call.kwargs.get("year") == "2020-2023"
            assert call.kwargs.get("min_citation_count") == 100
            assert call.kwargs.get("venue") == "NeurIPS"

        assert arxiv_mock.call_count > 0, "arXiv should have been called"
        assert crossref_mock.call_count > 0, "CrossRef should have been called"


class TestSearchHandlesSourceFailure:
    @pytest.mark.asyncio
    async def test_search_handles_source_failure(
        self, mocker, scholar_agent, stub_s2_prequery, fresh_arxiv_rate_limiter
    ):
        mocker.patch.object(
            semantic_scholar,
            "search",
            new=AsyncMock(side_effect=RuntimeError("S2 API is down")),
        )
        mocker.patch.object(arxiv_api, "search", new=AsyncMock(return_value=[]))
        mocker.patch.object(crossref_api, "search", new=AsyncMock(return_value=[]))

        five_papers = [
            PaperResult(
                external_id=f"oa_{i}",
                paper_id=f"oa_{i}",
                source="openalex",
                title=f"OpenAlex Paper {i}",
                abstract=None,
                authors=["A. Author"],
                year=2022,
                url=None,
                doi=None,
                citation_count=10 * i,
            )
            for i in range(5)
        ]
        mocker.patch.object(
            openalex_api, "search", new=AsyncMock(return_value=five_papers)
        )

        state = _make_state()
        await scholar_agent.search_papers(state)

        failed = state["context"]["search_metadata"].get("sources_failed", [])
        failed_sources = [f["source"] for f in failed]
        assert "semantic_scholar" in failed_sources, (
            f"S2 should be in sources_failed, got: {failed}"
        )
        s2_entry = next(f for f in failed if f["source"] == "semantic_scholar")
        assert "S2 API is down" in s2_entry["reason"]

        raw = state["context"]["raw_search_results"]
        oa_in_raw = [r for r in raw if r.get("source") == "openalex"]
        assert len(oa_in_raw) >= 5, (
            f"OpenAlex should contribute ≥5 papers, got: {len(oa_in_raw)}"
        )


class TestSearchIncludesMatchedInField:
    @pytest.mark.asyncio
    async def test_search_includes_matched_in_field(
        self, mocker, scholar_agent, stub_s2_prequery, fresh_arxiv_rate_limiter
    ):
        sample_papers = [
            PaperResult(
                external_id=f"s2_{i}",
                paper_id=f"s2_{i}",
                source="semantic_scholar",
                title="Attention Is All You Need",
                abstract="The dominant sequence transduction models are based on attention.",
                authors=["A. Vaswani"],
                year=2017,
                url=None,
                doi=None,
                citation_count=1000,
            )
            for i in range(3)
        ]
        mocker.patch.object(
            semantic_scholar, "search", new=AsyncMock(return_value=sample_papers)
        )
        mocker.patch.object(arxiv_api, "search", new=AsyncMock(return_value=[]))
        mocker.patch.object(openalex_api, "search", new=AsyncMock(return_value=[]))
        mocker.patch.object(crossref_api, "search", new=AsyncMock(return_value=[]))

        state = _make_state()
        await scholar_agent.search_papers(state)

        raw = state["context"]["raw_search_results"]
        assert len(raw) > 0, "Expected at least one result from S2"
        for r in raw:
            assert "matched_in" in r, f"Result missing matched_in: {r}"
            assert isinstance(r["matched_in"], list), (
                f"matched_in must be a list, got: {type(r['matched_in'])}"
            )
            assert all(isinstance(m, str) for m in r["matched_in"])
            assert len(r["matched_in"]) > 0, (
                f"matched_in must be non-empty, got: {r['matched_in']}"
            )


class TestSearchRespectsArxivRateLimit:
    @pytest.mark.asyncio
    async def test_search_respects_arxiv_rate_limit(
        self, mocker, scholar_agent, stub_s2_prequery
    ):
        """When arXiv is called multiple times, ≥3s gap is enforced between calls.

        Patches the arxiv_rate_limiter symbol into BOTH namespaces:
        - app.utils.rate_limiters (where arxiv_api.search() reads it)
        - app.agents.scholar_agent (where the refactored search_papers calls it)
        """
        from app.utils.rate_limiters import TokenBucketRateLimiter

        fresh_limiter = TokenBucketRateLimiter(rate_per_second=1 / 3, burst=1)
        mocker.patch.object(rate_limiters, "arxiv_rate_limiter", fresh_limiter)
        mocker.patch("app.agents.scholar_agent.arxiv_rate_limiter", fresh_limiter)

        call_times: list[float] = []

        async def arxiv_search_stub(query, max_results=20, start=0):
            call_times.append(time.monotonic())
            return [
                PaperResult(
                    external_id=f"ax_{len(call_times)}",
                    paper_id=f"ax_{len(call_times)}",
                    source="arxiv",
                    title=f"arXiv result for {query}",
                    abstract=None,
                    authors=[],
                    year=2023,
                    url=None,
                    doi=None,
                    citation_count=None,
                )
            ]

        mocker.patch.object(arxiv_api, "search", new=arxiv_search_stub)
        mocker.patch.object(semantic_scholar, "search", new=AsyncMock(return_value=[]))
        mocker.patch.object(openalex_api, "search", new=AsyncMock(return_value=[]))
        mocker.patch.object(crossref_api, "search", new=AsyncMock(return_value=[]))

        state = _make_state()
        await scholar_agent.search_papers(state)

        # First call gets the burst token; subsequent calls must wait ≥3s.
        assert len(call_times) >= 2, (
            f"Expected arXiv called ≥2 times, got {len(call_times)}"
        )
        for i in range(1, len(call_times)):
            gap = call_times[i] - call_times[i - 1]
            assert gap >= 2.9, (
                f"arXiv call {i} came {gap:.2f}s after call {i-1}, expected ≥3s gap"
            )
