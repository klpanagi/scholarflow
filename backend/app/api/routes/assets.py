import asyncio
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import get_db
from app.core.arq import get_arq_pool
from app.core.security import get_current_user
from app.models import User, Paper, PaperChunk, AgentConfig, AgentRole
from app.schemas import PaperCreate, PaperResponse, PaperListResponse
from app.services.minio_service import minio_service
from app.services.pdf_service import pdf_service
from app.services.search_service import search_service
from app.services.analysis_service import analyze_paper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])


async def _get_analyzer_config(db: AsyncSession, owner_id: UUID) -> tuple[str, str]:
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


async def _get_user(user_id: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
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
        processing_status="processing",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    references = extracted.references or []
    full_text = extracted.full_text
    sections = extracted.sections or []

    del content, extracted

    try:
        pool = await get_arq_pool()
        job = await pool.enqueue_job(
            "process_asset_task",
            asset_id=str(asset.id),
            owner_id=str(current_user.id),
            title=asset.title,
            abstract=asset.abstract,
            doc_type=asset.doc_type,
            full_text=full_text,
            sections=sections,
            references=references,
        )
        if job:
            logger.info(f"Asset {asset.id} enqueued as ARQ job {job.job_id}")
    except Exception as e:
        logger.error(f"Failed to enqueue asset processing for {asset.id}: {e}")
        asset.processing_status = "failed"
        await db.commit()

    return asset


@router.post("/batch", response_model=list[PaperResponse], status_code=status.HTTP_201_CREATED)
async def upload_assets_batch(
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
            processing_status="processing",
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)

        references = extracted.references or []
        full_text = extracted.full_text
        sections = extracted.sections or []

        del content, extracted

        try:
            pool = await get_arq_pool()
            job = await pool.enqueue_job(
                "process_asset_task",
                asset_id=str(asset.id),
                owner_id=str(current_user.id),
                title=asset.title,
                abstract=asset.abstract,
                doc_type=asset.doc_type,
                full_text=full_text,
                sections=sections,
                references=references,
            )
            if job:
                logger.info(f"Asset {asset.id} enqueued as ARQ job {job.job_id}")
        except Exception as e:
            logger.error(f"Failed to enqueue asset processing for {asset.id}: {e}")
            asset.processing_status = "failed"
            await db.commit()

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
        model, provider = await _get_analyzer_config(db, current_user.id)
        analysis = await asyncio.wait_for(
            analyze_paper(
                title=asset.title, abstract=asset.abstract,
                full_text=full_text, doc_type=asset.doc_type,
                model=model, provider=provider,
            ), timeout=90,
        )
        if analysis:
            asset.analysis = analysis.model_dump()
            asset.tags = list(set((asset.tags or []) + analysis.keywords[:8]))
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Analysis failed — LLM returned empty or invalid response. Try a different provider.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Re-analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Analysis failed: {e}",
        )

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


@router.post("/{asset_id}/reprocess", response_model=PaperResponse)
async def reprocess_asset(
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

    err = await _reprocess_single_asset(asset, current_user, db)
    if err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=err)

    return asset


class ReprocessBatchRequest(BaseModel):
    asset_ids: list[str]


async def _reprocess_single_asset(
    asset: Paper, current_user: User, db: AsyncSession
) -> str | None:
    chunks_result = await db.execute(
        select(PaperChunk).where(PaperChunk.paper_id == asset.id)
    )
    for chunk in chunks_result.scalars().all():
        try:
            await search_service.delete_document("assets", f"{asset.id}_{chunk.chunk_index}")
        except Exception:
            pass
        await db.delete(chunk)
    await db.commit()

    try:
        file_data = await minio_service.download_file(asset.minio_key)
    except Exception as e:
        logger.warning(f"PDF not found for asset {asset.id}: {e}")
        return f"PDF not found: {e}"

    extracted = await pdf_service.extract_text(file_data)
    del file_data

    asset.processing_status = "processing"
    asset.embedding = None
    asset.es_doc_id = None
    await db.commit()

    try:
        pool = await get_arq_pool()
        job = await pool.enqueue_job(
            "process_asset_task",
            asset_id=str(asset.id),
            owner_id=str(current_user.id),
            title=asset.title,
            abstract=asset.abstract,
            doc_type=asset.doc_type,
            full_text=extracted.full_text,
            sections=extracted.sections or [],
            references=extracted.references or [],
        )
        if job:
            logger.info(f"Asset {asset.id} re-enqueued as ARQ job {job.job_id}")
    except Exception as e:
        logger.error(f"Failed to enqueue reprocessing for {asset.id}: {e}")
        asset.processing_status = "failed"
        await db.commit()
        return str(e)

    return None


@router.post("/reprocess-batch")
async def reprocess_batch(
    body: ReprocessBatchRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    asset_ids = [UUID(aid) for aid in body.asset_ids]

    result = await db.execute(
        select(Paper).where(
            Paper.id.in_(asset_ids), Paper.owner_id == current_user.id
        )
    )
    assets = result.scalars().all()

    if not assets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching assets found")

    enqueued = 0
    errors: list[str] = []
    for asset in assets:
        err = await _reprocess_single_asset(asset, current_user, db)
        if err:
            errors.append(f"{asset.title}: {err}")
        else:
            enqueued += 1

    return {
        "enqueued": enqueued,
        "total": len(assets),
        "errors": errors,
    }
