# AI Company Knowledge Assistant

A local development project for exploring a company knowledge assistant. The current version includes a React frontend, a FastAPI backend, and PostgreSQL with the pgvector extension.

## Current features

- React and TypeScript frontend served by Vite.
- FastAPI health checks at `/api/health` and `/api/health/database`.
- Local PostgreSQL 16 with pgvector, started using Docker Compose.
- A Vite proxy that forwards frontend `/api` requests to FastAPI.
- Upload and text extraction for `.pdf`, `.docx`, and `.txt` files.
- Extracted text and document details are stored in the local database; original files are not retained.
- Extracted text is split into overlapping 1,000-character chunks for the next RAG stage.

No LLM service, API key, or paid service is configured.

## Run locally

The `.env` file contains local database credentials and is ignored by Git. For a fresh checkout, copy `.env.example` to `.env` and replace the example password with a private local password in both `POSTGRES_PASSWORD` and `DATABASE_URL`.

1. From the project root, start the database:

   ```powershell
   docker compose up -d db
   ```

2. In a terminal, start the backend:

   ```powershell
   Set-Location backend
   .\.venv\Scripts\Activate.ps1
   python migrate_chunks.py
   python -m uvicorn main:app --reload --env-file ..\.env
   ```

   If the virtual environment has not been created, run `python -m venv .venv` and `python -m pip install -r requirements.txt` first.

3. In a second terminal, start the frontend:

   ```powershell
   Set-Location frontend
   npm install
   npm run dev
   ```

   Open the local URL printed by Vite, usually `http://127.0.0.1:5173/`.

## Check the services

- Frontend: `http://127.0.0.1:5173/`
- API health: `http://127.0.0.1:8000/api/health`
- Database and pgvector health: `http://127.0.0.1:8000/api/health/database`
- Uploaded documents: `http://127.0.0.1:8000/api/documents`
- Interactive API docs: `http://127.0.0.1:8000/docs`

The database health check should return `{"status":"ok","database":"connected","pgvector":"enabled"}`.
Use the upload section in the frontend to add a PDF, Word, or text file. Files must be 5 MB or smaller. PDFs need selectable text; scanned-image OCR is not included.

To stop the database without removing its data, run `docker compose stop db`. Database data is stored in the `postgres_data` Docker volume.

## Project files

- `compose.yaml` — Defines the local PostgreSQL/pgvector container and persistent data volume.
- `.env.example` — Safe-to-commit template for local database settings; never commit `.env`.
- `backend/main.py` — FastAPI health checks and document upload/list routes.
- `backend/requirements.txt` — Python package dependencies.
- `backend/init.sql` — Enables pgvector and creates the documents table when the database is first initialized.
- `backend/document_chunks.sql` — Defines the table that stores extracted text chunks.
- `backend/chunking.py` — Splits extracted text into overlapping chunks.
- `backend/migrate_chunks.py` — Adds the chunk table and safely backfills documents already in the database.
- `frontend/src/App.tsx` — Main React page, API status, and document library UI.
- `frontend/src/lib/api.ts` — Typed frontend API requests for health checks and documents.
- `frontend/vite.config.ts` — Proxies API requests to the local backend during development.
- `.gitignore` — Excludes generated files and local credentials from Git.
