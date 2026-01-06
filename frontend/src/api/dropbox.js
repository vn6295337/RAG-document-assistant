/**
 * Dropbox API utilities for file access
 * Privacy: Files are fetched via backend proxy, processed client-side
 */

import { getDropboxFile } from './client';

/**
 * Fetch file content from Dropbox via backend proxy
 */
export async function fetchFileContent(filePath, accessToken) {
  const result = await getDropboxFile(filePath, accessToken);

  if (result.error) {
    throw new Error(result.error);
  }

  return result.content;
}

/**
 * Process selected files from Dropbox picker
 * Fetches content for each file and returns array of {name, content}
 */
export async function processSelectedFiles(files, accessToken, onProgress) {
  const results = [];

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    onProgress?.({ fileName: file.name, current: i + 1, total: files.length });

    try {
      const content = await fetchFileContent(file.path_lower, accessToken);
      if (content) {
        results.push({
          id: file.id,
          name: file.name,
          path: file.path_lower, // Store path for re-fetching at query time
          content: content
        });
      }
    } catch (error) {
      console.error(`Failed to read ${file.name}:`, error);
    }
  }

  return results;
}
