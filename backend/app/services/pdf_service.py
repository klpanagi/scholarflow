"""PDF processing service using PyMuPDF and GROBID."""

import io
import re
from dataclasses import dataclass, field

import fitz
import httpx

from app.core.config import settings


@dataclass
class ExtractedContent:
    """Content extracted from a PDF."""

    title: str | None
    abstract: str | None
    full_text: str
    authors: list[str]
    references: list[dict]
    sections: list[dict]
    page_count: int
    doc_type: str
    metadata: dict = field(default_factory=dict)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None


class PDFService:
    """PDF text extraction, section parsing, and citation extraction."""

    SECTION_PATTERNS = [
        (r"^(?:\d+\.?\s+)?(?:I\s*\.?\s+)?INTRODUCTION", "introduction"),
        (r"^(?:\d+\.?\s+)?(?:II\s*\.?\s+)?(?:RELATED\s+)?(?:WORK|LITERATURE|BACKGROUND|PRIOR\s+WORK)", "related_work"),
        (r"^(?:\d+\.?\s+)?(?:III\s*\.?\s+)?(?:METHODOLOGY|METHODS?|APPROACH|EXPERIMENTAL\s+(?:DESIGN|SETUP)|PROPOSED\s+METHOD)", "methodology"),
        (r"^(?:\d+\.?\s+)?(?:IV\s*\.?\s+)?(?:EXPERIMENTS?|RESULTS?|EVALUATION|PERFORMANCE)", "results"),
        (r"^(?:\d+\.?\s+)?(?:V\s*\.?\s+)?(?:DISCUSSION|ANALYSIS|INTERPRETATION)", "discussion"),
        (r"^(?:\d+\.?\s+)?(?:VI\s*\.?\s+)?(?:CONCLUSIONS?|SUMMARY|FUTURE\s+WORK)", "conclusion"),
        (r"^(?:\d+\.?\s+)?(?:VII\s*\.?\s+)?(?:REFERENCES|BIBLIOGRAPHY|WORKS\s+CITED)", "references"),
        (r"^(?:\d+\.?\s+)?(?:VIII\s*\.?\s+)?(?:APPENDIX|APPENDICES|SUPPLEMENTARY)", "appendix"),
        (r"^(?:\d+\.?\s+)?ABSTRACT", "abstract"),
        (r"^(?:\d+\.?\s+)?ACKNOWLEDGMENTS?", "acknowledgments"),
    ]

    DOC_TYPE_SIGNALS = {
        "proposal": [
            "grant proposal", "research proposal", "project proposal", "funding request",
            "specific aims", "project summary", "budget justification", "broader impacts",
            "significance", "innovation", "research strategy", "feasibility",
        ],
        "review": [
            "systematic review", "literature review", "meta-analysis", "survey paper",
            "state of the art", "comprehensive review", "narrative review",
            "scoping review", "critical review",
        ],
        "report": [
            "technical report", "deliverable", "progress report", "final report",
            "interim report", "status report", "quarterly report",
        ],
    }

    async def extract_text(self, pdf_data: bytes) -> ExtractedContent:
        """Extract structured content from PDF using PyMuPDF."""
        doc = fitz.open(stream=io.BytesIO(pdf_data), filetype="pdf")

        pages = []
        for page in doc:
            pages.append(page.get_text())

        full_text = "\n\n".join(pages)

        title = self._extract_title(full_text, doc)
        abstract = self._extract_abstract(full_text)
        authors = self._extract_authors(full_text, doc)
        sections = self._extract_sections(full_text)
        references = self._extract_references(full_text)
        doc_type = self._detect_doc_type(full_text, title)
        metadata = self._extract_pdf_metadata(doc)
        year = self._extract_year(full_text, metadata)
        venue = self._extract_venue(full_text, metadata)
        doi = self._extract_doi(full_text, metadata)
        arxiv_id = self._extract_arxiv_id(full_text, metadata)

        return ExtractedContent(
            title=title,
            abstract=abstract,
            full_text=full_text,
            authors=authors,
            references=references,
            sections=sections,
            page_count=len(doc),
            doc_type=doc_type,
            metadata=metadata,
            year=year,
            venue=venue,
            doi=doi,
            arxiv_id=arxiv_id,
        )

    def _extract_title(self, full_text: str, doc: fitz.Document) -> str | None:
        """Extract title using PDF metadata, then first page heuristic."""
        meta_title = (doc.metadata.get("title") or "").strip()
        if meta_title and 5 < len(meta_title) < 300:
            return meta_title

        if doc.page_count > 0:
            page_text = doc[0].get_text()
            lines = [l.strip() for l in page_text.split("\n") if l.strip()]
            for line in lines[:10]:
                if any(skip in line.lower() for skip in ["@", "university", "institute", "department", "copyright", "proceedings", "conference", "journal"]):
                    continue
                if 10 < len(line) < 200:
                    return line
        return None

    def _extract_abstract(self, full_text: str) -> str | None:
        """Extract abstract using keyword detection."""
        text_lower = full_text.lower()

        for marker in ["abstract—", "abstract –", "abstract:", "abstract\n", "abstract "]:
            start = text_lower.find(marker)
            if start != -1:
                start += len(marker)
                end_candidates = []
                for end_marker in ["introduction", "keywords", "1. introduction", "1 introduction", "i. introduction", "categories and subject descriptors"]:
                    idx = text_lower.find(end_marker, start)
                    if idx != -1:
                        end_candidates.append(idx)
                end = min(end_candidates) if end_candidates else start + 1500

                abstract = full_text[start:end].strip()
                abstract = re.sub(r'\s+', ' ', abstract).strip()
                if len(abstract) > 50:
                    return abstract[:2000]
        return None

    def _extract_authors(self, full_text: str, doc: fitz.Document) -> list[str]:
        """Extract author names from PDF metadata or text heuristics."""
        meta_author = (doc.metadata.get("author") or "").strip()
        if meta_author and len(meta_author) > 2:
            authors = re.split(r'[;,&]|\band\b', meta_author)
            authors = [a.strip() for a in authors if a.strip() and len(a.strip()) > 1]
            if authors:
                return authors

        text_lower = full_text.lower()
        abstract_pos = text_lower.find("abstract")
        if abstract_pos > 0:
            header_text = full_text[:abstract_pos]
            lines = [l.strip() for l in header_text.split("\n") if l.strip()]
            name_pattern = re.compile(r'^[A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+$')
            authors = []
            for line in lines[1:15]:
                if name_pattern.match(line):
                    authors.append(line)
            if authors:
                return authors

        return []

    def _extract_year(self, full_text: str, metadata: dict) -> int | None:
        """Extract publication year from content or metadata."""
        creation = metadata.get("creation_date") or ""
        if creation:
            m = re.search(r'(\d{4})', str(creation))
            if m:
                year = int(m.group(1))
                if 1980 <= year <= 2030:
                    return year

        first_page = full_text[:2000]
        copyright_match = re.search(r'(?:©|\(c\)|Copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})', first_page, re.IGNORECASE)
        if copyright_match:
            year = int(copyright_match.group(1))
            if 1980 <= year <= 2030:
                return year

        year_matches = re.findall(r'\b(19[89]\d|20[0-3]\d)\b', first_page)
        if year_matches:
            return int(year_matches[-1])

        return None

    def _extract_venue(self, full_text: str, metadata: dict) -> str | None:
        """Extract venue/journal/conference name from text or metadata."""
        subject = (metadata.get("subject") or "").strip()
        if subject and len(subject) > 3:
            return subject

        first_page = full_text[:3000]
        # Conference: "Proceedings of the X" or "In Proceedings of X"
        venue_patterns = [
            r'(?:proceedings\s+of\s+(?:the\s+)?)((?:\d+(?:st|nd|rd|th)\s+)?(?:IEEE|ACM|AAAI|NeurIPS|ICML|ICLR|ACL|EMNLP|NAACL|CVPR|ICCV|ECCV|SIGMOD|VLDB|WWW|CHI|SIGCOMM|OSDI|SOSP|ISCA|MICRO|ASPLOS|PLDI|POPL|STOC|FOCS|SODA|CRYPTO|EUROCRYPT|USENIX|NSDI|ATC|EuroSys|Middleware|ICS|HPDC|SC|IPDPS|HPCC)[^,\n]{0,80})',
            r'(?:(?:published|accepted|submitted)\s+(?:in|to)\s+)((?:the\s+)?(?:journal\s+of|transactions?\s+on|proceedings\s+of|acm|ieee|springer|elsevier|wiley)[^,\n]{0,80})',
            r'(arxiv\s+preprint\s+arXiv:\d+\.\d+)',
        ]
        for pat in venue_patterns:
            m = re.search(pat, first_page, re.IGNORECASE)
            if m:
                venue = m.group(1).strip()
                if 5 < len(venue) < 200:
                    return venue

        return None

    def _extract_doi(self, full_text: str, metadata: dict) -> str | None:
        """Extract DOI from content or metadata."""
        keywords = (metadata.get("keywords") or "").strip()
        if keywords:
            doi_match = re.search(r'(10\.\d{4,}/[^\s,;]+)', keywords)
            if doi_match:
                return doi_match.group(1).rstrip('.')

        # Search first and last pages where DOIs typically appear
        search_text = full_text[:3000] + "\n" + full_text[-2000:]
        doi_match = re.search(r'(?:doi[:\s]*|https?://doi\.org/)?(10\.\d{4,}/[^\s,;<>"]+)', search_text, re.IGNORECASE)
        if doi_match:
            doi = doi_match.group(1) if doi_match.group(1).startswith('10.') else doi_match.group(0)
            doi = doi.rstrip('.,;:')
            if len(doi) > 7:
                return doi

        return None

    def _extract_arxiv_id(self, full_text: str, metadata: dict) -> str | None:
        """Extract arXiv ID from content."""
        search_text = full_text[:3000] + "\n" + full_text[-2000:]

        # arXiv:YYMM.NNNNN or arXiv:YYMM.NNNNNvN
        m = re.search(r'arXiv[:\s]+(\d{4}\.\d{4,5}(?:v\d+)?)', search_text, re.IGNORECASE)
        if m:
            return m.group(1)

        m = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)', search_text, re.IGNORECASE)
        if m:
            return m.group(1)

        return None

    def _extract_sections(self, full_text: str) -> list[dict]:
        """Split text into academic sections."""
        lines = full_text.split("\n")
        sections = []
        current_section = None
        current_text = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                current_text.append("")
                continue

            matched_section = None
            for pattern, section_name in self.SECTION_PATTERNS:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    matched_section = section_name
                    break

            if matched_section:
                if current_section and current_text:
                    section_text = "\n".join(current_text).strip()
                    if section_text:
                        sections.append({
                            "name": current_section,
                            "text": section_text,
                            "word_count": len(section_text.split()),
                        })
                current_section = matched_section
                current_text = []
            else:
                current_text.append(line_stripped)

        if current_section and current_text:
            section_text = "\n".join(current_text).strip()
            if section_text:
                sections.append({
                    "name": current_section,
                    "text": section_text,
                    "word_count": len(section_text.split()),
                })

        return sections

    def _extract_references(self, full_text: str) -> list[dict]:
        """Extract references/bibliography entries."""
        text_lower = full_text.lower()
        ref_start = None

        for marker in ["references", "bibliography", "works cited"]:
            idx = text_lower.rfind(marker)
            if idx != -1:
                ref_start = idx
                break

        if ref_start is None:
            return []

        ref_text = full_text[ref_start:]
        references = []

        numbered_pattern = re.compile(r'\[(\d+)\]\s*(.+?)(?=\[\d+\]|\Z)', re.DOTALL)
        matches = numbered_pattern.findall(ref_text)
        if matches:
            for num, text in matches:
                ref_text_clean = re.sub(r'\s+', ' ', text).strip()
                if ref_text_clean:
                    references.append({
                        "index": int(num),
                        "text": ref_text_clean,
                        "authors": self._parse_ref_authors(ref_text_clean),
                        "year": self._parse_ref_year(ref_text_clean),
                    })
            return references

        author_year_pattern = re.compile(
            r'([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)*\s*(?:et\s+al\.?)?)\s*'
            r'\((\d{4})\)\s*(.+?)(?=[A-Z][a-z]+.*?\(\d{4}\)|\Z)',
            re.DOTALL
        )
        matches = author_year_pattern.findall(ref_text)
        if matches:
            for i, (authors, year, text) in enumerate(matches):
                ref_text_clean = re.sub(r'\s+', ' ', text).strip()
                if ref_text_clean:
                    references.append({
                        "index": i + 1,
                        "text": f"{authors} ({year}) {ref_text_clean}",
                        "authors": [a.strip() for a in re.split(r',|\band\b', authors) if a.strip()],
                        "year": int(year),
                    })

        return references

    def _parse_ref_authors(self, ref_text: str) -> list[str]:
        """Parse authors from a reference string."""
        author_match = re.match(r'^([^.]+?)\s*[,(]', ref_text)
        if author_match:
            authors_str = author_match.group(1)
            authors = re.split(r',\s*|\band\b\s*', authors_str)
            return [a.strip() for a in authors if a.strip() and len(a.strip()) > 1]
        return []

    def _parse_ref_year(self, ref_text: str) -> int | None:
        """Parse year from a reference string."""
        year_match = re.search(r'\((\d{4})\)', ref_text)
        if year_match:
            year = int(year_match.group(1))
            if 1900 <= year <= 2030:
                return year
        return None

    def _detect_doc_type(self, full_text: str, title: str | None) -> str:
        """Detect document type from content signals."""
        text_lower = full_text.lower()[:5000]

        scores = {}
        for doc_type, signals in self.DOC_TYPE_SIGNALS.items():
            score = sum(1 for s in signals if s in text_lower)
            if score > 0:
                scores[doc_type] = score

        if scores:
            return max(scores, key=scores.get)

        has_abstract = "abstract" in text_lower
        has_intro = "introduction" in text_lower
        has_refs = "references" in text_lower
        if has_abstract and has_intro and has_refs:
            return "paper"

        return "other"

    def _extract_pdf_metadata(self, doc: fitz.Document) -> dict:
        """Extract PDF metadata."""
        metadata = doc.metadata
        return {
            "title": metadata.get("title"),
            "author": metadata.get("author"),
            "subject": metadata.get("subject"),
            "keywords": metadata.get("keywords"),
            "creator": metadata.get("creator"),
            "producer": metadata.get("producer"),
            "creation_date": metadata.get("creationDate"),
            "page_count": doc.page_count,
        }

    def chunk_sections(self, sections: list[dict], chunk_size: int = 800, overlap: int = 100) -> list[dict]:
        """Chunk sections into overlapping pieces, preserving section context."""
        chunks = []
        for section in sections:
            words = section["text"].split()
            if len(words) <= chunk_size:
                chunks.append({
                    "text": section["text"],
                    "section": section["name"],
                    "word_count": len(words),
                })
            else:
                start = 0
                while start < len(words):
                    end = min(start + chunk_size, len(words))
                    chunk_text = " ".join(words[start:end])
                    chunks.append({
                        "text": chunk_text,
                        "section": section["name"],
                        "word_count": end - start,
                    })
                    start = end - overlap
        return chunks

    async def extract_citations(self, pdf_data: bytes) -> list[dict]:
        """Extract citations using GROBID service."""
        if not settings.GROBID_URL:
            return []

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.GROBID_URL}/api/processFulltextDocument",
                files={"input": ("paper.pdf", pdf_data, "application/pdf")},
                timeout=60.0,
            )

            if response.status_code != 200:
                return []

            return []

    async def extract_metadata(self, pdf_data: bytes) -> dict:
        """Extract metadata from PDF."""
        doc = fitz.open(stream=io.BytesIO(pdf_data), filetype="pdf")
        return self._extract_pdf_metadata(doc)


pdf_service = PDFService()
