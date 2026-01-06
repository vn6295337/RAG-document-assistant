import { useState } from 'react';
import { runQuery } from '../api/client';
import ResultCard from './ResultCard';

export default function QueryPanel({ accessToken }) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showDebug, setShowDebug] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    if (!accessToken) {
      setError('Please connect to Dropbox first to enable zero-storage queries.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await runQuery(query, accessToken);
      setResult(data);
      if (data.error) {
        setError(data.error);
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const handleClear = () => {
    setQuery('');
    setResult(null);
    setError(null);
    setShowDebug(false);
  };

  return (
    <div className="flex-1 p-6 overflow-auto bg-slate-900">
      {/* Query Form */}
      <form onSubmit={handleSubmit} className="mb-6">
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Enter your question:
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What would you like to know?"
            className="flex-1 px-4 py-3 border border-slate-600 rounded-lg bg-slate-800 text-slate-100 placeholder-slate-500 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 focus:ring-offset-slate-900 focus:border-blue-500 transition-all duration-200"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-all duration-200"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Searching...
              </span>
            ) : (
              'Search'
            )}
          </button>
        </div>
      </form>

      {/* Error Message */}
      {error && (
        <div
          className="bg-red-900/30 border border-red-700 text-red-400 px-4 py-3 rounded-lg mb-6 flex items-start gap-3"
          role="alert"
        >
          <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Results */}
      {result && !error && (
        <div className="space-y-6">
          {/* Results Header with Clear Button */}
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-100">Answer</h2>
            <button
              type="button"
              onClick={handleClear}
              className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Clear Results
            </button>
          </div>

          {/* Answer Card */}
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow-sm">
            <p className="text-slate-200 whitespace-pre-wrap leading-relaxed">
              {result.answer || 'No answer generated.'}
            </p>
          </div>

          {/* Citations */}
          {result.citations?.length > 0 && (
            <div>
              <h2 className="text-base font-semibold text-slate-100 mb-3">
                Citations ({result.citations.length})
              </h2>
              <div className="space-y-3">
                {result.citations.map((citation, idx) => (
                  <ResultCard key={citation.id || idx} citation={citation} />
                ))}
              </div>
            </div>
          )}

          {/* Debug Toggle */}
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setShowDebug(!showDebug)}
              className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
            >
              <svg
                className={`w-4 h-4 transition-transform duration-200 ${showDebug ? 'rotate-90' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              {showDebug ? 'Hide Debug Info' : 'Show Debug Info'}
            </button>
            {showDebug && (
              <pre className="mt-3 bg-slate-950 text-slate-300 p-4 rounded-lg text-xs overflow-auto max-h-96 border border-slate-700">
                {JSON.stringify(result, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* Empty State - No query yet */}
      {!result && !error && !loading && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <svg className="w-16 h-16 text-slate-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <h3 className="text-lg font-medium text-slate-300 mb-2">Ask a Question</h3>
          <p className="text-sm text-slate-500 max-w-sm">
            {accessToken
              ? 'Enter a question above to search your indexed documents. Results will include relevant citations from your files.'
              : 'Connect to Dropbox and index your files first, then ask questions here. Your documents are re-fetched at query time for true zero-storage privacy.'
            }
          </p>
        </div>
      )}
    </div>
  );
}
