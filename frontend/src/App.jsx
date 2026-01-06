import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import QueryPanel from './components/QueryPanel';
import { getStatus } from './api/client';

export default function App() {
  const [status, setStatus] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [showPrivacyInfo, setShowPrivacyInfo] = useState(false);

  const fetchStatus = async () => {
    try {
      const data = await getStatus();
      setStatus(data);
    } catch (err) {
      console.error('Failed to fetch status:', err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div className="flex h-screen bg-slate-900">
      <Sidebar onStatusChange={fetchStatus} onAccessTokenChange={setAccessToken} />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-gradient-to-r from-slate-800 to-slate-800/80 border-b border-slate-700 px-6 py-4 flex-shrink-0">
          <div className="flex items-center justify-between">
            {/* Left: App title */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-semibold text-slate-100">RAG Document Assistant</h1>
                <p className="text-xs text-slate-400">Search your documents with AI</p>
              </div>
            </div>

            {/* Right: Zero Storage Badge with Tooltip */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowPrivacyInfo(!showPrivacyInfo)}
                className="flex items-center gap-1.5 bg-green-900/40 border border-green-700 rounded-md px-2.5 py-1.5 hover:bg-green-900/60 transition-colors cursor-pointer"
                aria-label="Learn about zero storage privacy"
              >
                <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span className="text-sm font-medium text-green-400">Zero Storage</span>
                <svg className={`w-3 h-3 text-green-400 transition-transform ${showPrivacyInfo ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Privacy Info Dropdown */}
              {showPrivacyInfo && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowPrivacyInfo(false)} />
                  <div className="absolute right-0 top-full mt-2 w-80 bg-slate-800 border border-slate-600 rounded-xl shadow-lg z-20 p-4">
                    <h3 className="font-semibold text-slate-100 mb-3 flex items-center gap-2">
                      <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                      </svg>
                      How Your Privacy Is Protected
                    </h3>
                    <ul className="space-y-2.5 text-sm text-slate-300">
                      <li className="flex gap-2">
                        <span className="text-green-400 mt-0.5">&#10003;</span>
                        <span><strong className="text-slate-200">No server storage</strong> - Your documents are never stored on our servers</span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-green-400 mt-0.5">&#10003;</span>
                        <span><strong className="text-slate-200">Embeddings only</strong> - Text is converted to mathematical vectors, then immediately purged</span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-green-400 mt-0.5">&#10003;</span>
                        <span><strong className="text-slate-200">Query-time re-fetch</strong> - Text is retrieved fresh from YOUR Dropbox for each search</span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-green-400 mt-0.5">&#10003;</span>
                        <span><strong className="text-slate-200">LLM processing</strong> - Your text is sent to AI models for answer generation (not stored)</span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-green-400 mt-0.5">&#10003;</span>
                        <span><strong className="text-slate-200">You control access</strong> - Disconnect Dropbox anytime to revoke all access</span>
                      </li>
                    </ul>
                    <div className="mt-3 pt-3 border-t border-slate-700 text-xs text-slate-400">
                      Embeddings cannot be reversed to reconstruct your original text.
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>
        <QueryPanel accessToken={accessToken} />
      </div>
    </div>
  );
}
