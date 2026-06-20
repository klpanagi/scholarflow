import respx

from app.services.academic_apis import OpenAlexAPI, SemanticScholarAPI

S2_BASE = "https://api.semanticscholar.org/graph/v1"
OA_BASE = "https://api.openalex.org"


def _s2_bulk_payload(papers: list[dict]) -> dict:
    return {"data": papers}


def _s2_paper(
    paper_id: str,
    title: str,
    venue: str | None = None,
    citation_count: int = 100,
    year: int = 2024,
) -> dict:
    p: dict = {
        "paperId": paper_id,
        "title": title,
        "abstract": f"Abstract for {title}",
        "authors": [{"name": "Test Author"}],
        "year": year,
        "url": f"https://example.com/{paper_id}",
        "externalIds": {},
        "citationCount": citation_count,
    }
    if venue is not None:
        p["venue"] = venue
    return p


def _oa_work_item(
    work_id: str,
    title: str,
    year: int = 2024,
    cited_by_count: int = 100,
) -> dict:
    return {
        "id": f"https://openalex.org/{work_id}",
        "title": title,
        "abstract_inverted_index": {"The": [0], "abstract": [1]},
        "authorships": [{"author": {"display_name": "Test Author"}}],
        "publication_year": year,
        "doi": f"https://doi.org/10.example/{work_id}",
        "cited_by_count": cited_by_count,
    }


@respx.mock
async def test_s2_search_passes_year_param():
    route = respx.get(f"{S2_BASE}/paper/search/bulk").respond(
        json=_s2_bulk_payload([_s2_paper("p1", "Paper One")])
    )

    api = SemanticScholarAPI()
    results = await api.search("deep learning", year="2024", limit=5)

    assert len(results) == 1
    request_url = str(route.calls[0].request.url)
    assert "year=2024" in request_url, f"Expected 'year=2024' in URL, got: {request_url}"


@respx.mock
async def test_s2_search_passes_min_citation_param():
    route = respx.get(f"{S2_BASE}/paper/search/bulk").respond(
        json=_s2_bulk_payload([_s2_paper("p1", "Paper One", citation_count=50)])
    )

    api = SemanticScholarAPI()
    results = await api.search("transformers", min_citations=10, limit=5)

    assert len(results) == 1
    request_url = str(route.calls[0].request.url)
    assert "minCitationCount=10" in request_url, (
        f"Expected 'minCitationCount=10' in URL, got: {request_url}"
    )


@respx.mock
async def test_openalex_search_passes_year_param():
    route = respx.get(f"{OA_BASE}/works").respond(
        json={"results": [_oa_work_item("W1", "Paper One")]}
    )

    api = OpenAlexAPI()
    results = await api.search("neural networks", year="2024", limit=5)

    assert len(results) == 1
    request_url = str(route.calls[0].request.url)
    assert "filter=publication_year" in request_url and "2024" in request_url, (
        f"Expected 'filter=publication_year:2024' in URL, got: {request_url}"
    )


@respx.mock
async def test_s2_search_filters_by_venue_post_hoc():
    three_papers = [
        _s2_paper("p1", "NeurIPS Paper", venue="NeurIPS"),
        _s2_paper("p2", "ICML Paper", venue="ICML"),
        _s2_paper("p3", "ICLR Paper", venue="ICLR"),
    ]
    respx.get(f"{S2_BASE}/paper/search/bulk").respond(
        json=_s2_bulk_payload(three_papers)
    )

    api = SemanticScholarAPI()
    results = await api.search("machine learning", venue="NeurIPS", limit=10)

    assert len(results) == 1, f"Expected 1 result, got {len(results)}"
    assert results[0].title == "NeurIPS Paper"
