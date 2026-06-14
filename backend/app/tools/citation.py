from typing import Any

from langchain_core.tools import tool

from app.services.academic_apis import semantic_scholar


@tool
async def format_citation(
    doi: str | None = None,
    title: str | None = None,
    style: str = "apa",
) -> str:
    """Format a citation in the specified style.

    Args:
        doi: DOI of the paper
        title: Title of the paper (used if DOI not provided)
        style: Citation style ("apa", "mla", "chicago", "ieee")
    """
    if doi:
        paper = await semantic_scholar.get_paper(doi)
        if paper:
            authors = ", ".join(paper.authors[:3])
            if len(paper.authors) > 3:
                authors += ", et al."
            return f"{authors} ({paper.year or 'n.d.'}). {paper.title}. {f'DOI: {paper.doi}' if paper.doi else ''}"

    if title:
        results = await semantic_scholar.search(title, limit=1)
        if results:
            paper = results[0]
            authors = ", ".join(paper.authors[:3])
            if len(paper.authors) > 3:
                authors += ", et al."
            return f"{authors} ({paper.year or 'n.d.'}). {paper.title}."

    return "Citation not found"


@tool
async def find_citation(query: str) -> dict[str, Any] | None:
    """Find a paper and return its citation metadata.

    Args:
        query: Paper title or description to search for
    """
    results = await semantic_scholar.search(query, limit=1)
    if not results:
        return None

    paper = results[0]
    return {
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "doi": paper.doi,
        "url": paper.url,
        "citation_count": paper.citation_count,
    }
