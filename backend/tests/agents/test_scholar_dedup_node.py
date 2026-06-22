"""Tests for the SearchAgent deduplicate node (Task 7)."""

import pytest

pytestmark = pytest.mark.unit_db

from app.agents.search_agent import SearchAgent


def _make_state(raw_results: list[dict]) -> dict:
    """Build a minimal AgentState-like dict for node testing."""
    return {
        "messages": [],
        "context": {
            "raw_search_results": raw_results,
            "search_metadata": {
                "sources_failed": [],
            },
        },
        "output": None,
        "metadata": {"agent": "search"},
    }


# 5 raw results: paper 4 = DOI-dup of paper 1, paper 5 = arXiv-dup of paper 2 → 3 unique
_RAW_RESULTS = [
    {
        "title": "Attention Is All You Need",
        "doi": "10.48550/arXiv.1706.03762",
        "arxiv_id": "1706.03762",
        "source": "semantic_scholar",
        "citation_count": 95000,
        "abstract": "The dominant sequence transduction models.",
        "authors": ["Ashish Vaswani"],
        "year": 2017,
        "url": "https://arxiv.org/abs/1706.03762",
        "matched_in": ["title"],
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "doi": None,
        "arxiv_id": "1810.04805",
        "source": "arxiv",
        "citation_count": 70000,
        "abstract": "We introduce a new language representation model.",
        "authors": ["Jacob Devlin"],
        "year": 2019,
        "url": "https://arxiv.org/abs/1810.04805",
        "matched_in": ["title"],
    },
    {
        "title": "Language Models are Few-Shot Learners",
        "doi": "10.48550/arXiv.2005.14165",
        "arxiv_id": "2005.14165",
        "source": "semantic_scholar",
        "citation_count": 40000,
        "abstract": "Recent work has demonstrated substantial gains.",
        "authors": ["Tom Brown"],
        "year": 2020,
        "url": "https://arxiv.org/abs/2005.14165",
        "matched_in": ["title"],
    },
    {
        "title": "Attention Is All You Need",
        "doi": "10.48550/arXiv.1706.03762",
        "arxiv_id": "1706.03762",
        "source": "openalex",
        "citation_count": 95000,
        "abstract": "The dominant sequence transduction models.",
        "authors": ["Ashish Vaswani"],
        "year": 2017,
        "url": "https://arxiv.org/abs/1706.03762",
        "matched_in": ["title"],
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "doi": None,
        "arxiv_id": "1810.04805",
        "source": "openalex",
        "citation_count": 70000,
        "abstract": "We introduce a new language representation model.",
        "authors": ["Jacob Devlin"],
        "year": 2019,
        "url": "https://arxiv.org/abs/1810.04805",
        "matched_in": ["title"],
    },
]


@pytest.mark.asyncio
async def test_dedup_node_reduces_duplicates():
    """5 raw results with 2 sharing the same DOI → 3 unique papers after dedup."""
    agent = SearchAgent.__new__(SearchAgent)
    state = _make_state(_RAW_RESULTS)

    result = await agent.deduplicate(state)

    deduped = result["context"]["deduplicated_results"]
    assert len(deduped) == 3, f"Expected 3 unique papers, got {len(deduped)}"

    # The merged "Attention" paper should track both sources
    attention = next(p for p in deduped if "Attention" in p["title"])
    assert "semantic_scholar" in attention["merged_sources"]
    assert "openalex" in attention["merged_sources"]


@pytest.mark.asyncio
async def test_dedup_node_populates_search_metadata():
    """papers_after_dedup in search_metadata must equal len(deduplicated_results)."""
    agent = SearchAgent.__new__(SearchAgent)
    state = _make_state(_RAW_RESULTS)

    result = await agent.deduplicate(state)

    meta = result["context"]["search_metadata"]
    deduped = result["context"]["deduplicated_results"]
    assert meta["papers_after_dedup"] == len(deduped)
    assert meta["papers_after_dedup"] == 3
