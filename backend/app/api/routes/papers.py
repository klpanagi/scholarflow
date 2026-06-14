import asyncio
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Paper, PaperChunk
from app.schemas import PaperCreate, PaperResponse, PaperListResponse
from app.services.minio_service import minio_service
from app.services.pdf_service import pdf_service
from app.services.search_service import search_service
from app.services.analysis_service import analysis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["papers"])


async def _get_user(user_id: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def upload_paper(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    abstract: Optional[str] = Form(None),
    doc_type: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    content = await file.read()

    object_key = f"papers/{current_user.id}/{file.filename}"
    await minio_service.upload_file(content, object_key, content_type=file.content_type)

    extracted = await pdf_service.extract_text(content)

    paper = Paper(
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
    db.add(paper)
    await db.commit()
    await db.refresh(paper)

    if extracted.sections:
        section_chunks = pdf_service.chunk_sections(extracted.sections)
        for i, chunk in enumerate(section_chunks):
            embedding = None
            try:
                embedding = await asyncio.wait_for(search_service.embed_text(chunk["text"]), timeout=15)
            except Exception as e:
                logger.warning(f"Embedding failed for chunk {i}: {e}")

            chunk_record = PaperChunk(
                paper_id=paper.id,
                chunk_index=i,
                section=chunk["section"],
                text=chunk["text"],
                embedding=embedding,
            )
            db.add(chunk_record)

            try:
                await asyncio.wait_for(search_service.index_document(
                    index="papers",
                    doc_id=f"{paper.id}_{i}",
                    document={
                        "paper_id": str(paper.id),
                        "chunk_index": i,
                        "section": chunk["section"],
                        "content": chunk["text"],
                        "title": paper.title,
                        "owner_id": str(current_user.id),
                    },
                    embedding=embedding,
                ), timeout=10)
            except Exception as e:
                logger.warning(f"ES indexing failed for chunk {i}: {e}")
    else:
        text_chunks = _chunk_text(extracted.full_text, chunk_size=1000, overlap=200)
        for i, chunk in enumerate(text_chunks):
            embedding = None
            try:
                embedding = await asyncio.wait_for(search_service.embed_text(chunk), timeout=15)
            except Exception as e:
                logger.warning(f"Embedding failed for chunk {i}: {e}")

            chunk_record = PaperChunk(
                paper_id=paper.id,
                chunk_index=i,
                text=chunk,
                embedding=embedding,
            )
            db.add(chunk_record)

            try:
                await asyncio.wait_for(search_service.index_document(
                    index="papers",
                    doc_id=f"{paper.id}_{i}",
                    document={
                        "paper_id": str(paper.id),
                        "chunk_index": i,
                        "content": chunk,
                        "title": paper.title,
                        "owner_id": str(current_user.id),
                    },
                    embedding=embedding,
                ), timeout=10)
            except Exception as e:
                logger.warning(f"ES indexing failed for chunk {i}: {e}")

    analysis_data = {}
    if extracted.references:
        analysis_data["references"] = [
            {"index": r.get("index"), "text": r.get("text", ""), "authors": r.get("authors", []), "year": r.get("year")}
            for r in extracted.references if isinstance(r, dict)
        ]

    try:
        summary = await asyncio.wait_for(
            analysis_service.generate_summary(
                title=paper.title,
                abstract=paper.abstract,
                full_text=extracted.full_text,
                doc_type=paper.doc_type,
            ),
            timeout=30,
        )
        auto_tags = await asyncio.wait_for(
            analysis_service.generate_tags(
                title=paper.title,
                abstract=paper.abstract,
                full_text=extracted.full_text,
            ),
            timeout=30,
        )
        summary["auto_tags"] = auto_tags
        summary.update(analysis_data)
        paper.analysis = summary
        paper.tags = list(set((paper.tags or []) + auto_tags))
    except Exception as e:
        logger.warning(f"AI analysis failed (non-blocking): {e}")
        if analysis_data:
            paper.analysis = analysis_data

    await db.commit()
    return paper


@router.post("/batch", response_model=list[PaperResponse], status_code=status.HTTP_201_CREATED)
async def upload_papers_batch(
    files: list[UploadFile] = File(...),
    doc_type: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    papers = []

    for file in files:
        content = await file.read()
        object_key = f"papers/{current_user.id}/{file.filename}"
        await minio_service.upload_file(content, object_key, content_type=file.content_type)

        extracted = await pdf_service.extract_text(content)

        paper = Paper(
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
        db.add(paper)
        await db.commit()
        await db.refresh(paper)

        if extracted.sections:
            section_chunks = pdf_service.chunk_sections(extracted.sections)
            for i, chunk in enumerate(section_chunks):
                embedding = None
                try:
                    embedding = await asyncio.wait_for(search_service.embed_text(chunk["text"]), timeout=15)
                except Exception:
                    pass
                db.add(PaperChunk(
                    paper_id=paper.id, chunk_index=i, section=chunk["section"],
                    text=chunk["text"], embedding=embedding,
                ))
                try:
                    await asyncio.wait_for(search_service.index_document(
                        index="papers", doc_id=f"{paper.id}_{i}",
                        document={"paper_id": str(paper.id), "chunk_index": i, "section": chunk["section"], "content": chunk["text"], "title": paper.title, "owner_id": str(current_user.id)},
                        embedding=embedding,
                    ), timeout=10)
                except Exception:
                    pass
        else:
            text_chunks = _chunk_text(extracted.full_text, chunk_size=1000, overlap=200)
            for i, chunk in enumerate(text_chunks):
                embedding = None
                try:
                    embedding = await asyncio.wait_for(search_service.embed_text(chunk), timeout=15)
                except Exception:
                    pass
                db.add(PaperChunk(paper_id=paper.id, chunk_index=i, text=chunk, embedding=embedding))

        analysis_data = {}
        if extracted.references:
            analysis_data["references"] = [
                {"index": r.get("index"), "text": r.get("text", ""), "authors": r.get("authors", []), "year": r.get("year")}
                for r in extracted.references if isinstance(r, dict)
            ]

        try:
            summary = await asyncio.wait_for(
                analysis_service.generate_summary(
                    title=paper.title, abstract=paper.abstract,
                    full_text=extracted.full_text, doc_type=paper.doc_type,
                ), timeout=30,
            )
            auto_tags = await asyncio.wait_for(
                analysis_service.generate_tags(
                    title=paper.title, abstract=paper.abstract, full_text=extracted.full_text,
                ), timeout=30,
            )
            summary["auto_tags"] = auto_tags
            summary.update(analysis_data)
            paper.analysis = summary
            paper.tags = list(set(auto_tags))
        except Exception as e:
            logger.warning(f"AI analysis failed for batch file {file.filename}: {e}")
            if analysis_data:
                paper.analysis = analysis_data
        papers.append(paper)

    await db.commit()
    return papers


@router.post("/{paper_id}/analyze", response_model=PaperResponse)
async def analyze_paper(
    paper_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id, Paper.owner_id == current_user.id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    from app.services.minio_service import minio_service as ms

    try:
        file_data = await ms.download_file(paper.minio_key)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PDF file not found in storage: {e}")

    extracted = await pdf_service.extract_text(file_data)

    try:
        sw = await asyncio.wait_for(
            analysis_service.analyze_strengths_weaknesses(
                title=paper.title, abstract=paper.abstract,
                full_text=extracted.full_text, doc_type=paper.doc_type,
            ), timeout=60,
        )
        existing = paper.analysis or {}
        existing["strengths_weaknesses"] = sw
        paper.analysis = existing
    except Exception as e:
        logger.warning(f"Strength/weakness analysis failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {e}")

    await db.commit()
    return paper


@router.get("/", response_model=PaperListResponse)
async def list_papers(
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
    papers = result.scalars().all()

    count_query = select(Paper).where(Paper.owner_id == current_user.id)
    if doc_type:
        count_query = count_query.where(Paper.doc_type == doc_type)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return {"items": papers, "total": total, "page": page, "size": size}


@router.get("/search")
async def search_papers_endpoint(
    q: str = "",
    limit: int = 20,
    user_id: str = Depends(get_current_user),
):
    if not q.strip():
        return []
    results = await search_service.search(
        query=q,
        index="papers",
        limit=limit,
        owner_filter=user_id,
    )
    return results


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id, Paper.owner_id == current_user.id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(
    paper_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id, Paper.owner_id == current_user.id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    await minio_service.delete_file(paper.minio_key)

    chunks_result = await db.execute(
        select(PaperChunk).where(PaperChunk.paper_id == paper.id)
    )
    for chunk in chunks_result.scalars().all():
        try:
            await search_service.delete_document("papers", f"{paper.id}_{chunk.chunk_index}")
        except Exception:
            pass
        await db.delete(chunk)

    await db.delete(paper)
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
