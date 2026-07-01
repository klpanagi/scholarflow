"""Asset processing task for ARQ workers."""

import asyncio
import json
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import AsyncSessionLocal
from app.models import AgentConfig, AgentRole, Paper, PaperChunk
from app.services.analysis_service import analyze_paper
from app.services.minio_service import minio_service
from app.services.pdf_service import pdf_service
from app.services.search_service import search_service
from app.services.system_settings import get_setting

logger = logging.getLogger(__name__)

DEFAULT_EXTRACTION_METHOD = "grobid"


async def process_asset_task(
    ctx: dict,
    asset_id: str,
) -> dict:
    """Process uploaded asset: extract, chunk, embed, index, analyze.

    Fully autonomous — loads the Paper from DB, downloads the file from
    MinIO, selects the extraction method from SystemSettings, extracts
    structured content, stores extraction_meta in Paper.analysis,
    chunks, embeds, indexes in ES, and runs LLM analysis.
    """
    asset_uuid = UUID(asset_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Paper).where(Paper.id == asset_uuid))
        asset = result.scalar_one_or_none()
        if not asset:
            return {"status": "error", "error": "asset not found"}

        logger.info("Asset %s: starting processing", asset.title)

        method = DEFAULT_EXTRACTION_METHOD
        try:
            raw = await get_setting(db, "extraction_method")
            if raw and raw.strip().lower() in ("grobid", "pymupdf", "tika"):
                method = raw.strip().lower()
        except Exception:
            pass

        try:
            pdf_bytes = await minio_service.download_file(asset.minio_key)
        except Exception as e:
            logger.error("Asset %s: MinIO download failed: %s", asset.title, e)
            asset.processing_status = "failed"
            await db.commit()
            return {"status": "error", "error": f"MinIO download failed: {e}"}

        asset.processing_status = "processing"
        await db.commit()

        try:
            extracted = await pdf_service.extract(pdf_bytes, method=method)
        except Exception as e:
            logger.error("Asset %s: extraction failed: %s", asset.title, e)
            asset.processing_status = "failed"
            await db.commit()
            return {"status": "error", "error": f"Extraction failed: {e}"}
        finally:
            del pdf_bytes

        asset.title = extracted.title or asset.title
        asset.authors = extracted.authors or asset.authors
        asset.abstract = extracted.abstract or asset.abstract
        if extracted.year:
            asset.year = extracted.year
        if extracted.venue:
            asset.venue = extracted.venue
        if extracted.doi:
            asset.doi = extracted.doi
        if extracted.arxiv_id:
            asset.arxiv_id = extracted.arxiv_id
        if extracted.doc_type and extracted.doc_type != "other":
            asset.doc_type = extracted.doc_type

        existing_analysis = asset.analysis or {}
        if isinstance(existing_analysis, str):
            existing_analysis = json.loads(existing_analysis)
        existing_analysis["extraction_meta"] = extracted.to_extraction_meta()
        asset.analysis = existing_analysis
        flag_modified(asset, "analysis")

        await db.commit()

        logger.info(
            "Asset %s: extracted via %s (%.1fs, %d sections, %d refs)",
            asset.title, extracted.source, extracted.extraction_time,
            len(extracted.sections), len(extracted.references),
        )

        sections_for_chunking = [
            {"name": s.get("heading", ""), "text": s.get("text", "")}
            for s in extracted.sections
        ]
        section_chunks = _chunk_sections(sections_for_chunking, extracted.full_text)
        logger.info("Asset %s: created %d chunks", asset.title, len(section_chunks))

        for i, chunk in enumerate(section_chunks):
            db.add(PaperChunk(
                paper_id=asset_uuid,
                chunk_index=i,
                section=chunk.get("section"),
                text=chunk["text"],
                embedding=None,
            ))
        await db.commit()

        embedding_errors = 0
        for i, chunk in enumerate(section_chunks):
            try:
                embedding = await asyncio.wait_for(
                    search_service.embed_text(chunk["text"]),
                    timeout=15,
                )
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning("Asset %s chunk %d embedding failed: %s", asset.title, i, e)
                embedding = None
                embedding_errors += 1

            try:
                await asyncio.wait_for(
                    search_service.index_document(
                        index="assets",
                        doc_id=f"{asset_uuid}_{i}",
                        document={
                            "text": chunk["text"],
                            "asset_id": str(asset_uuid),
                            "owner_id": str(asset.owner_id),
                            "chunk_index": i,
                            "section": chunk.get("section"),
                            "title": asset.title,
                        },
                        embedding=embedding,
                    ),
                    timeout=10,
                )
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning("Asset %s chunk %d ES index failed: %s", asset.title, i, e)

            chunk_obj = (await db.execute(
                select(PaperChunk).where(
                    PaperChunk.paper_id == asset_uuid,
                    PaperChunk.chunk_index == i,
                )
            )).scalar_one_or_none()
            if chunk_obj:
                chunk_obj.embedding = embedding
                flag_modified(chunk_obj, "embedding")
        await db.commit()

        try:
            analyzer_model, analyzer_provider = await _get_analyzer_config_task(db, asset.owner_id)
            analysis = await asyncio.wait_for(
                analyze_paper(
                    title=asset.title,
                    abstract=asset.abstract or "",
                    full_text=extracted.full_text[:50000],
                    doc_type=asset.doc_type,
                    model=analyzer_model,
                    provider=analyzer_provider,
                ),
                timeout=90,
            )
            if analysis is not None:
                existing = asset.analysis or {}
                if isinstance(existing, str):
                    existing = json.loads(existing)
                existing["llm_analysis"] = analysis.model_dump()
                asset.analysis = existing
                flag_modified(asset, "analysis")
        except (asyncio.TimeoutError, Exception) as e:
            logger.error("Asset %s analysis failed: %s", asset.title, e)

        asset.processing_status = "completed"
        await db.commit()

        logger.info(
            "Asset %s: completed (chunks=%d, embedding_errors=%d)",
            asset.title, len(section_chunks), embedding_errors,
        )
        return {
            "status": "completed",
            "asset_id": asset_id,
            "chunks": len(section_chunks),
            "embedding_errors": embedding_errors,
        }


def _chunk_sections(sections: list[dict], full_text: str) -> list[dict]:
    if sections:
        all_chunks: list[dict] = []
        for sec in sections:
            sec_text = sec.get("text", "")
            sec_name = sec.get("name", "")
            all_chunks.extend(_chunk_words(sec_text.split(), sec_name))
        return all_chunks
    return _chunk_text_list(full_text)


def _chunk_words(words: list[str], section: str | None, chunk_size: int = 800, overlap: int = 100) -> list[dict]:
    if not words:
        return []
    if len(words) <= chunk_size:
        return [{"text": " ".join(words), "section": section, "word_count": len(words)}]
    chunks: list[dict] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append({"text": " ".join(words[start:end]), "section": section, "word_count": end - start})
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def _chunk_text_list(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[dict]:
    words = text.split()
    return _chunk_words(words, None, chunk_size, overlap)


async def _get_analyzer_config_task(db, owner_id: UUID) -> tuple[str, str]:
    result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.user_id == owner_id,
            AgentConfig.role == AgentRole.ANALYZER,
        ).limit(1)
    )
    config = result.scalar_one_or_none()
    if config:
        return config.model, config.provider
    return "google/gemma-4-31b-it:free", "openrouter"



