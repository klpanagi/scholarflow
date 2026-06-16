import logging
from typing import Any

from langchain_core.tools import tool

from app.services.academic_apis import semantic_scholar, arxiv_api, crossref_api, openalex_api
from app.services.search_service import search_service

logger = logging.getLogger(__name__)


def _truncate_query(query: str, max_chars: int = 200) -> str:
    if len(query) <= max_chars:
        return query
    truncated = query[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.6:
        truncated = truncated[:last_space]
    result = truncated + "..."
    logger.info(f"Query truncated: {len(query)} -> {len(result)} chars")
    return result


@tool
async def search_papers(
    query: str,
    source: str = "all",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search academic papers across Semantic Scholar, arXiv, CrossRef, and OpenAlex."""
    query = _truncate_query(query)
    results = []

    if source in ("all", "semantic_scholar"):
        try:
            s2 = await semantic_scholar.search(query, limit=limit)
            results.extend([
                {
                    "title": r.title,
                    "authors": r.authors,
                    "year": r.year,
                    "abstract": r.abstract,
                    "source": r.source,
                    "url": r.url,
                    "doi": r.doi,
                    "citation_count": r.citation_count,
                    "tldr": r.tldr,
                }
                for r in s2
            ])
        except Exception as e:
            logger.warning(f"Semantic Scholar search failed: {e}")

    if source in ("all", "arxiv"):
        try:
            arxiv_results = await arxiv_api.search(query, max_results=limit)
            results.extend([
                {
                    "title": r.title,
                    "authors": r.authors,
                    "year": r.year,
                    "abstract": r.abstract,
                    "source": r.source,
                    "url": r.url,
                    "doi": r.doi,
                }
                for r in arxiv_results
            ])
        except Exception as e:
            logger.warning(f"arXiv search failed: {e}")

    if source in ("all", "crossref"):
        try:
            cr = await crossref_api.search(query, rows=limit)
            results.extend([
                {
                    "title": r.title,
                    "authors": r.authors,
                    "year": r.year,
                    "abstract": r.abstract,
                    "source": r.source,
                    "url": r.url,
                    "doi": r.doi,
                    "citation_count": r.citation_count,
                }
                for r in cr
            ])
        except Exception as e:
            logger.warning(f"CrossRef search failed: {e}")

    if source in ("all", "openalex"):
        try:
            oa = await openalex_api.search(query, limit=limit)
            results.extend([
                {
                    "title": r.title,
                    "authors": r.authors,
                    "year": r.year,
                    "abstract": r.abstract,
                    "source": r.source,
                    "url": r.url,
                    "doi": r.doi,
                    "citation_count": r.citation_count,
                }
                for r in oa
            ])
        except Exception as e:
            logger.warning(f"OpenAlex search failed: {e}")

    # Deduplicate by normalized title
    seen_titles = set()
    deduped = []
    for r in results:
        title_key = (r.get("title") or "").lower().strip()
        if title_key and title_key not in seen_titles:
            seen_titles.add(title_key)
            deduped.append(r)

    logger.info(f"search_papers('{query[:50]}...'): {len(deduped)} unique results from {len(results)} total")
    return deduped[:limit]


@tool
async def search_web(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search the web for supplementary information.

    Args:
        query: Search query
        limit: Maximum results
    """
    return await search_service.search(query=query, index="web", limit=limit)
