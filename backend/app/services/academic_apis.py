"""Academic API integrations (Semantic Scholar, arXiv, CrossRef)."""

from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings


@dataclass
class PaperResult:
    """Paper from academic API."""

    external_id: str
    source: str
    title: str
    abstract: str | None
    authors: list[str]
    year: int | None
    url: str | None
    doi: str | None
    citation_count: int | None = None


class SemanticScholarAPI:
    """Semantic Scholar API client."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PaperResult]:
        """Search papers."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/paper/search",
                params={
                    "query": query,
                    "limit": limit,
                    "offset": offset,
                    "fields": "title,abstract,authors,year,url,externalIds,citationCount",
                },
                headers=(
                    {"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY}
                    if settings.SEMANTIC_SCHOLAR_API_KEY
                    else {}
                ),
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return [
                PaperResult(
                    external_id=paper.get("paperId", ""),
                    source="semantic_scholar",
                    title=paper.get("title", ""),
                    abstract=paper.get("abstract"),
                    authors=[a.get("name", "") for a in paper.get("authors", [])],
                    year=paper.get("year"),
                    url=paper.get("url"),
                    doi=paper.get("externalIds", {}).get("DOI"),
                    citation_count=paper.get("citationCount"),
                )
                for paper in data.get("data", [])
            ]

    async def get_paper(self, paper_id: str) -> Optional[PaperResult]:
        """Get paper by ID."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/paper/{paper_id}",
                params={
                    "fields": "title,abstract,authors,year,url,externalIds,citationCount",
                },
                headers=(
                    {"x-api-key": settings.SEMANTIC_SCHOLAR_API_KEY}
                    if settings.SEMANTIC_SCHOLAR_API_KEY
                    else {}
                ),
                timeout=30.0,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            paper = response.json()

            return PaperResult(
                external_id=paper.get("paperId", ""),
                source="semantic_scholar",
                title=paper.get("title", ""),
                abstract=paper.get("abstract"),
                authors=[a.get("name", "") for a in paper.get("authors", [])],
                year=paper.get("year"),
                url=paper.get("url"),
                doi=paper.get("externalIds", {}).get("DOI"),
                citation_count=paper.get("citationCount"),
            )


class ArXivAPI:
    """arXiv API client."""

    BASE_URL = "http://export.arxiv.org/api/query"

    async def search(
        self,
        query: str,
        max_results: int = 20,
        start: int = 0,
    ) -> list[PaperResult]:
        """Search arXiv papers."""
        import xml.etree.ElementTree as ET

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.BASE_URL,
                params={
                    "search_query": f"all:{query}",
                    "start": start,
                    "max_results": max_results,
                },
                timeout=30.0,
            )
            response.raise_for_status()

            root = ET.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            results = []
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                authors = entry.findall("atom:author", ns)
                link = entry.find("atom:link", ns)
                arxiv_id = entry.find("atom:id", ns)

                results.append(
                    PaperResult(
                        external_id=arxiv_id.text.split("/abs/")[-1] if arxiv_id is not None else "",
                        source="arxiv",
                        title=title.text.strip().replace("\n", " ") if title is not None else "",
                        abstract=summary.text.strip() if summary is not None else None,
                        authors=[
                            a.find("atom:name", ns).text
                            for a in authors
                            if a.find("atom:name", ns) is not None
                        ],
                        year=None,
                        url=link.get("href") if link is not None else None,
                        doi=None,
                    )
                )

            return results


class CrossRefAPI:
    """CrossRef API client."""

    BASE_URL = "https://api.crossref.org"

    async def search(
        self,
        query: str,
        rows: int = 20,
        offset: int = 0,
    ) -> list[PaperResult]:
        """Search CrossRef works."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/works",
                params={
                    "query": query,
                    "rows": rows,
                    "offset": offset,
                },
                headers=(
                    {"Crossref-Plus-API-Token": settings.CROSSREF_API_KEY}
                    if settings.CROSSREF_API_KEY
                    else {}
                ),
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("message", {}).get("items", []):
                authors = [
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in item.get("author", [])
                ]
                year = None
                if item.get("published-print"):
                    year = item["published-print"].get("date-parts", [[None]])[0][0]

                results.append(
                    PaperResult(
                        external_id=item.get("DOI", ""),
                        source="crossref",
                        title=item.get("title", [""])[0] if item.get("title") else "",
                        abstract=item.get("abstract"),
                        authors=authors,
                        year=year,
                        url=item.get("URL"),
                        doi=item.get("DOI"),
                        citation_count=item.get("is-referenced-by-count"),
                    )
                )

            return results


semantic_scholar = SemanticScholarAPI()
arxiv_api = ArXivAPI()
crossref_api = CrossRefAPI()
