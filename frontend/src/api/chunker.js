/**
 * Client-side text chunking utilities
 * Chunks text into smaller pieces for embedding
 * Tracks character positions for later re-extraction (zero-storage)
 */

const DEFAULT_CHUNK_SIZE = 500; // characters
const DEFAULT_OVERLAP = 50;

/**
 * Split text into chunks with overlap, tracking positions
 * Returns chunks with start/end character positions for re-extraction
 */
export function chunkText(text, options = {}) {
  const {
    chunkSize = DEFAULT_CHUNK_SIZE,
    overlap = DEFAULT_OVERLAP,
  } = options;

  if (!text || text.length === 0) {
    return [];
  }

  const chunks = [];
  let start = 0;

  while (start < text.length) {
    let end = Math.min(start + chunkSize, text.length);

    // Try to break at sentence boundary
    if (end < text.length) {
      const searchStart = Math.max(start + chunkSize - 100, start);
      const searchText = text.slice(searchStart, end + 50);
      const sentenceEnd = searchText.search(/[.!?]\s+/);
      if (sentenceEnd > 0) {
        end = searchStart + sentenceEnd + 1;
      }
    }

    const chunkText = text.slice(start, end).trim();
    if (chunkText.length > 0) {
      chunks.push({
        text: chunkText,
        startChar: start,
        endChar: end,
      });
    }

    // Move start with overlap
    start = end - overlap;
    if (start >= text.length - overlap) break;
  }

  return chunks;
}

/**
 * Chunk multiple files and prepare for embedding
 * Includes file path and character positions for re-fetching
 */
export function chunkFiles(files, options = {}) {
  const allChunks = [];

  for (const file of files) {
    const chunks = chunkText(file.content, options);

    chunks.forEach((chunk, index) => {
      allChunks.push({
        text: chunk.text,
        metadata: {
          filename: file.name,
          fileId: file.id,
          filePath: file.path, // Dropbox path for re-fetching
          chunkIndex: index,
          totalChunks: chunks.length,
          startChar: chunk.startChar,
          endChar: chunk.endChar,
        },
      });
    });
  }

  return allChunks;
}

/**
 * Estimate token count (rough approximation)
 */
export function estimateTokens(text) {
  // Rough estimate: ~4 characters per token for English
  return Math.ceil(text.length / 4);
}
