import { useState } from 'react';

/**
 * Display complete Docling parsing output with breakdown numbers
 * Shows all elements, element type counts, and stats
 */
export default function DoclingOutput({ results, onContinue, onDownload }) {
  const [expandedFiles, setExpandedFiles] = useState(
    // Expand first file by default
    results?.length > 0 ? { [results[0].filename]: true } : {}
  );

  const toggleFile = (filename) => {
    setExpandedFiles(prev => ({
      ...prev,
      [filename]: !prev[filename]
    }));
  };

  const formatNumber = (num) => {
    return num?.toLocaleString() || '0';
  };

  const handleDownload = () => {
    const dataStr = JSON.stringify(results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `docling-output-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    onDownload?.();
  };

  // Get element type badge color
  const getTypeColor = (type) => {
    const colors = {
      heading: 'bg-blue-900/50 text-blue-300 border-blue-700',
      paragraph: 'bg-slate-700 text-slate-300 border-slate-600',
      table: 'bg-purple-900/50 text-purple-300 border-purple-700',
      list_item: 'bg-orange-900/50 text-orange-300 border-orange-700',
      list: 'bg-orange-900/50 text-orange-300 border-orange-700',
      code: 'bg-green-900/50 text-green-300 border-green-700',
      image: 'bg-pink-900/50 text-pink-300 border-pink-700',
      caption: 'bg-yellow-900/50 text-yellow-300 border-yellow-700',
      formula: 'bg-cyan-900/50 text-cyan-300 border-cyan-700',
      footer: 'bg-gray-700 text-gray-300 border-gray-600',
      header: 'bg-gray-700 text-gray-300 border-gray-600',
    };
    return colors[type] || 'bg-slate-700 text-slate-300 border-slate-600';
  };

  if (!results || results.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        No parsing results available
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="p-4 border-b border-slate-700 flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Docling Parsing Results</h2>
            <p className="text-sm text-slate-400 mt-0.5">
              {results.length} file{results.length !== 1 ? 's' : ''} parsed
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleDownload}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-300 bg-slate-700 border border-slate-600 rounded-lg hover:bg-slate-600 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download JSON
            </button>
            <button
              type="button"
              onClick={onContinue}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Continue to Indexing
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content - Scrollable */}
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {results.map((doc, idx) => (
            <div key={idx} className="bg-slate-900 border border-slate-700 rounded-lg overflow-hidden">
              {/* File Header - Clickable */}
              <button
                type="button"
                onClick={() => toggleFile(doc.filename)}
                className="w-full p-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  <svg className={`w-5 h-5 text-slate-400 transition-transform ${expandedFiles[doc.filename] ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                  <svg className="w-5 h-5 text-slate-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 2l5 5h-5V4z"/>
                  </svg>
                  <span className="font-medium text-slate-200">{doc.filename}</span>
                </div>
                <div className="flex items-center gap-2">
                  {doc.status === 'OK' ? (
                    <span className="flex items-center gap-1 text-xs font-medium px-2 py-1 bg-green-900/40 border border-green-700 text-green-400 rounded">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      OK
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs font-medium px-2 py-1 bg-red-900/40 border border-red-700 text-red-400 rounded">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      {doc.status || 'ERROR'}
                    </span>
                  )}
                  <span className="text-xs text-slate-500 uppercase">{doc.format}</span>
                </div>
              </button>

              {/* Expanded Content */}
              {expandedFiles[doc.filename] && (
                <div className="border-t border-slate-700">
                  {doc.error ? (
                    <div className="p-4 bg-red-900/20 text-red-400 text-sm">
                      Error: {doc.error}
                    </div>
                  ) : (
                    <>
                      {/* Stats Grid */}
                      <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-center">
                          <p className="text-2xl font-bold text-blue-400">{formatNumber(doc.total_elements)}</p>
                          <p className="text-xs text-slate-500 mt-1">Elements</p>
                        </div>
                        <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-center">
                          <p className="text-2xl font-bold text-green-400">{formatNumber(doc.total_chars)}</p>
                          <p className="text-xs text-slate-500 mt-1">Characters</p>
                        </div>
                        <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-center">
                          <p className="text-2xl font-bold text-purple-400">{formatNumber(doc.total_words)}</p>
                          <p className="text-xs text-slate-500 mt-1">Words</p>
                        </div>
                        <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-center">
                          <p className="text-2xl font-bold text-orange-400">{doc.page_count || '-'}</p>
                          <p className="text-xs text-slate-500 mt-1">Pages</p>
                        </div>
                      </div>

                      {/* Element Types */}
                      {doc.element_types && Object.keys(doc.element_types).length > 0 && (
                        <div className="px-4 pb-4">
                          <h4 className="text-sm font-medium text-slate-400 mb-2">Element Types</h4>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(doc.element_types)
                              .sort((a, b) => b[1] - a[1])
                              .map(([type, count]) => (
                                <span
                                  key={type}
                                  className={`text-xs font-medium px-2 py-1 rounded border ${getTypeColor(type)}`}
                                >
                                  {type}: {count}
                                </span>
                              ))}
                          </div>
                        </div>
                      )}

                      {/* Complete Output */}
                      {doc.elements && doc.elements.length > 0 && (
                        <div className="px-4 pb-4">
                          <h4 className="text-sm font-medium text-slate-400 mb-2">
                            Complete Output ({doc.elements.length} elements)
                          </h4>
                          <div className="bg-slate-950 border border-slate-700 rounded-lg max-h-96 overflow-auto">
                            {doc.elements.map((el, elIdx) => (
                              <div
                                key={elIdx}
                                className="p-3 border-b border-slate-800 last:border-b-0 hover:bg-slate-900/50"
                              >
                                <div className="flex items-center gap-2 mb-1">
                                  <span className={`text-xs font-medium px-2 py-0.5 rounded border ${getTypeColor(el.type)}`}>
                                    {el.type}
                                  </span>
                                  {el.level && (
                                    <span className="text-xs text-slate-500">L{el.level}</span>
                                  )}
                                  {el.page && (
                                    <span className="text-xs text-slate-600">p.{el.page}</span>
                                  )}
                                </div>
                                <p className="text-sm text-slate-300 whitespace-pre-wrap break-words">
                                  {el.text || '(empty)'}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
