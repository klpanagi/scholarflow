"""pytest fixtures for academic-pal backend tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import respx
from httpx import Response
from langchain_core.messages import AIMessage

from app.services.academic_apis import PaperResult


@pytest.fixture
def mock_llm():
    """Return a MagicMock with ainvoke() returning a fixed AIMessage response."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value=AIMessage(content="Mocked synthesis response"))
    return mock


@pytest.fixture
def mock_paper_results():
    """Return 5 PaperResult fixtures with DOI variants, arXiv variants, and exact duplicates."""
    return [
        # Paper 1: has DOI only
        PaperResult(
            external_id="s2_doi_only",
            paper_id="s2_doi_only",
            source="semantic_scholar",
            title="Attention Is All You Need",
            abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
            year=2017,
            url="https://arxiv.org/abs/1706.03762",
            doi="10.48550/arXiv.1706.03762",
            citation_count=95000,
        ),
        # Paper 2: has arXiv ID only (no DOI)
        PaperResult(
            external_id="s2_arxiv_only",
            paper_id="s2_arxiv_only",
            source="arxiv",
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            abstract="We introduce a new language representation model called BERT.",
            authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
            year=2019,
            url="https://arxiv.org/abs/1810.04805",
            doi=None,
            citation_count=70000,
        ),
        # Paper 3: has both DOI and arXiv ID
        PaperResult(
            external_id="s2_both_ids",
            paper_id="s2_both_ids",
            source="semantic_scholar",
            title="Language Models are Few-Shot Learners",
            abstract="Recent work has demonstrated substantial gains on many NLP tasks.",
            authors=["Tom Brown", "Benjamin Mann", "Nick Ryder"],
            year=2020,
            url="https://arxiv.org/abs/2005.14165",
            doi="10.48550/arXiv.2005.14165",
            citation_count=40000,
        ),
        # Paper 4: exact duplicate of Paper 1 (same external_id, title, DOI)
        PaperResult(
            external_id="s2_doi_only",
            paper_id="s2_doi_only",
            source="semantic_scholar",
            title="Attention Is All You Need",
            abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
            year=2017,
            url="https://arxiv.org/abs/1706.03762",
            doi="10.48550/arXiv.1706.03762",
            citation_count=95000,
        ),
        # Paper 5: another unique paper for variety
        PaperResult(
            external_id="s2_resnet",
            paper_id="s2_resnet",
            source="openalex",
            title="Deep Residual Learning for Image Recognition",
            abstract="Deeper neural networks are more difficult to train.",
            authors=["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
            year=2015,
            url="https://arxiv.org/abs/1512.03385",
            doi="10.48550/arXiv.1512.03385",
            citation_count=180000,
        ),
    ]


@pytest.fixture
def httpx_mock():
    """Use respx to mock academic API endpoints.

    Mocks the main search endpoints for:
    - Semantic Scholar
    - arXiv
    - OpenAlex
    - CrossRef
    """
    import xml.etree.ElementTree as ET

    base_s2 = "https://api.semanticscholar.org/graph/v1"
    base_rec = "https://api.semanticscholar.org/recommendations/v1"
    base_arxiv = "https://export.arxiv.org/api/query"
    base_openalex = "https://api.openalex.org"
    base_crossref = "https://api.crossref.org"

    with respx.mock:
        # --- Semantic Scholar ---
        # Paper search/bulk
        respx.get(f"{base_s2}/paper/search/bulk").respond(
            json={
                "data": [
                    {
                        "paperId": "s2_doi_only",
                        "title": "Attention Is All You Need",
                        "abstract": "The dominant sequence transduction models.",
                        "authors": [{"name": "Ashish Vaswani"}],
                        "year": 2017,
                        "url": "https://arxiv.org/abs/1706.03762",
                        "externalIds": {"DOI": "10.48550/arXiv.1706.03762"},
                        "citationCount": 95000,
                    }
                ]
            }
        )
        # Paper search/match
        respx.get(f"{base_s2}/paper/search/match").respond(
            json={"data": [{"paperId": "s2_doi_only", "title": "Attention Is All You Need"}]}
        )
        # Get single paper
        respx.get(url__startswith=f"{base_s2}/paper/", regex=False).respond(
            json={
                "paperId": "s2_doi_only",
                "title": "Attention Is All You Need",
                "abstract": "The dominant sequence transduction models.",
                "authors": [{"name": "Ashish Vaswani"}],
                "year": 2017,
                "url": "https://arxiv.org/abs/1706.03762",
                "externalIds": {"DOI": "10.48550/arXiv.1706.03762"},
                "citationCount": 95000,
            }
        )

        # --- arXiv ---
        arxiv_xml = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models.</summary>
    <published>2017-06-12</published>
    <author><name>Ashish Vaswani</name></author>
    <link href="http://arxiv.org/abs/1706.03762" rel="alternate" type="text/html"/>
  </entry>
</feed>"""
        respx.get(base_arxiv).respond(
            content=arxiv_xml.encode(),
            headers={"Content-Type": "application/xml"},
        )

        # --- OpenAlex ---
        respx.get(f"{base_openalex}/works").respond(
            json={
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "title": "Attention Is All You Need",
                        "abstract_inverted_index": {"The": [0], "dominant": [1]},
                        "authorships": [
                            {
                                "author": {"display_name": "Ashish Vaswani"},
                                "author_position": "first",
                            }
                        ],
                        "publication_year": 2017,
                        "doi": "https://doi.org/10.48550/arXiv.1706.03762",
                        "cited_by_count": 95000,
                    }
                ]
            }
        )
        respx.get(f"{base_openalex}/authors").respond(
            json={
                "results": [
                    {
                        "id": "https://openalex.org/A1",
                        "display_name": "Ashish Vaswani",
                        "last_known_institutions": [{"display_name": "Google"}],
                        "works_count": 42,
                        "cited_by_count": 150000,
                        "summary_stats": {"h_index": 30},
                    }
                ]
            }
        )

        # --- CrossRef ---
        respx.get(f"{base_crossref}/works").respond(
            json={
                "message": {
                    "items": [
                        {
                            "DOI": "10.48550/arXiv.1706.03762",
                            "title": ["Attention Is All You Need"],
                            "author": [{"given": "Ashish", "family": "Vaswani"}],
                            "published-print": {"date-parts": [[2017]]},
                            "URL": "https://arxiv.org/abs/1706.03762",
                            "is-referenced-by-count": 95000,
                        }
                    ]
                }
            }
        )

        yield
