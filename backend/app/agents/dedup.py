"""Fuzzy paper deduplication using DOI, arXiv ID, and Levenshtein distance."""

from __future__ import annotations

import re
import string
from typing import Any


def normalize_title(title: str) -> str:
    table = str.maketrans("", "", string.punctuation)
    cleaned = title.translate(table).lower().strip()
    return " ".join(cleaned.split())


def levenshtein(a: str, b: str) -> int:
    """Standard DP Levenshtein distance. O(m*n) time, O(min(m,n)) space."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    if len(a) < len(b):
        a, b = b, a

    prev = list(range(len(b) + 1))
    curr = [0] * (len(b) + 1)

    for i, ca in enumerate(a, 1):
        curr[0] = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + cost,
            )
        prev, curr = curr, prev

    return prev[len(b)]


def are_titles_duplicate(t1: str, t2: str, threshold: int = 2) -> bool:
    """True if Levenshtein distance ≤ threshold on normalized titles, or one is a substring of the other."""
    n1 = normalize_title(t1)
    n2 = normalize_title(t2)
    if n1 == n2:
        return True
    if n1 in n2 or n2 in n1:
        return True
    return levenshtein(n1, n2) <= threshold


def extract_arxiv_id(paper: dict[str, Any]) -> str | None:
    arxiv_id = paper.get("arxiv_id")
    if arxiv_id:
        return arxiv_id

    doi = paper.get("doi")
    if doi and "arxiv" in doi.lower():
        parts = doi.rsplit("/", 1)
        if len(parts) == 2:
            candidate = parts[1]
            if candidate.startswith("arXiv."):
                candidate = candidate[len("arXiv."):]
            return candidate

    url = paper.get("url", "") or ""
    m = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)", url)
    if m:
        return m.group(1)

    return None


# Metadata priority: higher value means more authoritative for that field.
_SOURCES_CITATION_PRIORITY = {"semantic_scholar": 3, "crossref": 2, "openalex": 1, "arxiv": 0}
_SOURCES_ABSTRACT_PRIORITY = {"openalex": 3, "semantic_scholar": 2, "arxiv": 1, "crossref": 0}


def _merge_papers(group: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    sources: list[str] = []

    merged["title"] = group[0].get("title", "")
    merged["merged_sources"] = sources

    for paper in group:
        src = paper.get("source", "unknown")
        sources.append(src)

        if not merged.get("doi") and paper.get("doi"):
            merged["doi"] = paper["doi"]

        existing_cc = merged.get("citation_count") or 0
        new_cc = paper.get("citation_count") or 0
        src_priority = _SOURCES_CITATION_PRIORITY.get(src, 0)
        existing_src = merged.get("source", "")
        existing_priority = _SOURCES_CITATION_PRIORITY.get(existing_src, 0)
        if new_cc > existing_cc or (new_cc == existing_cc and src_priority > existing_priority):
            merged["citation_count"] = new_cc

        existing_abs = merged.get("abstract")
        new_abs = paper.get("abstract")
        if new_abs:
            abs_priority = _SOURCES_ABSTRACT_PRIORITY.get(src, 0)
            existing_abs_priority = _SOURCES_ABSTRACT_PRIORITY.get(existing_src, 0)
            if not existing_abs or abs_priority > existing_abs_priority:
                merged["abstract"] = new_abs

        for key in ("year", "url", "venue", "arxiv_id", "authors", "external_id", "paper_id", "tldr"):
            if not merged.get(key) and paper.get(key):
                merged[key] = paper[key]

        if paper.get("source"):
            merged["source"] = paper["source"]

    merged["merged_sources"] = sources
    return merged


def deduplicate_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not papers:
        return []

    groups: list[list[dict[str, Any]]] = [[p] for p in papers]
    merged_indices: set[int] = set()

    doi_map: dict[str, list[int]] = {}
    for i, group in enumerate(groups):
        doi = (group[0].get("doi") or "").strip().lower()
        if doi:
            doi_map.setdefault(doi, []).append(i)

    doi_merged: set[int] = set()
    for indices in doi_map.values():
        if len(indices) < 2:
            continue
        primary = indices[0]
        for idx in indices[1:]:
            groups[primary].extend(groups[idx])
            doi_merged.add(idx)
        merged_indices |= doi_merged

    arxiv_map: dict[str, list[int]] = {}
    for i, group in enumerate(groups):
        if i in merged_indices:
            continue
        arxiv_id = extract_arxiv_id(group[0])
        if arxiv_id:
            arxiv_map.setdefault(arxiv_id, []).append(i)

    for indices in arxiv_map.values():
        if len(indices) < 2:
            continue
        primary = indices[0]
        for idx in indices[1:]:
            if idx in merged_indices:
                continue
            groups[primary].extend(groups[idx])
            merged_indices.add(idx)

    title_groups: list[list[int]] = []
    for i, group in enumerate(groups):
        if i in merged_indices:
            continue
        matched = False
        for tg in title_groups:
            representative = groups[tg[0]]
            if are_titles_duplicate(representative[0].get("title", ""), group[0].get("title", "")):
                tg.append(i)
                matched = True
                break
        if not matched:
            title_groups.append([i])

    for tg in title_groups:
        if len(tg) < 2:
            continue
        primary = tg[0]
        for idx in tg[1:]:
            groups[primary].extend(groups[idx])
            merged_indices.add(idx)

    results: list[dict[str, Any]] = []
    for i, group in enumerate(groups):
        if i in merged_indices:
            continue
        results.append(_merge_papers(group))

    return results
