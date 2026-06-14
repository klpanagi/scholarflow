from langchain_core.tools import tool

from app.services.pdf_service import pdf_service
from app.services.minio_service import minio_service


@tool
async def extract_pdf_text(object_key: str) -> str:
    """Extract text content from a PDF stored in MinIO.

    Args:
        object_key: MinIO object key of the PDF
    """
    pdf_data = await minio_service.download_file(object_key)
    content = await pdf_service.extract_text(pdf_data)
    return content.full_text


@tool
async def extract_citations(object_key: str) -> list[dict]:
    """Extract citations from a PDF stored in MinIO.

    Args:
        object_key: MinIO object key of the PDF
    """
    pdf_data = await minio_service.download_file(object_key)
    return await pdf_service.extract_citations(pdf_data)
