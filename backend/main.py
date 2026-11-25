from datetime import datetime
from io import BytesIO
import logging
import os
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from fastapi import FastAPI, File, HTTPException, UploadFile
from lxml.etree import XMLSyntaxError
import psycopg
from pydantic import BaseModel
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from chunking import chunk_text

app = FastAPI(title="AI Company Knowledge Assistant API")
logger = logging.getLogger(__name__)
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
MAX_DOCX_UNCOMPRESSED_SIZE = 20 * 1024 * 1024
MAX_PDF_PAGES = 100
PREVIEW_LENGTH = 240
ALLOWED_FILE_TYPES = {"txt", "pdf", "docx"}


class DocumentSummary(BaseModel):
    id: int
    filename: str
    file_type: str
    character_count: int
    preview: str
    uploaded_at: datetime
    chunk_count: int


def extract_text(file_type: str, file_content: bytes) -> str:
    if file_type == "txt":
        try:
            return file_content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise HTTPException(
                status_code=422,
                detail="Text files must use UTF-8 encoding",
            ) from error

    if file_type == "pdf":
        if not file_content.startswith(b"%PDF-"):
            raise HTTPException(status_code=422, detail="This is not a valid PDF file")

        try:
            pdf = PdfReader(BytesIO(file_content), strict=False)
            if pdf.is_encrypted:
                raise HTTPException(
                    status_code=422,
                    detail="Password-protected PDFs are not supported",
                )
            if len(pdf.pages) > MAX_PDF_PAGES:
                raise HTTPException(
                    status_code=413,
                    detail=f"PDFs must have {MAX_PDF_PAGES} pages or fewer",
                )
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except PdfReadError as error:
            raise HTTPException(
                status_code=422,
                detail="The PDF could not be read",
            ) from error

    if file_type == "docx":
        try:
            with ZipFile(BytesIO(file_content)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise HTTPException(
                        status_code=422,
                        detail="This is not a valid Word document",
                    )
                uncompressed_size = sum(item.file_size for item in archive.infolist())
                if uncompressed_size > MAX_DOCX_UNCOMPRESSED_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="The uncompressed Word document is too large",
                    )
            document = Document(BytesIO(file_content))
        except (BadZipFile, PackageNotFoundError, XMLSyntaxError, ValueError) as error:
            raise HTTPException(
                status_code=422,
                detail="The Word document could not be read",
            ) from error

        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                paragraphs.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(paragraphs)

    raise HTTPException(status_code=415, detail="This file type is not supported")


def document_summary(row: tuple[object, ...]) -> DocumentSummary:
    return DocumentSummary(
        id=row[0],
        filename=row[1],
        file_type=row[2],
        character_count=row[3],
        preview=row[4],
        uploaded_at=row[5],
        chunk_count=row[6],
    )


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health/database")
def database_health_check() -> dict[str, str]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL is not configured",
        )

    try:
        with psycopg.connect(database_url, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
                )
                vector_extension = cursor.fetchone()
    except psycopg.Error as error:
        logger.exception("Database health check failed")
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        ) from error

    if vector_extension is None:
        raise HTTPException(
            status_code=503,
            detail="The pgvector extension is not installed",
        )

    return {"status": "ok", "database": "connected", "pgvector": "enabled"}


@app.post("/api/documents", response_model=DocumentSummary, status_code=201)
def upload_document(file: UploadFile = File(...)) -> DocumentSummary:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")

    filename = PurePosixPath(file.filename.replace("\\", "/")).name
    if not filename or len(filename) > 255:
        raise HTTPException(
            status_code=400,
            detail="The filename must be between 1 and 255 characters",
        )

    file_type = PurePosixPath(filename).suffix.lower().lstrip(".")
    if file_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Supported file types are .txt, .pdf, and .docx",
        )

    file_content = file.file.read(MAX_UPLOAD_SIZE + 1)
    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Files must be 5 MB or smaller")

    extracted_text = extract_text(file_type, file_content)
    if not extracted_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text was found in the document",
        )
    chunks = chunk_text(extracted_text)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL is not configured",
        )

    try:
        with psycopg.connect(database_url, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO documents (filename, file_type, content, character_count)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, filename, file_type, character_count,
                              LEFT(content, %s), uploaded_at
                    """,
                    (
                        filename,
                        file_type,
                        extracted_text,
                        len(extracted_text),
                        PREVIEW_LENGTH,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise HTTPException(
                        status_code=500,
                        detail="The database did not return the saved document",
                    )

                cursor.executemany(
                    """
                    INSERT INTO document_chunks (document_id, chunk_index, content)
                    VALUES (%s, %s, %s)
                    """,
                    [
                        (row[0], index, chunk)
                        for index, chunk in enumerate(chunks)
                    ],
                )
                row = (*row, len(chunks))
    except psycopg.Error as error:
        logger.exception("Could not save uploaded document")
        raise HTTPException(
            status_code=503,
            detail="The document could not be saved",
        ) from error

    return document_summary(row)


@app.get("/api/documents", response_model=list[DocumentSummary])
def list_documents() -> list[DocumentSummary]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL is not configured",
        )

    try:
        with psycopg.connect(database_url, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT d.id, d.filename, d.file_type, d.character_count,
                           LEFT(d.content, %s), d.uploaded_at,
                           (
                               SELECT COUNT(*)
                               FROM document_chunks AS c
                               WHERE c.document_id = d.id
                           )
                    FROM documents AS d
                    ORDER BY d.uploaded_at DESC, d.id DESC
                    """,
                    (PREVIEW_LENGTH,),
                )
                rows = cursor.fetchall()
    except psycopg.Error as error:
        logger.exception("Could not list uploaded documents")
        raise HTTPException(
            status_code=503,
            detail="Documents could not be loaded",
        ) from error

    return [document_summary(row) for row in rows]
