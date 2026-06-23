import asyncio
import json
import logging
import math
import re
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState
from app.agents.dedup import deduplicate_papers, levenshtein
from app.agents.dossier import (
    MethodologyEntry,
    PaperRecord,
    PaperSource,
    ResearchDossier,
    ResearchGap,
    SearchMetadata,
    _coerce_source_name,
    _resolve_paper_id,
)
from app.services.academic_apis import (
    semantic_scholar,
    arxiv_api,
    crossref_api,
    openalex_api,
)
from app.utils.pdf_model_support import extract_text_from_message_content
from app.utils.rate_limiters import arxiv_rate_limiter

logger = logging.getLogger(__name__)


_METHODS_TOP_N = 15


def _parse_llm_json(text: str) -> dict | None:
    """Recover a JSON object from an LLM response, tolerating code fences and prose.

    Tries in order:
    1. Strip ```json ... ``` (or plain ```) fences and parse the captured block
    2. Parse the whole text as JSON
    3. Find the first {...} block via regex and parse that

    Returns the parsed dict, or None if all attempts fail.
    """
    if not text or not isinstance(text, str):
        return None

    candidates = [text]

    fenced = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE
    )
    if fenced:
        candidates.append(fenced.group(1))

    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass

    first_obj = re.search(r"\{.*\}", text, re.DOTALL)
    if first_obj:
        try:
            obj = json.loads(first_obj.group(0))
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _resolve_paper_id_for_methodology(paper: dict) -> str:
    """Pick a stable paper_id for a MethodologyEntry row.

    Priority: explicit paper_id > doi > arxiv:arxiv_id > url > title:<title> > "".
    """
    pid = paper.get("paper_id")
    if pid:
        return str(pid)
    doi = paper.get("doi")
    if doi:
        return str(doi)
    arxiv = paper.get("arxiv_id")
    if arxiv:
        return f"arxiv:{arxiv}"
    url = paper.get("url")
    if url:
        return str(url)
    title = paper.get("title")
    if title:
        return f"title:{title}"
    return ""


async def _extract_methodology_for_paper(
    llm: BaseChatModel,
    paper: dict,
) -> MethodologyEntry:
    """Ask the LLM to extract a methodology row from a paper abstract.

    Returns a MethodologyEntry with confidence="low" if the LLM call or JSON
    recovery fails — never raises. The fallback row uses the paper title as
    method_name and "unknown" for dataset/result so downstream consumers
    can still distinguish a failed extraction from an absent one.
    """
    paper_id = _resolve_paper_id_for_methodology(paper)
    abstract = (paper.get("abstract") or "").strip()
    title = paper.get("title") or "Untitled"

    prompt = (
        "You extract structured methodology information from academic paper abstracts.\n\n"
        f"Paper title: {title}\n"
        f"Abstract:\n{abstract}\n\n"
        "Extract the following from the abstract and return ONLY a JSON object "
        "with exactly these keys (no commentary, no markdown):\n"
        "1. method_name: name of the proposed/analysed method as written in the paper\n"
        "2. dataset: dataset or benchmark on which the result was measured "
        '(string; use "unknown" if not stated)\n'
        "3. metrics: list of metric names reported "
        '(e.g. ["BLEU", "ROUGE-L"]; use [] if none stated)\n'
        "4. baseline_methods: list of baseline method names the proposed method is "
        "compared against (use [] if none stated)\n"
        "5. result: reported main result string "
        '(e.g. "28.4 BLEU", "91.2% accuracy"; use "unknown" if not stated)\n'
        '6. confidence: your confidence in this extraction — "high", "medium", or "low"\n\n'
        "Example output:\n"
        '{"method_name": "...", "dataset": "...", "metrics": ["..."], '
        '"baseline_methods": ["..."], "result": "...", "confidence": "high"}'
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        text = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
    except Exception as e:
        logger.warning(f"evaluate_methods: LLM call failed for paper {paper_id!r}: {e}")
        return MethodologyEntry(
            paper_id=paper_id,
            method_name=title,
            dataset="unknown",
            metrics=[],
            baseline_methods=[],
            result="unknown",
            confidence="low",
        )

    parsed = _parse_llm_json(text)
    if not parsed:
        logger.warning(
            f"evaluate_methods: could not recover JSON for paper {paper_id!r}; "
            f"raw response (first 200 chars): {text[:200]!r}"
        )
        return MethodologyEntry(
            paper_id=paper_id,
            method_name=title,
            dataset="unknown",
            metrics=[],
            baseline_methods=[],
            result="unknown",
            confidence="low",
        )

    confidence = parsed.get("confidence") or "medium"
    if confidence not in ("high", "medium", "low"):
        confidence = "medium"

    return MethodologyEntry(
        paper_id=paper_id,
        method_name=parsed.get("method_name") or title,
        dataset=parsed.get("dataset") or "unknown",
        metrics=list(parsed.get("metrics") or []),
        baseline_methods=list(parsed.get("baseline_methods") or []),
        result=parsed.get("result") or "unknown",
        confidence=confidence,
    )


async def _expand_queries_with_llm(
    llm: BaseChatModel,
    base_queries: list[str],
    message_content: str,
    n_queries: int = 4,
) -> list[str]:
    """Ask the LLM for n_queries additional search queries (synonyms, related concepts).

    The regex-based _extract_search_queries only sees the paper title + first abstract
    sentence + keywords line. This step adds semantic breadth: domain synonyms, related
    methodologies, broader/narrower topic variants — based on the full paper context.
    Returns [] on any failure so the caller can fall back to the original queries.
    """
    if not base_queries or not llm:
        return []

    queries_block = "\n".join(f"- {q}" for q in base_queries[:6])
    content_snip = (message_content or "")[:1500]

    prompt = (
        "You help expand academic search queries to find related work.\n\n"
        f"Current queries extracted from the paper:\n{queries_block}\n\n"
        f"Paper content snippet (first 1500 chars):\n{content_snip}\n\n"
        f"Generate {n_queries} ADDITIONAL search queries that would find papers "
        "related to this work. Focus on:\n"
        "- Domain synonyms (e.g., 'machine learning' → 'statistical learning')\n"
        "- Related concepts, methodologies, and techniques\n"
        "- Broader/narrower scope variants of the topic\n"
        "- Specific tools, datasets, or evaluation methods mentioned\n\n"
        "Output ONLY the queries, one per line. No numbering, no bullets, no commentary. "
        "Each query should be 3-8 words and search-friendly."
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        text = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
        cleaned: list[str] = []
        for line in text.split("\n"):
            c = line.strip().lstrip("0123456789.-) ").strip().strip("`\"'")
            if not c or len(c) < 5 or len(c) > 120:
                continue
            if c.startswith(("#", "*", ">", "Here", "Output", "Sure", "Below", "Note")):
                continue
            if not (2 <= len(c.split()) <= 10):
                continue
            cleaned.append(c)
        return cleaned[:n_queries]
    except Exception as e:
        logger.warning(f"_expand_queries_with_llm failed: {e}")
        return []


async def _resolve_to_recommendations(title: str) -> tuple[str | None, list]:
    """Resolve a paper title to S2 paperId and fetch recommendations.

    Returns (paperId_or_None, list_of_PaperResult). The paperId is returned
    so callers can record which seed was used (useful for the synthesis prompt
    and for debugging).
    """
    if not title or not title.strip():
        return None, []
    try:
        pid = await semantic_scholar.resolve_paper_id(title)
        if not pid:
            return None, []
        recs = await semantic_scholar.get_recommendations([pid], limit=20)
        return pid, recs
    except Exception as e:
        logger.warning(f"_resolve_to_recommendations failed: {e}")
        return None, []


def _extract_paper_title(full_text: str) -> str:
    import re

    text = full_text.strip()

    # Strip "PAPER / INPUT:" prefix injected by _build_stage_context
    paper_block = re.search(
        r"PAPER\s*/\s*INPUT:\s*\n(.+)", text, re.IGNORECASE | re.DOTALL
    )
    if paper_block:
        text = paper_block.group(1).strip()

    title_match = re.search(r"^Title[:\s]+([^\n]+)", text, re.IGNORECASE | re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()

    # Handle task_template format: "Paper:\n{content}\n\nOutput:"
    paper_match = re.search(
        r"Paper:\s*\n(.+?)(?:\n\n|\nOutput:)", text, re.IGNORECASE | re.DOTALL
    )
    if paper_match:
        inner = paper_match.group(1).strip()
        inner_title = re.search(
            r"^Title[:\s]+([^\n]+)", inner, re.IGNORECASE | re.MULTILINE
        )
        if inner_title:
            return inner_title.group(1).strip()
        first_line = inner.split("\n")[0].strip()
        if len(first_line) > 10:
            return first_line[:120]

    # Fallback: first substantial non-instruction line
    for line in text.split("\n"):
        line = line.strip()
        if (
            len(line) > 10
            and not line.lower().startswith(
                ("you are", "search for", "find ", "output:", "paper:", "instruction")
            )
            and not line.startswith(("- ", "* ", "1.", "2.", "3."))
        ):
            return line[:120]

    return text[:120]


async def verify_paper_exists(title: str, doi: str | None = None) -> dict:

    if doi:
        try:
            result = await semantic_scholar.search(doi, limit=1)
            if result:
                return {
                    "verified": True,
                    "source": "semantic_scholar",
                    "url": f"https://doi.org/{doi}",
                    "title": result[0].title,
                }
        except Exception:
            pass

    try:
        results = await semantic_scholar.search(title, limit=3)
        for r in results:
            title_lower = r.title.lower().strip()
            search_title_lower = title.lower().strip()
            if (
                title_lower == search_title_lower
                or search_title_lower in title_lower
                or title_lower in search_title_lower
            ):
                return {
                    "verified": True,
                    "source": "semantic_scholar",
                    "url": getattr(r, "url", None),
                    "title": r.title,
                }
    except Exception:
        pass

    try:
        results = await openalex_api.search(title, limit=3)
        for r in results:
            title_lower = r.title.lower().strip()
            search_title_lower = title.lower().strip()
            if (
                title_lower == search_title_lower
                or search_title_lower in title_lower
                or title_lower in search_title_lower
            ):
                return {
                    "verified": True,
                    "source": "openalex",
                    "url": getattr(r, "url", None),
                    "title": r.title,
                }
    except Exception:
        pass

    return {"verified": False, "source": None, "url": None, "title": title}


def _extract_search_queries(full_text: str, max_queries: int = 8) -> list[str]:
    import re

    primary = _extract_paper_title(full_text)
    queries = [primary]

    text = full_text.strip()
    paper_block = re.search(
        r"PAPER\s*/\s*INPUT:\s*\n(.+)", text, re.IGNORECASE | re.DOTALL
    )
    if paper_block:
        text = paper_block.group(1).strip()

    paper_match = re.search(
        r"Paper\s+to\s+review:\s*\n(.+?)(?:\n\n|\nCRITICAL|\nOutput:)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if paper_match:
        text = paper_match.group(1).strip()

    abstract = ""
    abstract_match = re.search(
        r"Abstract[:\s]+(.+?)(?:\n\n|\nFull Text:|\nKeywords:|\nScientific)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if abstract_match:
        abstract = abstract_match.group(1).strip()[:500]
        sentences = re.split(r"[.!]", abstract)
        if sentences and len(sentences[0].split()) >= 3:
            queries.append(sentences[0].strip()[:120])

    kw_match = re.search(
        r"(?:keywords?|key terms?|Auto Tags)[:\s]+(.+?)(?:\n|$)", text, re.IGNORECASE
    )
    if kw_match:
        queries.append(kw_match.group(1).strip()[:120])

    areas_match = re.search(r"Scientific Areas[:\s]+(.+?)(?:\n|$)", text, re.IGNORECASE)
    if areas_match:
        queries.append(areas_match.group(1).strip()[:120])

    seen = set()
    unique = []
    for q in queries:
        q_clean = q.lower().strip()
        if q_clean not in seen and len(q_clean) > 5:
            seen.add(q_clean)
            unique.append(q)
    return unique[:max_queries]


def _compute_matched_in(paper, query: str) -> list[str]:
    """Return field names where `query` appears in `paper` (case-insensitive).

    Accepts either a dict or a PaperResult. Returns ["title"] as fallback when
    the query doesn't appear in any field — the paper was still returned by a
    source, so title is the safest attribution.
    """
    q = (query or "").lower().strip()
    if not q:
        return ["unknown"]
    if isinstance(paper, dict):
        title = (paper.get("title") or "").lower()
        abstract = (paper.get("abstract") or "").lower()
    else:
        title = (getattr(paper, "title", "") or "").lower()
        abstract = (getattr(paper, "abstract", "") or "").lower()
    matches: list[str] = []
    if q in title:
        matches.append("title")
    if q in abstract:
        matches.append("abstract")
    return matches or ["title"]


def _paper_to_dict(
    paper,
    matched_in: list[str] | None = None,
    query: str | None = None,
) -> dict:
    """Normalize PaperResult (or pre-staged dict) → dict with `matched_in` populated.

    Downstream nodes (dedup, identify_gaps) operate on dict shapes, so PaperResult
    is converted here. Either pass `matched_in` explicitly (for pre-query results
    like citation_graph, s2_recommendation) or `query` to compute it automatically.
    """
    if isinstance(paper, dict):
        d = dict(paper)
    else:
        d = {
            "external_id": getattr(paper, "external_id", None),
            "paper_id": getattr(paper, "paper_id", None),
            "source": getattr(paper, "source", ""),
            "title": getattr(paper, "title", "Untitled"),
            "abstract": getattr(paper, "abstract", None),
            "authors": getattr(paper, "authors", []) or [],
            "year": getattr(paper, "year", None),
            "url": getattr(paper, "url", None),
            "doi": getattr(paper, "doi", None),
            "citation_count": getattr(paper, "citation_count", None),
            "venue": getattr(paper, "venue", None),
        }
    if matched_in is not None:
        d["matched_in"] = list(matched_in)
    elif query is not None:
        d["matched_in"] = _compute_matched_in(d, query)
    else:
        d["matched_in"] = ["unknown"]
    return d


def _extract_tool_names(full_text: str) -> list[str]:
    """Extract specific tool/framework names from message content.

    Looks for:
    1. Explicit tool names in instructions (e.g., 'Search for RisQFLan')
    2. Capitalized names that look like tool names (e.g., 'CAL', 'PyCascades')
    3. Tool names in backticks or quotes
    """
    import re

    NON_TOOLS = {
        "The",
        "This",
        "That",
        "What",
        "When",
        "Where",
        "How",
        "Why",
        "You",
        "Your",
        "Output",
        "Input",
        "Paper",
        "Title",
        "Authors",
        "Abstract",
        "Keywords",
        "Search",
        "Find",
        "List",
        "For",
        "CRITICAL",
        "INSTRUCTIONS",
        "STEP",
        "NOTE",
        "IMPORTANT",
        "DSL",
        "STPA",
        "DOI",
        "URL",
        "PDF",
        "XML",
        "JSON",
        "EACH",
        "DSLs",
        "BROADER",
        "COMPETING",
        "TOOLS",
        "APPROACHES",
        "DOMAIN",
        "CONCEPTS",
        "RELATED",
        "WORK",
        "SPECIFICALLY",
        "USED",
        "FOUND",
        "ASSESSMENT",
        "GAPS",
        "OUTPUT",
    }

    tool_names = []

    search_patterns = [
        r"search\s+for\s+['\"]?([A-Z][A-Za-z0-9]+)['\"]?",
        r"Search\s+for\s+['\"]?([A-Z][A-Za-z0-9]+)['\"]?",
        r"specifically[.\s]+['\"]?([A-Z][A-Za-z0-9]+)['\"]?",
    ]
    for pattern in search_patterns:
        matches = re.findall(pattern, full_text)
        tool_names.extend([t for t in matches if t not in NON_TOOLS and len(t) > 2])

    quoted_patterns = [
        r"['\"]([A-Z][A-Za-z0-9]+)['\"]",
        r"`([A-Z][A-Za-z0-9]+)`",
    ]
    for pattern in quoted_patterns:
        matches = re.findall(pattern, full_text)
        tool_names.extend([t for t in matches if t not in NON_TOOLS and len(t) > 2])

    tool_context = re.findall(
        r"(?:tool|framework|system|platform|language|DSL|library|package|approach|method|model|notation)[s]?\s+(?:called|named|is|like|such as|including|e\.g\.)\s+([A-Z][A-Za-z0-9]+)",
        full_text,
    )
    tool_names.extend([t for t in tool_context if t not in NON_TOOLS and len(t) > 2])

    seen = set()
    unique = []
    for name in tool_names:
        name_lower = name.lower()
        if name_lower not in seen and len(name) > 2:
            seen.add(name_lower)
            unique.append(name)

    return unique


class SearchAgent(BaseAgent):
    name = "search"
    description = "Search and discover academic papers across multiple sources"
    system_prompt = (
        "You are a scholarly research assistant. Your role is to help users "
        "find relevant academic papers, understand research trends, and discover "
        "new publications in their field of interest.\n\n"
        "When searching for papers:\n"
        "- Use precise, domain-specific terminology\n"
        "- Consider synonyms and related concepts\n"
        "- Prioritize recent publications unless told otherwise\n"
        "- Provide context about why papers are relevant\n\n"
        "Always cite sources with title, authors, year, and venue when available."
    )

    async def search_papers(
        self,
        state: AgentState,
        *,
        year: str | None = None,
        min_citation_count: int | None = None,
        venue: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> AgentState:
        """Search all 4 sources per query with new filters, matched_in, and per-source failure isolation.

        Pre-query strategies (build_related_work, _expand_queries_with_llm, _resolve_to_recommendations)
        still run first to seed the result set with citation-graph and S2-recommendation papers.
        Per-source calls are wrapped in try/except so a single source failure populates
        `context["search_metadata"]["sources_failed"]` without killing the whole node.
        Manual dedup is REMOVED — Task 7's `deduplicate` node (using `app.agents.dedup`) handles it.
        """
        message_content = extract_text_from_message_content(
            state["messages"][-1].content
        )
        paper_s2_id = state["context"].get("paper_s2_id")
        topic_query = state["context"].get("topic_query")

        ctx = state["context"]
        year = year if year is not None else ctx.get("year")
        min_citation_count = (
            min_citation_count
            if min_citation_count is not None
            else ctx.get("min_citation_count")
        )
        venue = venue if venue is not None else ctx.get("venue")
        date_from = date_from if date_from is not None else ctx.get("date_from")
        date_to = date_to if date_to is not None else ctx.get("date_to")
        min_citations = min_citation_count

        ctx.setdefault("search_metadata", {})
        ctx["search_metadata"].setdefault("sources_failed", [])

        title = _extract_paper_title(message_content)
        base_queries = _extract_search_queries(message_content)
        tool_names = _extract_tool_names(message_content)
        for tool_name in tool_names:
            if tool_name.lower() not in [q.lower() for q in base_queries]:
                base_queries.append(tool_name)

        async def _build_related():
            if not paper_s2_id:
                return []
            try:
                return await semantic_scholar.build_related_work(
                    paper_id=paper_s2_id,
                    topic_query=topic_query or _extract_paper_title(message_content),
                    limit=20,
                )
            except Exception as e:
                logger.warning(f"build_related_work failed: {e}")
                return []

        (
            related_results,
            expanded_queries,
            (s2_seed_id, recommendations),
        ) = await asyncio.gather(
            _build_related(),
            _expand_queries_with_llm(self.llm, base_queries, message_content),
            _resolve_to_recommendations(title),
        )

        all_queries = list(base_queries)
        seen_lower = {q.lower() for q in all_queries}
        for q in expanded_queries:
            if q.lower() not in seen_lower:
                all_queries.append(q)
                seen_lower.add(q.lower())
        all_queries = all_queries[:12]

        raw_results: list[dict] = []

        for r in related_results:
            raw_results.append(_paper_to_dict(r, matched_in=["citation_graph"]))

        for r in recommendations or []:
            raw_results.append(_paper_to_dict(r, matched_in=["s2_recommendation"]))

        def _record_failure(source: str, query: str, exc: Exception) -> None:
            ctx["search_metadata"]["sources_failed"].append(
                {
                    "source": source,
                    "query": query,
                    "reason": str(exc),
                }
            )
            logger.warning(f"{source} search failed for {query!r}: {exc}")

        async def _search_one_source(q: str, source_name: str):
            if source_name == "s2":
                try:
                    return await semantic_scholar.search(
                        q,
                        limit=5,
                        year=year,
                        min_citations=min_citations,
                        venue=venue,
                    )
                except Exception as e:
                    _record_failure("semantic_scholar", q, e)
                    return []
            if source_name == "arxiv":
                try:
                    await arxiv_rate_limiter.acquire()
                    return await arxiv_api.search(q, max_results=5)
                except Exception as e:
                    _record_failure("arxiv", q, e)
                    return []
            if source_name == "crossref":
                try:
                    return await crossref_api.search(q, rows=3)
                except Exception as e:
                    _record_failure("crossref", q, e)
                    return []
            if source_name == "openalex":
                try:
                    return await openalex_api.search(
                        q,
                        limit=5,
                        year=year,
                        min_citation_count=min_citation_count,
                        venue=venue,
                    )
                except Exception as e:
                    _record_failure("openalex", q, e)
                    return []
            return []

        for q in all_queries:
            results_by_source = await asyncio.gather(
                _search_one_source(q, "s2"),
                _search_one_source(q, "arxiv"),
                _search_one_source(q, "crossref"),
                _search_one_source(q, "openalex"),
            )
            for source_results in results_by_source:
                for r in source_results:
                    raw_results.append(_paper_to_dict(r, query=q))

        raw_results.sort(key=lambda p: p.get("citation_count") or 0, reverse=True)

        ctx["raw_search_results"] = raw_results
        ctx["search_results"] = raw_results[:30]
        ctx["search_queries"] = all_queries
        ctx["expanded_queries"] = expanded_queries
        ctx["recommendations_seed_id"] = s2_seed_id

        logger.info(
            f"search_papers: {len(raw_results)} raw results, {len(all_queries)} queries "
            f"({len(expanded_queries)} expanded), seed={s2_seed_id}, "
            f"failed={len(ctx['search_metadata']['sources_failed'])}"
        )
        return state

    async def deduplicate(self, state: AgentState) -> AgentState:
        """Deduplicate raw search results using DOI, arXiv ID, and fuzzy title matching.

        Reads context["raw_search_results"] (set by search_papers) and writes
        context["deduplicated_results"] with merged papers. Each merged paper
        carries a merged_sources list for provenance tracking.
        """
        ctx = state["context"]
        raw = ctx.get("raw_search_results", [])

        deduplicated = deduplicate_papers(raw)

        ctx["deduplicated_results"] = deduplicated
        ctx["search_metadata"]["papers_after_dedup"] = len(deduplicated)

        logger.info(f"deduplicate: {len(raw)} raw → {len(deduplicated)} unique")
        return state

    async def evaluate_methods(self, state: AgentState) -> AgentState:
        """Extract a methodology row per top-15 deduplicated paper using the LLM.

        Reads context["deduplicated_results"] (set by `deduplicate`) and writes
        context["methodology_table"] = list[MethodologyEntry]. Caps processing
        at the top 15 papers (by `final_rank` when present, else first 15).
        Skips papers without an abstract. LLM failures and unparseable JSON
        produce a MethodologyEntry with confidence="low" so the pipeline keeps
        moving.
        """
        ctx = state["context"]
        papers = ctx.get("deduplicated_results", []) or []

        # Sort by final_rank when it's an int (any value, including 0). Papers
        # without an int final_rank fall through to the unranked tail, which
        # preserves their insertion order.
        ranked = [p for p in papers if isinstance(p.get("final_rank"), int)]
        unranked = [p for p in papers if not isinstance(p.get("final_rank"), int)]
        ranked.sort(key=lambda p: p.get("final_rank", 0))
        ordered = ranked + unranked
        top_papers = ordered[:_METHODS_TOP_N]

        methodology_table: list[MethodologyEntry] = []
        for paper in top_papers:
            abstract = (paper.get("abstract") or "").strip()
            if not abstract:
                logger.info(
                    f"evaluate_methods: skipping paper {paper.get('paper_id') or paper.get('title')!r} "
                    f"(no abstract)"
                )
                continue

            entry = await _extract_methodology_for_paper(self.llm, paper)
            methodology_table.append(entry)

        ctx["methodology_table"] = methodology_table

        logger.info(
            f"evaluate_methods: processed {len(methodology_table)} papers "
            f"(out of {len(top_papers)} with abstracts, top-{_METHODS_TOP_N} of {len(papers)})"
        )
        return state

    @staticmethod
    def _extract_concepts(paper: dict) -> list[str]:
        """Extract concept strings from a paper.

        Preference order: paper-level `fields_of_study` → source-level
        `fields_of_study` (or `concepts`) → regex noun extraction from
        title + abstract. Returns a deduplicated, lower-cased list.
        """
        fos = paper.get("fields_of_study")
        if isinstance(fos, list) and fos:
            return [str(c).strip().lower() for c in fos if c]

        for src in paper.get("sources", []) or []:
            if not isinstance(src, dict):
                continue
            src_fos = (
                src.get("fields_of_study")
                or src.get("concepts")
                or src.get("fieldsOfStudy")
            )
            if isinstance(src_fos, list) and src_fos:
                return [str(c).strip().lower() for c in src_fos if c]

        text = f"{paper.get('title', '') or ''} {paper.get('abstract', '') or ''}"
        nouns = re.findall(r"\b[A-Z][a-z]{3,}\b", text)
        return list({n.lower() for n in nouns})

    @staticmethod
    def _concepts_similar(a: str, b: str, max_distance: int = 3) -> bool:
        """Two concepts are similar when one is a substring of the other, or
        their Levenshtein distance is ≤ max_distance. Identical strings are
        not considered (same concept, not a gap)."""
        if a == b:
            return False
        if a in b or b in a:
            return True
        return levenshtein(a, b) <= max_distance

    @staticmethod
    def _percentile(values: list[int], p: float) -> float:
        """Linear-interpolation percentile (p in [0, 100])."""
        if not values:
            return 0.0
        s = sorted(values)
        n = len(s)
        if n == 1:
            return float(s[0])
        k = (p / 100.0) * (n - 1)
        f = int(k)
        c = min(f + 1, n - 1)
        if f == c:
            return float(s[f])
        return float(s[f] + (k - f) * (s[c] - s[f]))

    @staticmethod
    def _confidence_for_rank(rank: int) -> str:
        """Assign confidence by rank among the top-5 gap candidates.

        Rank 0 (lowest co-occurrence) → 'high'; ranks 1-2 → 'medium';
        ranks 3-4 → 'low'.
        """
        if rank == 0:
            return "high"
        if rank <= 2:
            return "medium"
        return "low"

    def _paper_stable_id(self, paper: dict, fallback: str) -> str:
        """Pick a stable id for a paper for inclusion in `supporting_papers`."""
        for key in ("paper_id", "doi", "arxiv_id"):
            val = paper.get(key)
            if val:
                return str(val)
        title = paper.get("title")
        if title:
            return f"title:{title}"
        return fallback

    async def _generate_gap_descriptions(
        self,
        candidates: list[tuple[str, str, int]],
    ) -> dict[str, str]:
        """Call the LLM once to produce a short description per candidate.

        Returns a dict mapping '1'..'N' → description. On any failure
        (LLM error, missing LLM, unparseable JSON), returns {} so callers
        can fall back to a templated description.
        """
        if not candidates or not self.llm:
            return {}

        lines = [
            f"{i + 1}. Concept A: {a} | Concept B: {b} | Co-occurrence weight: {w}"
            for i, (a, b, w) in enumerate(candidates)
        ]
        prompt = (
            "You are identifying under-explored research intersections in the\n"
            "academic literature. Each candidate below is a pair of related\n"
            "concepts with unusually low co-occurrence across the corpus.\n\n"
            f"Candidates ({len(candidates)}):\n" + "\n".join(lines) + "\n\n"
            "For each candidate, write a SINGLE concise sentence (≤ 25 words)\n"
            "describing the potential research gap or under-explored\n"
            "intersection. Return ONLY a JSON object with string keys '1'..'N'\n"
            "(where N is the number of candidates) and string values.\n"
            "No commentary, no markdown fences.\n\n"
            'Example: {"1": "...", "2": "..."}'
        )
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            text = (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            )
        except Exception as e:
            logger.warning(f"identify_gaps: LLM call failed: {e}")
            return {}

        parsed = _parse_llm_json(text)
        if not isinstance(parsed, dict):
            logger.warning(
                f"identify_gaps: could not parse descriptions JSON "
                f"(first 200 chars): {text[:200]!r}"
            )
            return {}
        return {str(k): str(v) for k, v in parsed.items() if v}

    async def identify_gaps(self, state: AgentState) -> AgentState:
        """Surface concept-level research gaps via co-occurrence analysis.

        Reads context["deduplicated_results"] (set by the `deduplicate`
        node) and writes context["gaps"] = list[ResearchGap]. Concept
        extraction prefers `fields_of_study` and falls back to a simple
        regex on title+abstract. A pair of similar concepts (Levenshtein
        ≤ 3 or substring) with co-occurrence at or below the 5th
        percentile of all pair weights is a gap candidate. The top 5
        candidates (by ascending weight) get a single LLM call for
        natural-language descriptions and confidence assigned by rank.
        """
        ctx = state["context"]
        papers = ctx.get("deduplicated_results", []) or []
        if len(papers) < 2:
            ctx["gaps"] = []
            return state

        concepts_per_paper: list[set[str]] = []
        paper_concept_lists: list[list[str]] = []
        for paper in papers:
            concepts = self._extract_concepts(paper)
            if len(concepts) < 2:
                continue
            paper_concept_lists.append(concepts)
            concepts_per_paper.append(set(concepts))

        if not concepts_per_paper:
            ctx["gaps"] = []
            return state

        pair_weights: dict[tuple[str, str], int] = {}
        pair_support: dict[tuple[str, str], list[str]] = {}
        for paper, concepts in zip(papers, concepts_per_paper):
            unique = sorted(concepts)
            paper_id = self._paper_stable_id(
                paper, fallback=f"paper_{papers.index(paper)}"
            )
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    pair = (unique[i], unique[j])
                    pair_weights[pair] = pair_weights.get(pair, 0) + 1
                    pair_support.setdefault(pair, []).append(paper_id)

        if not pair_weights:
            ctx["gaps"] = []
            return state

        weights = sorted(pair_weights.values())
        threshold = self._percentile(weights, 5)
        if threshold < 1:
            threshold = 1.0

        candidates: list[tuple[str, str, int, list[str]]] = []
        for (a, b), w in pair_weights.items():
            if w <= threshold and self._concepts_similar(a, b):
                candidates.append((a, b, w, pair_support[(a, b)]))

        if not candidates:
            ctx["gaps"] = []
            return state

        candidates.sort(key=lambda c: (c[2], c[0], c[1]))
        top5 = candidates[:5]

        llm_input = [(a, b, w) for a, b, w, _ in top5]
        descriptions = await self._generate_gap_descriptions(llm_input)

        max_weight = max(weights)
        gaps: list[ResearchGap] = []
        for rank, (a, b, w, supporting) in enumerate(top5):
            description = descriptions.get(str(rank + 1))
            if not description:
                description = (
                    f"Low co-occurrence ({w} paper{'s' if w != 1 else ''}) "
                    f"between '{a}' and '{b}' suggests an under-explored intersection."
                )
            gap_score = 1.0 - (w / max_weight) if max_weight > 0 else 0.0
            gaps.append(
                ResearchGap(
                    concept_a=a,
                    concept_b=b,
                    gap_score=round(gap_score, 4),
                    supporting_papers=list(supporting),
                    confidence=self._confidence_for_rank(rank),  # type: ignore[arg-type]
                    description=description,
                )
            )

        ctx["gaps"] = gaps

        logger.info(
            f"identify_gaps: {len(papers)} papers → {len(pair_weights)} pair weights, "
            f"{len(candidates)} similar candidates, returning top {len(gaps)}"
        )
        return state

    async def synthesize(self, state: AgentState) -> AgentState:
        """Build a ResearchDossier, apply hybrid ranking, and produce LLM synthesis."""
        ctx = state["context"]
        deduped: list[dict] = ctx.get("deduplicated_results", []) or []
        gaps: list[ResearchGap] = ctx.get("gaps", []) or []
        methodology_table: list[MethodologyEntry] = (
            ctx.get("methodology_table", []) or []
        )
        search_metadata_raw: dict = ctx.get("search_metadata", {}) or {}
        queries_used: list[str] = ctx.get("search_queries", [])
        expanded_used: list[str] = ctx.get("expanded_queries", [])
        s2_seed_id: str | None = ctx.get("recommendations_seed_id")

        logger.info(
            f"synthesize: {len(deduped)} deduped results, {len(gaps)} gaps, "
            f"{len(methodology_table)} methods"
        )

        if not deduped:
            state["output"] = "No papers found for your query."
            return state

        now = datetime.now()
        n = len(deduped)
        scored_papers: list[tuple[float, PaperRecord]] = []

        for raw in deduped:
            if not isinstance(raw, dict):
                continue

            raw_rank = raw.get("final_rank", 0)
            relevance_score = 1.0 - (raw_rank / max(n - 1, 1)) if n > 1 else 1.0

            citation_count = raw.get("citation_count", 0) or 0
            try:
                citation_count = int(citation_count)
            except (TypeError, ValueError):
                citation_count = 0
            citation_normalized = min(citation_count / 100, 1.0)

            year = raw.get("year")
            try:
                year_int: int | None = int(year) if year is not None else None
            except (TypeError, ValueError):
                year_int = None
            recency_score = (
                max(0.0, min(1.0, math.exp(-0.1 * (2026 - year_int))))
                if year_int is not None
                else 0.0
            )

            composite = (
                0.50 * relevance_score
                + 0.30 * citation_normalized
                + 0.20 * recency_score
            )

            merged_sources: list[str] = raw.get("merged_sources", []) or []
            source_list: list[PaperSource] = []
            for src_name in merged_sources:
                coerced = _coerce_source_name(src_name)
                if coerced is not None:
                    source_list.append(
                        PaperSource(
                            source=coerced,
                            matched_in=raw.get("matched_in", ["title"]) or ["title"],
                            fetched_at=now,
                            raw_id=raw.get("paper_id", ""),
                        )
                    )

            doi_val = raw.get("doi")
            arxiv_val = raw.get("arxiv_id")
            url_val = raw.get("url")
            paper_id = _resolve_paper_id(
                doi=doi_val if isinstance(doi_val, str) else None,
                arxiv_id=arxiv_val if isinstance(arxiv_val, str) else None,
                paper_id=raw.get("paper_id"),
                url=url_val if isinstance(url_val, str) else None,
                title=raw.get("title") if isinstance(raw.get("title"), str) else None,
            )

            authors = raw.get("authors") or []
            if not isinstance(authors, list):
                authors = [str(authors)]
            authors = [str(a) for a in authors]

            record = PaperRecord(
                paper_id=paper_id,
                doi=doi_val if isinstance(doi_val, str) else None,
                arxiv_id=arxiv_val if isinstance(arxiv_val, str) else None,
                title=raw.get("title") or "",
                authors=authors,
                year=year_int,
                venue=raw.get("venue") if isinstance(raw.get("venue"), str) else None,
                citation_count=citation_count,
                abstract=raw.get("abstract")
                if isinstance(raw.get("abstract"), str)
                else None,
                sources=source_list,
                relevance_score=round(relevance_score, 4),
                recency_score=round(recency_score, 4),
                final_rank=0,
            )
            scored_papers.append((composite, record))

        scored_papers.sort(key=lambda x: x[0], reverse=True)
        papers: list[PaperRecord] = []
        for rank, (_, rec) in enumerate(scored_papers):
            papers.append(rec.model_copy(update={"final_rank": rank}))

        search_metadata: SearchMetadata | None = None
        if search_metadata_raw:
            try:
                search_metadata = SearchMetadata(**search_metadata_raw)
            except Exception:
                logger.warning(
                    "synthesize: failed to build SearchMetadata from raw dict"
                )

        dossier = ResearchDossier(
            papers=papers,
            gaps=gaps,
            methodologies=methodology_table,
            search_metadata=search_metadata,
            generated_at=now,
        )
        ctx["research_dossier"] = dossier

        legacy_results: list[dict] = []
        for p in papers:
            legacy_results.append(
                {
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "authors": p.authors,
                    "year": p.year,
                    "venue": p.venue,
                    "citation_count": p.citation_count,
                    "doi": p.doi,
                    "arxiv_id": p.arxiv_id,
                    "abstract": p.abstract,
                    "source": p.sources[0].source if p.sources else "",
                    "url": p.doi and f"https://doi.org/{p.doi}" or "",
                }
            )
        ctx["search_results"] = legacy_results

        async def _verify(r: dict) -> tuple[dict, dict]:
            title = r.get("title", "Untitled")
            doi = r.get("doi")
            verification = await verify_paper_exists(title, doi)
            return r, verification

        verification_tasks = [_verify(r) for r in legacy_results[:15]]
        verification_results = await asyncio.gather(*verification_tasks)

        verified_results: list[dict] = []
        for r, verification in verification_results:
            if verification["verified"]:
                r["verified"] = True
                r["verification_source"] = verification["source"]
                verified_results.append(r)

        lines: list[str] = []
        for r in verified_results:
            title = r.get("title", "Untitled")
            authors = r.get("authors", []) or []
            year = r.get("year")
            source = r.get("source", "")
            citations = r.get("citation_count")
            abstract = r.get("abstract")
            verified = r.get("verified", False)

            authors_str = ", ".join(authors[:3]) + ("..." if len(authors) > 3 else "")
            verified_tag = " ✓" if verified else ""
            line = (
                f"- **{title}**{verified_tag} ({year or 'N/A'})\n"
                f"  Authors: {authors_str}\n"
                f"  Source: {source} | Citations: {citations or 'N/A'}"
            )
            if abstract:
                line += f"\n  {abstract[:200]}..."
            lines.append(line)

        results_text = "\n\n".join(lines)
        queries_text = ", ".join(queries_used)
        expanded_text = (
            f"\nLLM-expanded queries (synonyms/related concepts): {', '.join(expanded_used)}"
            if expanded_used
            else ""
        )
        seed_text = (
            f"\nS2 recommendations seed paperId: {s2_seed_id}" if s2_seed_id else ""
        )

        top5 = papers[:5]
        top5_text = (
            "\n".join(
                f"  - {p.title} ({p.year or 'N/A'}) [{p.citation_count} cites]"
                for p in top5
            )
            or "  (none)"
        )

        gaps_text = (
            "\n".join(
                f"  - {g.concept_a} ↔ {g.concept_b}: {g.description}" for g in gaps[:3]
            )
            or "  (none)"
        )

        methods_text = (
            "\n".join(
                f"  - {m.method_name} on {m.dataset}: {m.result}"
                for m in methodology_table[:5]
            )
            or "  (none)"
        )

        synthesis_prompt = (
            f"Search queries used: {queries_text}{expanded_text}{seed_text}\n\n"
            f"Found {len(verified_results)} verified papers (out of {len(deduped)} total). "
            f"Papers marked with ✓ have been verified in academic databases. "
            f"ONLY cite papers marked with ✓ in your review.\n\n"
            f"Top papers:\n{top5_text}\n\n"
            f"Research gaps:\n{gaps_text}\n\n"
            f"Methodology highlights:\n{methods_text}\n\n"
            f"Results:\n{results_text}"
        )

        response = await self._run_strategy(
            state["messages"] + [HumanMessage(content=synthesis_prompt)],
            tools=[],
        )
        state["output"] = response.content

        usage = getattr(response, "additional_kwargs", {}).get("usage")
        if usage:
            existing = state["context"].get("_usage", {})
            if existing:
                usage = {
                    "input_tokens": usage.get("input_tokens", 0)
                    + existing.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0)
                    + existing.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                    + existing.get("total_tokens", 0),
                }
            state["context"]["_usage"] = usage
        return state

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        graph.add_node("search_papers", self.search_papers)
        graph.add_node("deduplicate", self.deduplicate)
        graph.add_node("evaluate_methods", self.evaluate_methods)
        graph.add_node("identify_gaps", self.identify_gaps)
        graph.add_node("synthesize", self.synthesize)

        graph.set_entry_point("search_papers")
        graph.add_edge("search_papers", "deduplicate")
        graph.add_edge("deduplicate", "evaluate_methods")
        graph.add_edge("evaluate_methods", "identify_gaps")
        graph.add_edge("identify_gaps", "synthesize")
        graph.add_edge("synthesize", END)

        return graph
