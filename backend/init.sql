CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL CHECK (file_type IN ('txt', 'pdf', 'docx')),
    content TEXT NOT NULL,
    character_count INTEGER NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
