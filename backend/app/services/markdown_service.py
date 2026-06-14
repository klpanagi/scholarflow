import io
import re
from dataclasses import dataclass

import fitz

from app.services.minio_service import minio_service


@dataclass
class MarkdownResult:
    markdown: str
    title: str | None
    page_count: int
    word_count: int
    minio_key: str | None = None


class MarkdownService:

    async def convert_pdf_to_markdown(self, pdf_data: bytes) -> MarkdownResult:
        doc = fitz.open(stream=io.BytesIO(pdf_data), filetype="pdf")
        pages_markdown = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            page_md = self._process_page(blocks, page_num + 1)
            if page_md.strip():
                pages_markdown.append(page_md)

        markdown = "\n\n---\n\n".join(pages_markdown)
        markdown = self._cleanup_markdown(markdown)
        title = self._extract_title(doc)
        word_count = len(markdown.split())

        return MarkdownResult(
            markdown=markdown,
            title=title,
            page_count=len(doc),
            word_count=word_count,
        )

    def _process_page(self, blocks: list, page_num: int) -> str:
        lines = []
        for block in blocks:
            if block["type"] != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans)
                if not text.strip():
                    continue
                max_size = max(s["size"] for s in spans)
                is_bold = any(s["flags"] & 16 for s in spans)
                if max_size >= 18:
                    lines.append(f"# {text.strip()}")
                elif max_size >= 15:
                    lines.append(f"## {text.strip()}")
                elif max_size >= 13 and is_bold:
                    lines.append(f"### {text.strip()}")
                elif is_bold and len(text.strip()) < 100:
                    lines.append(f"**{text.strip()}**")
                else:
                    lines.append(text.strip())
        return "\n".join(lines)

    def _extract_title(self, doc: fitz.Document) -> str | None:
        metadata = doc.metadata
        if metadata and metadata.get("title"):
            return metadata["title"].strip()
        if len(doc) > 0:
            page = doc[0]
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span["size"] >= 18 and span["text"].strip():
                            return span["text"].strip()
        return None

    def _cleanup_markdown(self, text: str) -> str:
        # Rejoin hyphenated words split across lines: "hyphen-\nated" → "hyphenated"
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Ensure blank line before markdown headings
        text = re.sub(r"\n(#{1,3} )", r"\n\n\1", text)
        # Strip standalone page numbers
        text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
        return text.strip()

    async def convert_and_store(
        self,
        pdf_data: bytes,
        paper_id: str,
        user_id: str,
    ) -> MarkdownResult:
        result = await self.convert_pdf_to_markdown(pdf_data)
        object_key = f"markdown/{user_id}/{paper_id}.md"
        md_bytes = result.markdown.encode("utf-8")
        await minio_service.upload_file(
            file_data=md_bytes,
            object_key=object_key,
            content_type="text/markdown",
            bucket_name="papers",
        )
        result.minio_key = object_key
        return result

    async def get_markdown(self, minio_key: str) -> str:
        data = await minio_service.download_file(object_key=minio_key)
        return data.decode("utf-8")


markdown_service = MarkdownService()
