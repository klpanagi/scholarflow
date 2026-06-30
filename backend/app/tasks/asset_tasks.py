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
    references: list[dict],
) -> dict:
    """Process uploaded asset: chunk, embed, index, analyze.

    Called by ARQ worker. All args are JSON-serializable (UUIDs as str).
    """
    asset_uuid = UUID(asset_id)
    owner_uuid = UUID(owner_id)

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Paper).where(Paper.id == asset_uuid))
            asset = result.scalar_one_or_none()
            if not asset:
                raise ValueError(f"Asset {asset_id} not found")

            if sections:
                section_chunks = pdf_service.chunk_sections(sections)
            else:
                section_chunks = _chunk_text_list(full_text)

            for i, chunk in enumerate(section_chunks):
                chunk_text = chunk["text"]
                embedding = None
                try:
                    embedding = await asyncio.wait_for(
                        search_service.embed_text(chunk_text), timeout=15
                    )
                except Exception as e:
                    logger.warning(f"Embedding failed for chunk {i}: {e}")

                db.add(PaperChunk(
                    paper_id=asset_uuid, chunk_index=i,
                    section=chunk.get("section"), text=chunk_text, embedding=embedding,
                ))

                try:
                    await asyncio.wait_for(search_service.index_document(
                        index="assets",
                        doc_id=f"{asset_id}_{i}",
                        document={
                            "asset_id": asset_id, "chunk_index": i,
                            "section": chunk.get("section"), "content": chunk_text,
                            "title": title, "owner_id": owner_id,
                        }, embedding=embedding,
                    ), timeout=10)
                except Exception as e:
                    logger.warning(f"ES indexing failed for chunk {i}: {e}")

            await db.commit()

            asset.processing_status = "completed"
            await db.commit()

            analysis_data = _build_analysis_data(references)
            try:
                model, provider = await _get_analyzer_config_task(db, owner_uuid)
                analysis = await asyncio.wait_for(
                    analyze_paper(
                        title=title, abstract=abstract,
                        full_text=full_text, doc_type=doc_type,
                        model=model, provider=provider,
                    ),
                    timeout=90,
                )
                if analysis:
                    asset.analysis = analysis.model_dump()
                    asset.analysis.update(analysis_data)
                    asset.tags = list(set((asset.tags or []) + analysis.keywords[:8]))
                elif analysis_data:
                    asset.analysis = analysis_data
                flag_modified(asset, "analysis")
                flag_modified(asset, "tags")
            except Exception as e:
                logger.warning(f"AI analysis failed: {e}")
                if analysis_data:
                    asset.analysis = analysis_data

            await db.commit()
            logger.info(f"Asset processing complete for {asset_id}")

        return {"status": "completed", "asset_id": asset_id}

    except Exception as e:
        logger.error(f"Asset processing failed for {asset_id}: {e}")
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Paper).where(Paper.id == asset_uuid))
                asset = result.scalar_one_or_none()
                if asset:
                    asset.processing_status = "failed"
                    await db.commit()
        except Exception:
            logger.error(f"Failed to set failed status for asset {asset_id}")
        raise


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


def _build_analysis_data(references: list[dict]) -> dict:
    if not references:
        return {}
    return {"references": [
        {"index": r.get("index"), "text": r.get("text", ""),
         "authors": r.get("authors", []), "year": r.get("year")}
        for r in references if isinstance(r, dict)
    ]}


def _chunk_text_list(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[dict]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_text = " ".join(words[start:end])
        chunks.append({"section": None, "text": chunk_text, "word_count": len(chunk_text.split())})
        start = end - overlap
    return chunks
