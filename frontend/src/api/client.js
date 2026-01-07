// Use environment variable for API URL, fallback to localhost for development
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/**
 * Run a query with zero-storage privacy
 * Requires Dropbox access token to re-fetch documents at query time
 */
export async function runQuery(query, accessToken, topK = 3) {
  const res = await fetch(`${API_BASE}/query-secure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      access_token: accessToken,
      top_k: topK
    })
  });
  return res.json();
}

export async function reindex(docsDir, outputPath = 'data/chunks.jsonl') {
  const res = await fetch(`${API_BASE}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ docs_dir: docsDir, output_path: outputPath })
  });
  return res.json();
}

export async function syncPinecone(chunksPath = 'data/chunks.jsonl') {
  const res = await fetch(`${API_BASE}/sync-pinecone`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chunks_path: chunksPath })
  });
  return res.json();
}

export async function getStatus(chunksPath = 'data/chunks.jsonl') {
  const res = await fetch(`${API_BASE}/status?chunks_path=${encodeURIComponent(chunksPath)}`);
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

/**
 * Clear all vectors from Pinecone index
 */
export async function clearIndex() {
  const res = await fetch(`${API_BASE}/clear-index`, {
    method: 'DELETE'
  });
  return res.json();
}

/**
 * Send pre-chunked text to server for embedding
 * Text is discarded immediately after embedding
 */
export async function embedChunks(chunks) {
  const res = await fetch(`${API_BASE}/embed-chunks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chunks })
  });
  return res.json();
}

/**
 * Exchange Dropbox authorization code for access token
 */
export async function exchangeDropboxCode(code, redirectUri) {
  const res = await fetch(`${API_BASE}/dropbox/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, redirect_uri: redirectUri })
  });
  return res.json();
}

/**
 * Get Dropbox folder contents via backend proxy
 */
export async function getDropboxFolder(path, accessToken) {
  const res = await fetch(`${API_BASE}/dropbox/folder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, access_token: accessToken })
  });
  return res.json();
}

/**
 * Get Dropbox file content via backend proxy
 */
export async function getDropboxFile(filePath, accessToken) {
  const res = await fetch(`${API_BASE}/dropbox/file`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: filePath, access_token: accessToken })
  });
  return res.json();
}

/**
 * Evaluate Docling parsing on a Dropbox file
 * Returns element breakdown and parsing metrics
 */
export async function evalParsing(filePath, accessToken) {
  const res = await fetch(`${API_BASE}/eval/parsing`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: filePath, access_token: accessToken })
  });
  return res.json();
}

/**
 * Get supported document formats for Docling parsing
 */
export async function getSupportedFormats() {
  const res = await fetch(`${API_BASE}/eval/formats`);
  return res.json();
}
