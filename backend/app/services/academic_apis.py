import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.utils.rate_limiters import arxiv_rate_limiter

logger = logging.getLogger(__name__)

_FIELDS = "title,abstract,authors,year,url,externalIds,citationCount"


@dataclass
class PaperResult:
    external_id: str
    source: str
    title: str
    abstract: str | None
    authors: list[str]
    year: int | None
    url: str | None
    doi: str | None
    citation_count: int | None = None
    tldr: str | None = None
    paper_id: str | None = None

    @staticmethod
    def from_s2(paper: dict) -> "PaperResult":
        tldr_obj = paper.get("tldr")
        return PaperResult(
            external_id=paper.get("paperId", ""),
            paper_id=paper.get("paperId"),
            source="semantic_scholar",
            title=paper.get("title", ""),
            abstract=paper.get("abstract"),
            authors=[a.get("name", "") for a in paper.get("authors", [])],
            year=paper.get("year"),
            url=paper.get("url"),
            doi=paper.get("externalIds", {}).get("DOI"),
            citation_count=paper.get("citationCount"),
            tldr=tldr_obj.get("text") if tldr_obj else None,
        )


class SemanticScholarAPI:

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    REC_URL = "https://api.semanticscholar.org/recommendations/v1"

    def _headers(self, user_api_key: str | None = None) -> dict:
        key = user_api_key or settings.SEMANTIC_SCHOLAR_API_KEY
        if key and key != "YOUR_SEMANTIC_SCHOLAR_API_KEY_HERE":
            return {"x-api-key": key}
        return {}

    async def search(
        self,
        query: str,
        limit: int = 20,
        year: str | None = None,
        min_citations: int | None = None,
        sort: str = "citationCount:desc",
        venue: str | None = None,
        user_api_key: str | None = None,
    ) -> list[PaperResult]:
        headers = self._headers(user_api_key)
        fields = _FIELDS
        if venue:
            fields = _FIELDS + ",venue"
        params = {
            "query": query,
            "fields": fields,
            "sort": sort,
        }
        if year:
            params["year"] = year
        if min_citations:
            params["minCitationCount"] = str(min_citations)

        for attempt in range(3):
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/paper/search/bulk",
                    params=params,
                    headers=headers,
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    papers = data.get("data", [])[:limit]
                    if venue:
                        papers = [
                            p for p in papers
                            if venue.lower() in (p.get("venue") or "").lower()
                        ]
                    return [PaperResult.from_s2(p) for p in papers]
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(f"S2 429, retrying in {wait}s (attempt {attempt+1})")
                    await asyncio.sleep(wait)
                    continue
                logger.warning(f"S2 search failed {resp.status_code}: {resp.text[:200]}")
                return []
        return []

    async def get_paper(self, paper_id: str, user_api_key: str | None = None) -> Optional[PaperResult]:
        headers = self._headers(user_api_key)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/paper/{paper_id}",
                params={"fields": _FIELDS},
                headers=headers,
                timeout=30.0,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return PaperResult.from_s2(resp.json())

    async def get_citations(
        self, paper_id: str, limit: int = 50, user_api_key: str | None = None
    ) -> list[PaperResult]:
        headers = self._headers(user_api_key)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/paper/{paper_id}/citations",
                params={"fields": _FIELDS, "limit": str(min(limit, 1000))},
                headers=headers,
                timeout=30.0,
            )
            if resp.status_code != 200:
                logger.warning(f"S2 citations failed {resp.status_code}")
                return []
            data = resp.json()
            return [
                PaperResult.from_s2(entry["citingPaper"])
                for entry in data.get("data", [])
                if entry.get("citingPaper")
            ][:limit]

    async def get_references(
        self, paper_id: str, limit: int = 50, user_api_key: str | None = None
    ) -> list[PaperResult]:
        headers = self._headers(user_api_key)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/paper/{paper_id}/references",
                params={"fields": _FIELDS, "limit": str(min(limit, 1000))},
                headers=headers,
                timeout=30.0,
            )
            if resp.status_code != 200:
                logger.warning(f"S2 references failed {resp.status_code}")
                return []
            data = resp.json()
            return [
                PaperResult.from_s2(entry["citedPaper"])
                for entry in data.get("data", [])
                if entry.get("citedPaper")
            ][:limit]

    async def get_recommendations(
        self,
        positive_paper_ids: list[str],
        negative_paper_ids: list[str] | None = None,
        limit: int = 50,
        user_api_key: str | None = None,
    ) -> list[PaperResult]:
        headers = self._headers(user_api_key)
        body = {"positivePaperIds": positive_paper_ids}
        if negative_paper_ids:
            body["negativePaperIds"] = negative_paper_ids

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.REC_URL}/papers",
                params={"fields": _FIELDS, "limit": str(min(limit, 500))},
                json=body,
                headers=headers,
                timeout=30.0,
            )
            if resp.status_code != 200:
                logger.warning(f"S2 recommendations failed {resp.status_code}")
                return []
            data = resp.json()
            papers = data.get("recommendedPapers", [])
            return sorted(
                [PaperResult.from_s2(p) for p in papers],
                key=lambda x: x.citation_count or 0,
                reverse=True,
            )

    async def resolve_paper_id(
        self, title: str, user_api_key: str | None = None
    ) -> Optional[str]:
        """Resolve a paper title to its Semantic Scholar paperId via /paper/search/match.

        Returns the paperId string, or None if no match is found.
        This is the bridge that lets us feed free-text titles into the S2
        Recommendations API (which requires S2 paper IDs).
        """
        if not title or not title.strip():
            return None
        headers = self._headers(user_api_key)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/paper/search/match",
                    params={"query": title, "fields": "paperId,title"},
                    headers=headers,
                    timeout=20.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    matches = data.get("data") or []
                    if matches:
                        return matches[0].get("paperId")
                if resp.status_code == 429:
                    logger.warning("S2 search/match 429; skipping resolve")
                else:
                    logger.warning(f"S2 search/match failed {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"S2 search/match error: {e}")
        return None

    async def build_related_work(
        self,
        paper_id: str,
        topic_query: str,
        limit: int = 20,
        user_api_key: str | None = None,
    ) -> list[PaperResult]:
        seen = set()
        results = []

        try:
            refs = await self.get_references(paper_id, limit=30, user_api_key=user_api_key)
            for p in refs:
                if p.paper_id and p.paper_id not in seen:
                    seen.add(p.paper_id)
                    results.append(p)
            await asyncio.sleep(1)
        except Exception:
            pass

        try:
            recs = await self.get_recommendations(
                [paper_id], limit=30, user_api_key=user_api_key
            )
            for p in recs:
                if p.paper_id and p.paper_id not in seen:
                    seen.add(p.paper_id)
                    results.append(p)
            await asyncio.sleep(1)
        except Exception:
            pass

        try:
            search = await self.search(topic_query, limit=20, user_api_key=user_api_key)
            for p in search:
                if p.paper_id and p.paper_id not in seen:
                    seen.add(p.paper_id)
                    results.append(p)
        except Exception:
            pass

        results.sort(key=lambda x: x.citation_count or 0, reverse=True)
        return results[:limit]


class ArXivAPI:

    BASE_URL = "https://export.arxiv.org/api/query"

    async def search(
        self,
        query: str,
        max_results: int = 20,
        start: int = 0,
    ) -> list[PaperResult]:
        import xml.etree.ElementTree as ET

        await arxiv_rate_limiter.acquire()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.BASE_URL,
                params={
                    "search_query": f"all:{query}",
                    "start": start,
                    "max_results": max_results,
                },
                timeout=30.0,
            )
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            results = []
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                authors = entry.findall("atom:author", ns)
                link = entry.find("atom:link", ns)
                arxiv_id = entry.find("atom:id", ns)
                published = entry.find("atom:published", ns)

                year = None
                if published is not None and published.text:
                    try:
                        year = int(published.text[:4])
                    except ValueError:
                        pass

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
                        year=year,
                        url=link.get("href") if link is not None else None,
                        doi=None,
                    )
                )
            return results


class OpenAlexAPI:
    """OpenAlex API — fully free, no key required.

    250M+ works. Set mailto header for polite pool (higher rate limits).
    """

    BASE_URL = "https://api.openalex.org"

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
        if not inverted_index:
            return None
        try:
            word_positions: list[tuple[int, str]] = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort(key=lambda x: x[0])
            return " ".join(word for _, word in word_positions)
        except Exception:
            return None

    async def search(
        self,
        query: str,
        limit: int = 20,
        year: str | None = None,
        venue: str | None = None,
        min_citation_count: int | None = None,
        user_api_key: str | None = None,
    ) -> list[PaperResult]:
        params: dict = {
            "search": query,
            "per_page": min(limit, 200),
            "sort": "relevance_score:desc",
        }
        filters: list[str] = []
        if year:
            filters.append(f"publication_year:{year}")
        if min_citation_count is not None:
            filters.append(f"cited_by_count:>{min_citation_count}")
        if filters:
            params["filter"] = ",".join(filters)

        mailto = user_api_key if user_api_key else "academic-pal@example.com"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/works",
                params=params,
                headers={"User-Agent": f"mailto:{mailto}"},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("results", []):
                authors = [
                    a.get("author", {}).get("display_name", "")
                    for a in item.get("authorships", [])
                    if a.get("author", {}).get("display_name")
                ]

                venue_info = item.get("primary_location") or {}
                source = venue_info.get("source") or {}
                item_venue = source.get("display_name")

                if venue and venue.lower() not in (item_venue or "").lower():
                    continue

                doi_raw = item.get("doi") or ""
                doi = doi_raw.replace("https://doi.org/", "") if doi_raw else None

                results.append(
                    PaperResult(
                        external_id=item.get("id", ""),
                        source="openalex",
                        title=item.get("title", ""),
                        abstract=self._reconstruct_abstract(item.get("abstract_inverted_index")),
                        authors=authors,
                        year=item.get("publication_year"),
                        url=item.get("doi") or item.get("id"),
                        doi=doi,
                        citation_count=item.get("cited_by_count"),
                    )
                )
            return results

    async def search_authors(
        self,
        name: str,
        limit: int = 5,
        user_api_key: str | None = None,
    ) -> list[dict]:
        mailto = user_api_key if user_api_key else "academic-pal@example.com"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/authors",
                params={"search": name, "per_page": limit},
                headers={"User-Agent": f"mailto:{mailto}"},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

            authors = []
            for item in data.get("results", []):
                institution = None
                if item.get("last_known_institutions"):
                    institution = item["last_known_institutions"][0].get("display_name")
                authors.append({
                    "id": item.get("id", ""),
                    "name": item.get("display_name", ""),
                    "institution": institution,
                    "paper_count": item.get("works_count"),
                    "citation_count": item.get("cited_by_count"),
                    "h_index": item.get("summary_stats", {}).get("h_index"),
                    "source": "openalex",
                })
            return authors


class CrossRefAPI:

    BASE_URL = "https://api.crossref.org"

    async def search(
        self,
        query: str,
        rows: int = 20,
        offset: int = 0,
    ) -> list[PaperResult]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/works",
                params={"query": query, "rows": rows, "offset": offset},
                headers=(
                    {"Crossref-Plus-API-Token": settings.CROSSREF_API_KEY}
                    if settings.CROSSREF_API_KEY and settings.CROSSREF_API_KEY != "YOUR_CROSSREF_API_KEY_HERE"
                    else {}
                ),
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

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
openalex_api = OpenAlexAPI()
