export interface HealthResponse {
  status: 'ok'
}

export interface DocumentSummary {
  id: number
  filename: string
  file_type: 'txt' | 'pdf' | 'docx'
  character_count: number
  preview: string
  uploaded_at: string
  chunk_count: number
}

function isDocumentSummary(value: unknown): value is DocumentSummary {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  return (
    'id' in value &&
    typeof value.id === 'number' &&
    'filename' in value &&
    typeof value.filename === 'string' &&
    'file_type' in value &&
    (value.file_type === 'txt' ||
      value.file_type === 'pdf' ||
      value.file_type === 'docx') &&
    'character_count' in value &&
    typeof value.character_count === 'number' &&
    'preview' in value &&
    typeof value.preview === 'string' &&
    'uploaded_at' in value &&
    typeof value.uploaded_at === 'string' &&
    'chunk_count' in value &&
    typeof value.chunk_count === 'number'
  )
}

async function parseDocumentResponse(response: Response): Promise<DocumentSummary> {
  const data: unknown = await response.json()

  if (!response.ok) {
    const detail =
      typeof data === 'object' &&
      data !== null &&
      'detail' in data &&
      typeof data.detail === 'string'
        ? data.detail
        : `Request failed with HTTP ${response.status}`
    throw new Error(detail)
  }

  if (!isDocumentSummary(data)) {
    throw new Error('The backend returned an unexpected document response')
  }

  return data
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health')

  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`)
  }

  const data: unknown = await response.json()

  if (
    typeof data !== 'object' ||
    data === null ||
    !('status' in data) ||
    data.status !== 'ok'
  ) {
    throw new Error('The backend returned an unexpected health-check response')
  }

  return { status: data.status }
}

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  const response = await fetch('/api/documents')
  const data: unknown = await response.json()

  if (!response.ok) {
    const detail =
      typeof data === 'object' &&
      data !== null &&
      'detail' in data &&
      typeof data.detail === 'string'
        ? data.detail
        : `Request failed with HTTP ${response.status}`
    throw new Error(detail)
  }

  if (!Array.isArray(data) || !data.every(isDocumentSummary)) {
    throw new Error('The backend returned an unexpected documents response')
  }

  return data
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch('/api/documents', {
    method: 'POST',
    body: formData,
  })

  return parseDocumentResponse(response)
}
