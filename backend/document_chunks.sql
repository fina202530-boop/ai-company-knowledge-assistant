CREATE TABLE IF NOT EXISTS document_chunks (
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    PRIMARY KEY (document_id, chunk_index)
);
