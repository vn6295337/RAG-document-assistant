import { useState } from 'react';
import { embedChunks, clearIndex } from '../api/client';
import { processSelectedFiles } from '../api/dropbox';
import { chunkFiles } from '../api/chunker';
import ProcessingStatus from './ProcessingStatus';
import IndexSummary from './IndexSummary';
import CloudConnect from './CloudConnect';

export default function Sidebar({ onStatusChange, onAccessTokenChange }) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [processingState, setProcessingState] = useState(null);
  const [indexResult, setIndexResult] = useState(null);

  // New state for two-step flow
  const [stagedFiles, setStagedFiles] = useState([]);
  const [accessToken, setAccessToken] = useState(null);

  // Handle files staged from CloudConnect (not processed yet)
  const handleFilesStaged = (files) => {
    setStagedFiles(files);
    setMessage(null);
    setIndexResult(null);
  };

  // Handle access token from CloudConnect - propagate to parent for queries
  const handleAccessTokenChange = (token) => {
    setAccessToken(token);
    onAccessTokenChange?.(token); // Propagate to App for QueryPanel
    if (!token) {
      setStagedFiles([]);
    }
  };

  // Remove a single file from staged list
  const removeFile = (fileId) => {
    setStagedFiles(stagedFiles.filter(f => f.id !== fileId));
  };

  // Clear all staged files
  const clearStagedFiles = () => {
    setStagedFiles([]);
  };

  // Start indexing the staged files
  const handleIndexFiles = async () => {
    if (stagedFiles.length === 0 || !accessToken) return;

    setLoading(true);
    setMessage(null);
    setIndexResult(null);

    try {
      // Step 1: Read files from Dropbox
      setProcessingState({ step: 'read', fileName: `${stagedFiles.length} files`, progress: 10 });

      const fileContents = await processSelectedFiles(stagedFiles, accessToken, (progress) => {
        setProcessingState({
          step: 'read',
          fileName: progress.fileName,
          progress: 10 + (progress.current / progress.total) * 20,
        });
      });

      if (fileContents.length === 0) {
        setMessage({ type: 'error', text: 'No readable files found' });
        setLoading(false);
        setProcessingState(null);
        return;
      }

      // Step 2: Chunk files (client-side)
      setProcessingState({ step: 'chunk', fileName: `${fileContents.length} files`, progress: 35 });
      await new Promise(r => setTimeout(r, 100));

      const chunks = chunkFiles(fileContents);

      // Step 3: Clear existing index
      setProcessingState({ step: 'clear', fileName: 'Clearing old data', progress: 50 });
      await clearIndex();

      // Step 4: Send chunks to server for embedding
      setProcessingState({ step: 'embed', fileName: `${chunks.length} chunks`, progress: 65 });

      const result = await embedChunks(chunks);

      // Step 5: Show discard step
      setProcessingState({ step: 'discard', fileName: '', progress: 85 });
      await new Promise(r => setTimeout(r, 300));

      // Step 6: Complete
      setProcessingState({ step: 'save', fileName: '', progress: 100 });
      await new Promise(r => setTimeout(r, 200));

      if (result.status === 'success') {
        setIndexResult({
          files: fileContents.length,
          chunks: result.vectors_upserted,
        });
        setStagedFiles([]); // Clear staged files after successful indexing
        onStatusChange?.();
      } else {
        setMessage({ type: 'error', text: result.error || 'Embedding failed' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }

    setProcessingState(null);
    setLoading(false);
  };

  // Format file size
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-72 bg-slate-800 p-4 border-r border-slate-700 flex flex-col h-full overflow-auto">
      <h2 className="text-base font-semibold mb-4 text-slate-100">Document Source</h2>

      {/* Processing Status */}
      {processingState && (
        <div className="mb-4">
          <ProcessingStatus
            currentStep={processingState.step}
            fileName={processingState.fileName}
            progress={processingState.progress}
          />
        </div>
      )}

      {/* Index Result - dismissible */}
      {indexResult && !processingState && (
        <div className="mb-4">
          <IndexSummary
            files={indexResult.files}
            chunks={indexResult.chunks}
            onClose={() => setIndexResult(null)}
          />
        </div>
      )}

      {/* Cloud Storage - always visible when not processing */}
      {!processingState && (
        <div className="mb-4">
          <CloudConnect
            onFilesStaged={handleFilesStaged}
            stagedFiles={stagedFiles}
            onAccessTokenChange={handleAccessTokenChange}
          />
        </div>
      )}

      {/* Staged Files List */}
      {!processingState && stagedFiles.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-slate-300">
              Selected Files ({stagedFiles.length})
            </h3>
            <button
              type="button"
              onClick={clearStagedFiles}
              className="text-xs text-slate-400 hover:text-red-400 transition-colors"
            >
              Clear All
            </button>
          </div>
          <div className="bg-slate-900 border border-slate-700 rounded-lg divide-y divide-slate-700 max-h-48 overflow-auto">
            {stagedFiles.map(file => (
              <div key={file.id} className="flex items-center justify-between p-2.5 hover:bg-slate-800 group">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <svg className="w-4 h-4 text-slate-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 2l5 5h-5V4z"/>
                  </svg>
                  <div className="min-w-0">
                    <p className="text-sm text-slate-200 truncate">{file.name}</p>
                    <p className="text-xs text-slate-500">{formatSize(file.size)}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeFile(file.id)}
                  className="p-1 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                  aria-label={`Remove ${file.name}`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>

          {/* Index Button */}
          <button
            type="button"
            onClick={handleIndexFiles}
            disabled={loading || stagedFiles.length === 0}
            className="w-full mt-3 flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-blue-700 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-all duration-200"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Indexing...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                Index Selected Files
              </>
            )}
          </button>
        </div>
      )}

      {/* Error/Success Messages */}
      {message && (
        <div
          className={`p-3 rounded-lg text-sm mb-4 ${
            message.type === 'success'
              ? 'bg-green-900/30 border border-green-700 text-green-400'
              : 'bg-red-900/30 border border-red-700 text-red-400'
          }`}
          role="alert"
        >
          {message.text}
        </div>
      )}

    </div>
  );
}
