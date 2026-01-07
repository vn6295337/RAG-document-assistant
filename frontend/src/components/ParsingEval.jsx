import { useState } from 'react';
import { evalParsing } from '../api/client';

export default function ParsingEval({ file, accessToken, onClose }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const runEval = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await evalParsing(file.path_lower, accessToken);
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch (err) {
      setError(err.message);
    }

    setLoading(false);
  };

  // Format number with commas
  const formatNumber = (num) => {
    return num?.toLocaleString() || '0';
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-xl">
        {/* Header */}
        <div className="p-4 border-b border-slate-700 flex items-center justify-between">
          <div>
            <h3 className="font-medium text-slate-100">Docling Parsing Evaluation</h3>
            <p className="text-sm text-slate-400 mt-0.5 truncate max-w-md">{file.name}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {!result && !loading && !error && (
            <div className="text-center py-8">
              <svg className="w-16 h-16 text-slate-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              <p className="text-slate-300 mb-2">Test Docling's document parsing</p>
              <p className="text-sm text-slate-500 mb-6">
                This will download the file and analyze how Docling extracts structure
              </p>
              <button
                type="button"
                onClick={runEval}
                className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 active:scale-[0.98] transition-all"
              >
                Run Parsing Evaluation
              </button>
            </div>
          )}

          {loading && (
            <div className="text-center py-12">
              <div className="w-10 h-10 border-3 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-slate-300">Parsing document with Docling...</p>
              <p className="text-sm text-slate-500 mt-2">This may take a moment for large files</p>
            </div>
          )}

          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-red-400 font-medium">Parsing failed</p>
                  <p className="text-sm text-red-300 mt-1">{error}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={runEval}
                className="mt-4 px-4 py-2 bg-slate-700 text-slate-200 rounded-lg text-sm hover:bg-slate-600 transition-colors"
              >
                Try Again
              </button>
            </div>
          )}

          {result && (
            <div className="space-y-6">
              {/* Status Badge */}
              <div className="flex items-center gap-2">
                {result.status === 'OK' ? (
                  <span className="flex items-center gap-1.5 bg-green-900/40 border border-green-700 text-green-400 px-3 py-1 rounded-full text-sm font-medium">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Parsing Successful
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 bg-red-900/40 border border-red-700 text-red-400 px-3 py-1 rounded-full text-sm font-medium">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    {result.status}
                  </span>
                )}
                <span className="text-slate-500 text-sm">{result.format?.toUpperCase()}</span>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-blue-400">{formatNumber(result.total_elements)}</p>
                  <p className="text-xs text-slate-500 mt-1">Elements</p>
                </div>
                <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-green-400">{formatNumber(result.total_chars)}</p>
                  <p className="text-xs text-slate-500 mt-1">Characters</p>
                </div>
                <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-purple-400">{formatNumber(result.total_words)}</p>
                  <p className="text-xs text-slate-500 mt-1">Words</p>
                </div>
                <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-orange-400">{result.page_count || '-'}</p>
                  <p className="text-xs text-slate-500 mt-1">Pages</p>
                </div>
              </div>

              {/* Element Types */}
              {result.element_types && Object.keys(result.element_types).length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-slate-300 mb-3">Element Types</h4>
                  <div className="bg-slate-900 border border-slate-700 rounded-lg divide-y divide-slate-700">
                    {Object.entries(result.element_types)
                      .sort((a, b) => b[1] - a[1])
                      .map(([type, count]) => (
                        <div key={type} className="flex items-center justify-between px-4 py-2.5">
                          <span className="text-slate-300 capitalize">{type.replace('_', ' ')}</span>
                          <span className="text-slate-400 font-mono">{count}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {/* Sample Elements */}
              {result.sample_elements && result.sample_elements.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-slate-300 mb-3">Sample Elements (first 10)</h4>
                  <div className="space-y-2">
                    {result.sample_elements.map((el, idx) => (
                      <div key={idx} className="bg-slate-900 border border-slate-700 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                            el.type === 'heading' ? 'bg-blue-900/50 text-blue-300' :
                            el.type === 'table' ? 'bg-purple-900/50 text-purple-300' :
                            el.type === 'list_item' ? 'bg-orange-900/50 text-orange-300' :
                            'bg-slate-700 text-slate-300'
                          }`}>
                            {el.type}
                          </span>
                          {el.level && (
                            <span className="text-xs text-slate-500">Level {el.level}</span>
                          )}
                        </div>
                        <p className="text-sm text-slate-400 break-words">{el.text || '(empty)'}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {result && (
          <div className="p-4 border-t border-slate-700 flex justify-end gap-2">
            <button
              type="button"
              onClick={runEval}
              className="px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 rounded-lg transition-colors"
            >
              Re-run
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
