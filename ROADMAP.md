# Roadmap

## Known Issues & Technical Debt

### Content passed to chat and workflow agents is GROBID-extracted text, not raw PDF

Both the chat system and the workflow pipeline pass **GROBID-extracted, chunked text** (`PaperChunk.text`) to the LLM — not the raw PDF content. This has implications:

- **Chat**: `_build_asset_context()` reads chunks from the DB, or falls back to abstract-only if none exist. The LLM never sees the original PDF layout, figures, tables, or formatting.
- **Workflows**: `_fetch_paper_content()` builds a flat text blob from the same chunked text. The structured `grobid_dict` (`extraction_meta`) is also injected into agent context. Raw `pdf_bytes` is passed only for models that support native PDF input (checked via `model_supports_pdf()`).

**Why this matters**: GROBID extraction is lossy — figures, tables, equations, and formatting are stripped. For many tasks (literature review, detailed analysis), the LLM should have access to the original document, not just the extracted text.

**Possible fixes**:
- Pass `pdf_bytes` (already available from MinIO) to all model calls, not just PDF-native ones. Have the LLM service convert to a supported format when needed.
- Store extracted figures/tables from GROBID TEI and inject them as structured context alongside the text.
- Add a per-asset preference for "send raw PDF vs extracted text" toggle.
- Implement multi-modal fallback: try PDF-native first, fall back to extracted text.
