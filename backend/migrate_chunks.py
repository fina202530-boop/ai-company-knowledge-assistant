import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from chunking import chunk_text


def migrate_existing_documents() -> None:
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    schema_path = Path(__file__).with_name("document_chunks.sql")
    schema_sql = schema_path.read_text(encoding="utf-8")
    total_documents = 0
    total_chunks = 0

    with psycopg.connect(database_url, connect_timeout=3) as connection:
        connection.execute(schema_sql)
        documents = connection.execute(
            """
            SELECT d.id, d.content
            FROM documents AS d
            WHERE NOT EXISTS (
                SELECT 1
                FROM document_chunks AS c
                WHERE c.document_id = d.id
            )
            ORDER BY d.id
            """
        ).fetchall()

        for document_id, content in documents:
            chunks = chunk_text(content)
            if not chunks:
                raise ValueError(
                    f"Document {document_id} has no text to split into chunks"
                )

            connection.cursor().executemany(
                """
                INSERT INTO document_chunks (document_id, chunk_index, content)
                VALUES (%s, %s, %s)
                """,
                [
                    (document_id, index, chunk)
                    for index, chunk in enumerate(chunks)
                ],
            )
            total_documents += 1
            total_chunks += len(chunks)

    print(
        f"Chunk migration complete: {total_documents} existing document(s), "
        f"{total_chunks} chunk(s)."
    )


if __name__ == "__main__":
    migrate_existing_documents()
