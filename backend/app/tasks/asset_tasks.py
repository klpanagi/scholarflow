"""Asset processing task for ARQ workers."""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import AsyncSessionLocal
from app.models import AgentConfig, AgentRole, Paper, PaperChunk
from app.services.analysis_service import analyze_paper
from app.services.pdf_service import pdf_service
from app.services.search_service import search_service

logger = logging.getLogger(__name__)


async def process_asset_task(
    ctx: dict,
    asset_id: str,
    owner_id: str,
    title: str,
    abstract: str | None,
    doc_type: str,
    full_text: str,
    sections: list[dict],
    references: list[dict],  # noqa: ARG001 — kept for API compat, not used
) -> dict:
    """Process uploaded asset: chunk, embed, index, analyze.

    Called by ARQ worker. All args are JSON-serializable (UUIDs as str).
    """
    asset_uuid = UUID(asset_id)
    owner_uuid = UUID(owner_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Paper).where(Paper.id == asset_uuid))
        asset = result.scalar_one_or_none()
        if not asset:
            return {"status": "error", "error": "asset not found"}

        logger.info("Asset %s: starting processing", asset.title)

        section_chunks = _chunk_sections(sections, full_text)
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
                            "owner_id": str(owner_uuid),
                            "chunk_index": i,
                            "section": chunk.get("section"),
                            "title": title,
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
            analyzer_model, analyzer_provider = await _get_analyzer_config_task(db, owner_uuid)
            analysis = await asyncio.wait_for(
                analyze_paper(
                    title=title,
                    abstract=abstract or "",
                    full_text=full_text[:50000],
                    doc_type=doc_type,
                    model=analyzer_model,
                    provider=analyzer_provider,
                ),
                timeout=90,
            )
            if analysis is not None:
                asset.analysis = analysis.model_dump()
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



