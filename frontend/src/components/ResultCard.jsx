export default function ResultCard({ citation }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow-sm hover:shadow-md hover:border-slate-600 transition-all duration-200">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="text-sm font-mono text-blue-400 truncate max-w-[200px]">{citation.id}</span>
        </div>
        <span className="text-xs bg-blue-900/40 text-blue-400 px-2 py-1 rounded-full font-medium border border-blue-700">
          {(citation.score * 100)?.toFixed(0) || '0'}% match
        </span>
      </div>
      {citation.snippet && (
        <p className="text-sm text-slate-400 line-clamp-3 leading-relaxed">{citation.snippet}</p>
      )}
    </div>
  );
}
