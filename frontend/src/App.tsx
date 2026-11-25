import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  fetchDocuments,
  fetchHealth,
  uploadDocument,
} from './lib/api'
import type { DocumentSummary } from './lib/api'
import './App.css'

type ConnectionState = 'checking' | 'connected' | 'disconnected'

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected error occurred'
}

function App() {
  const [connection, setConnection] = useState<ConnectionState>('checking')
  const [errorMessage, setErrorMessage] = useState('')
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')
  const [documentError, setDocumentError] = useState('')
  const [loadingDocuments, setLoadingDocuments] = useState(true)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const checkConnection = useCallback(async () => {
    setConnection('checking')
    setErrorMessage('')

    try {
      await fetchHealth()
      setConnection('connected')
    } catch (error) {
      setConnection('disconnected')
      setErrorMessage(getErrorMessage(error))
    }
  }, [])

  useEffect(() => {
    let isCurrent = true

    void fetchHealth()
      .then(() => {
        if (isCurrent) {
          setConnection('connected')
          setErrorMessage('')
        }
      })
      .catch((error: unknown) => {
        if (isCurrent) {
          setConnection('disconnected')
          setErrorMessage(getErrorMessage(error))
        }
      })

    return () => {
      isCurrent = false
    }
  }, [])

  useEffect(() => {
    let isCurrent = true

    void fetchDocuments()
      .then((items) => {
        if (isCurrent) {
          setDocuments(items)
          setDocumentError('')
        }
      })
      .catch((error: unknown) => {
        if (isCurrent) {
          setDocumentError(getErrorMessage(error))
        }
      })
      .finally(() => {
        if (isCurrent) {
          setLoadingDocuments(false)
        }
      })

    return () => {
      isCurrent = false
    }
  }, [])

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!selectedFile) {
      setUploadMessage('Choose a PDF, Word, or text file first.')
      return
    }

    setUploading(true)
    setUploadMessage('')
    setDocumentError('')

    try {
      const uploadedDocument = await uploadDocument(selectedFile)
      setDocuments((currentDocuments) => [
        uploadedDocument,
        ...currentDocuments,
      ])
      setSelectedFile(null)
      setUploadMessage(
        `${uploadedDocument.filename} added. Extracted ${uploadedDocument.character_count.toLocaleString()} characters into ${uploadedDocument.chunk_count.toLocaleString()} ${uploadedDocument.chunk_count === 1 ? 'chunk' : 'chunks'}.`,
      )
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (error) {
      setDocumentError(getErrorMessage(error))
    } finally {
      setUploading(false)
    }
  }

  const connectionLabel = {
    checking: 'Checking connection',
    connected: 'Backend connected',
    disconnected: 'Backend not connected',
  }[connection]

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Company Knowledge home">
          <span className="brand-mark" aria-hidden="true">K</span>
          <span>KNOWLEDGE<span className="brand-light"> / ASSISTANT</span></span>
        </a>
        <span className={`connection-pill ${connection}`}>
          <span className="status-dot" />
          {connectionLabel}
        </span>
      </header>

      <section className="hero">
        <p className="eyebrow">YOUR COMPANY, MORE CONNECTED</p>
        <h1>Find the knowledge<br />behind your next idea.</h1>
        <p className="intro">
          A thoughtful home for the documents, answers, and expertise your team
          already has.
        </p>
        <div className="status-card">
          <div className="status-copy">
            <span className="status-label">API STATUS</span>
            <strong>{connectionLabel}</strong>
            {errorMessage && <span className="error-message">{errorMessage}</span>}
          </div>
          <button
            className="check-button"
            type="button"
            onClick={() => void checkConnection()}
            disabled={connection === 'checking'}
          >
            {connection === 'checking' ? 'Checking...' : 'Check connection'}
          </button>
        </div>

        <section className="library" aria-labelledby="library-title">
          <div className="library-heading">
            <div>
              <p className="eyebrow">YOUR KNOWLEDGE LIBRARY</p>
              <h2 id="library-title">Bring your documents together.</h2>
            </div>
            <span className="document-count">
              {documents.length} {documents.length === 1 ? 'document' : 'documents'}
            </span>
          </div>

          <form className="upload-form" onSubmit={handleUpload}>
            <div className="file-picker">
              <span className="file-picker-icon" aria-hidden="true">+</span>
              <span className="file-picker-copy">
                <label htmlFor="document-file">Choose a document</label>
                <input
                  ref={fileInputRef}
                  id="document-file"
                  className="file-input"
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={(event) => {
                    setSelectedFile(event.target.files?.[0] ?? null)
                    setUploadMessage('')
                    setDocumentError('')
                  }}
                />
                <span>PDF, Word, or plain text · up to 5 MB</span>
              </span>
            </div>
            <button
              className="upload-button"
              type="submit"
              disabled={!selectedFile || uploading}
            >
              {uploading ? 'Adding document...' : 'Add document'}
            </button>
          </form>

          {uploadMessage && (
            <p className="upload-message" role="status">{uploadMessage}</p>
          )}
          {documentError && (
            <p className="document-error" role="alert">{documentError}</p>
          )}

          <div className="document-list" aria-live="polite">
            {loadingDocuments ? (
              <p className="empty-library">Loading your documents...</p>
            ) : documents.length === 0 ? (
              <p className="empty-library">
                Your library is empty. Add a document to get started.
              </p>
            ) : (
              documents.map((document) => (
                <article className="document-card" key={document.id}>
                  <div className="document-file-icon" aria-hidden="true">
                    {document.file_type.toUpperCase()}
                  </div>
                  <div className="document-details">
                    <div className="document-title-row">
                      <h3>{document.filename}</h3>
                      <span>
                        {document.chunk_count.toLocaleString()} {document.chunk_count === 1 ? 'chunk' : 'chunks'} · {document.character_count.toLocaleString()} characters
                      </span>
                    </div>
                    <p className="document-preview">{document.preview}</p>
                    <time dateTime={document.uploaded_at}>
                      {new Date(document.uploaded_at).toLocaleString()}
                    </time>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
      </section>

      <footer className="footer">
        <span>AI Company Knowledge Assistant</span>
        <span>Built for better answers.</span>
      </footer>
    </main>
  )
}

export default App
