import asyncio
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user
from app.models import User, Paper, PaperChunk
from app.schemas import PaperCreate, PaperResponse, PaperListResponse
from app.services.minio_service import minio_service
from app.services.pdf_service import pdf_service
from app.services.search_service import search_service
from app.services.analysis_service import analyze_paper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])


async def _get_user(user_id: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def _process_asset_background(
    asset_id: UUID,
    owner_id: UUID,
    title: str,
    abstract: str | None,
    doc_type: str,
    full_text: str,
    sections: list[dict],
    references: list[dict],
):
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Paper).where(Paper.id == asset_id))
            asset = result.scalar_one_or_none()
            if not asset:
                logger.warning(f"Background: asset {asset_id} not found")
                return

            if sections:
                section_chunks = pdf_service.chunk_sections(sections)
            else:
                section_chunks = [{"section": None, "text": t, "word_count": len(t.split())}
                                  for t in _chunk_text(full_text, chunk_size=1000, overlap=200)]

            for i, chunk in enumerate(section_chunks):
                chunk_text = chunk["text"]
                embedding = None
                try:
                    embedding = await asyncio.wait_for(search_service.embed_text(chunk_text), timeout=15)
                except Exception as e:
                    logger.warning(f"Embedding failed for chunk {i}: {e}")

                db.add(PaperChunk(
                    paper_id=asset.id, chunk_index=i,
                    section=chunk.get("section"), text=chunk_text, embedding=embedding,
                ))

                try:
                    await asyncio.wait_for(search_service.index_document(
                        index="assets", doc_id=f"{asset.id}_{i}",
                        document={
                            "asset_id": str(asset.id), "chunk_index": i,
                            "section": chunk.get("section"), "content": chunk_text,
                            "title": title, "owner_id": str(owner_id),
                        }, embedding=embedding,
                    ), timeout=10)
                except Exception as e:
                    logger.warning(f"ES indexing failed for chunk {i}: {e}")

            await db.commit()

            analysis_data = {}
            if references:
                analysis_data["references"] = [
                    {"index": r.get("index"), "text": r.get("text", ""),
                     "authors": r.get("authors", []), "year": r.get("year")}
                    for r in references if isinstance(r, dict)
                ]

            try:
                analysis = await asyncio.wait_for(
                    analyze_paper(title=title, abstract=abstract, full_text=full_text, doc_type=doc_type),
                    timeout=60,
                )
                if analysis:
                    asset.analysis = analysis.model_dump()
                    asset.analysis.update(analysis_data)
                    asset.tags = list(set((asset.tags or []) + analysis.keywords[:8]))
                else:
                    if analysis_data:
                        asset.analysis = analysis_data
                flag_modified(asset, "analysis")
                flag_modified(asset, "tags")
            except Exception as e:
                logger.warning(f"AI analysis failed: {e}")
                if analysis_data:
                    asset.analysis = analysis_data

            await db.commit()
            logger.info(f"Background processing complete for asset {asset_id}")

    except Exception as e:
        logger.error(f"Background processing crashed for asset {asset_id}: {e}")


@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    abstract: Optional[str] = Form(None),
    doc_type: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    content = await file.read()

    object_key = f"assets/{current_user.id}/{file.filename}"
    await minio_service.upload_file(content, object_key, content_type=file.content_type)

    extracted = await pdf_service.extract_text(content)

    asset = Paper(
        owner_id=current_user.id,
        title=title or extracted.title or file.filename,
        abstract=abstract or extracted.abstract,
        authors=extracted.authors,
        minio_key=object_key,
        doc_type=doc_type or extracted.doc_type,
        year=extracted.year,
        venue=extracted.venue,
        doi=extracted.doi,
        arxiv_id=extracted.arxiv_id,
        tags=[],
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    references = extracted.references or []
    full_text = extracted.full_text
    sections = extracted.sections or []

    del content, extracted

    background_tasks.add_task(
        _process_asset_background,
        asset_id=asset.id, owner_id=current_user.id,
        title=asset.title, abstract=asset.abstract, doc_type=asset.doc_type,
        full_text=full_text, sections=sections, references=references,
    )

    return asset


@router.post("/batch", response_model=list[PaperResponse], status_code=status.HTTP_201_CREATED)
async def upload_assets_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    doc_type: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    assets = []

    for file in files:
        content = await file.read()
        object_key = f"assets/{current_user.id}/{file.filename}"
        await minio_service.upload_file(content, object_key, content_type=file.content_type)

        extracted = await pdf_service.extract_text(content)

        asset = Paper(
            owner_id=current_user.id,
            title=extracted.title or file.filename,
            abstract=extracted.abstract,
            authors=extracted.authors,
            minio_key=object_key,
            doc_type=doc_type or extracted.doc_type,
            year=extracted.year,
            venue=extracted.venue,
            doi=extracted.doi,
            arxiv_id=extracted.arxiv_id,
            tags=[],
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)

        references = extracted.references or []
        full_text = extracted.full_text
        sections = extracted.sections or []

        del content, extracted

        background_tasks.add_task(
            _process_asset_background,
            asset_id=asset.id, owner_id=current_user.id,
            title=asset.title, abstract=asset.abstract, doc_type=asset.doc_type,
            full_text=full_text, sections=sections, references=references,
        )

        assets.append(asset)

    return assets


@router.post("/{asset_id}/analyze", response_model=PaperResponse)
async def analyze_asset(
    asset_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(Paper).where(Paper.id == asset_id, Paper.owner_id == current_user.id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    try:
        file_data = await minio_service.download_file(asset.minio_key)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PDF not found: {e}")

    extracted = await pdf_service.extract_text(file_data)
    del file_data

    full_text = extracted.full_text

    try:
        analysis = await asyncio.wait_for(
            analyze_paper(
                title=asset.title, abstract=asset.abstract,
                full_text=full_text, doc_type=asset.doc_type,
            ), timeout=60,
        )
        if analysis:
            asset.analysis = analysis.model_dump()
            asset.tags = list(set((asset.tags or []) + analysis.keywords[:8]))
        else:
            asset.analysis = asset.analysis or {}
    except Exception as e:
        logger.warning(f"Re-analysis failed: {e}")

    flag_modified(asset, "analysis")
    flag_modified(asset, "tags")

    await db.commit()
    return asset


@router.get("/", response_model=PaperListResponse)
async def list_assets(
    page: int = 1,
    size: int = 20,
    doc_type: Optional[str] = None,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    offset = (page - 1) * size

    query = select(Paper).where(Paper.owner_id == current_user.id)
    if doc_type:
        query = query.where(Paper.doc_type == doc_type)
    query = query.offset(offset).limit(size).order_by(Paper.created_at.desc())

    result = await db.execute(query)
    assets = result.scalars().all()

    count_query = select(Paper).where(Paper.owner_id == current_user.id)
    if doc_type:
        count_query = count_query.where(Paper.doc_type == doc_type)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return {"items": assets, "total": total, "page": page, "size": size}


@router.get("/search")
async def search_assets_endpoint(
    q: str = "",
    limit: int = 20,
    user_id: str = Depends(get_current_user),
):
    if not q.strip():
        return []
    results = await search_service.search(
        query=q, index="assets", limit=limit, owner_filter=user_id,
    )
    return results


@router.get("/{asset_id}", response_model=PaperResponse)
async def get_asset(
    asset_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(Paper).where(Paper.id == asset_id, Paper.owner_id == current_user.id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(Paper).where(Paper.id == asset_id, Paper.owner_id == current_user.id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    await minio_service.delete_file(asset.minio_key)

    chunks_result = await db.execute(
        select(PaperChunk).where(PaperChunk.paper_id == asset.id)
    )
    for chunk in chunks_result.scalars().all():
        try:
            await search_service.delete_document("assets", f"{asset.id}_{chunk.chunk_index}")
        except Exception:
            pass
        await db.delete(chunk)

    await db.delete(asset)
    await db.commit()


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
    return chunks
