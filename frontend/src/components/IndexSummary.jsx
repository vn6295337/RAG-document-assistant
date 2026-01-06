export default function IndexSummary({ files, chunks, onClose }) {
  return (
    <div className="bg-green-900/30 border border-green-700 rounded-lg p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 bg-green-900/50 rounded-full flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-green-300 mb-2">Indexing Complete</h3>

          <div className="space-y-1.5 text-sm text-green-400 mb-3">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>{files} file{files !== 1 ? 's' : ''} processed</span>
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" />
              </svg>
              <span>{chunks} chunk{chunks !== 1 ? 's' : ''} indexed</span>
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span className="font-medium">0 bytes stored on server</span>
            </div>
          </div>

          <p className="text-xs text-green-500 leading-relaxed">
            Your files remain in your cloud storage. Only searchable embeddings were saved.
          </p>

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="mt-3 text-sm text-green-400 hover:text-green-300 font-medium transition-colors"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
