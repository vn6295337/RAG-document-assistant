import { useState, useEffect, useRef } from 'react';
import { exchangeDropboxCode, getDropboxFolder } from '../api/client';

const DROPBOX_APP_KEY = import.meta.env.VITE_DROPBOX_APP_KEY;
const REDIRECT_URI = window.location.origin;

// Supported file extensions
const SUPPORTED_EXTENSIONS = ['.txt', '.md', '.pdf'];
const MAX_FILE_SIZE_MB = 5;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export default function CloudConnect({ onFilesStaged, stagedFiles = [], onAccessTokenChange }) {
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [showPicker, setShowPicker] = useState(false);
  const [files, setFiles] = useState([]);
  const [folders, setFolders] = useState([]);
  const [currentPath, setCurrentPath] = useState('');
  const [pathStack, setPathStack] = useState([]);
  const [pickerSelectedFiles, setPickerSelectedFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);

  const popupRef = useRef(null);
  const popupCheckInterval = useRef(null);

  // Listen for OAuth callback message from popup
  useEffect(() => {
    const handleMessage = async (event) => {
      // Verify origin for security
      if (event.origin !== window.location.origin) return;

      if (event.data?.type === 'DROPBOX_AUTH_CODE') {
        const { code, error: authError } = event.data;

        // Close popup
        if (popupRef.current && !popupRef.current.closed) {
          popupRef.current.close();
        }
        clearInterval(popupCheckInterval.current);

        if (authError) {
          setError(`Dropbox error: ${authError}`);
          setIsLoading(false);
          return;
        }

        if (code) {
          try {
            const data = await exchangeDropboxCode(code, REDIRECT_URI);
            if (data.access_token) {
              setAccessToken(data.access_token);
              setIsSignedIn(true);
              onAccessTokenChange?.(data.access_token);
            } else {
              setError(data.error || 'Failed to get access token');
            }
          } catch (err) {
            setError(err.message);
          }
          setIsLoading(false);
        }
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onAccessTokenChange]);

  // Check if this is the OAuth callback page (popup)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const errorParam = params.get('error');

    // If we have code/error and we're in a popup, send message to parent
    if ((code || errorParam) && window.opener) {
      window.opener.postMessage({
        type: 'DROPBOX_AUTH_CODE',
        code: code,
        error: errorParam
      }, window.location.origin);
      window.close();
    }
  }, []);

  // Fetch folder contents
  const fetchFolder = async (path) => {
    setLoadingFiles(true);
    setError(null);
    try {
      const data = await getDropboxFolder(path, accessToken);

      if (data.error) {
        setError(data.error);
        setLoadingFiles(false);
        return;
      }

      const entries = data.entries || [];
      const folderItems = entries.filter(item => item['.tag'] === 'folder');
      const fileItems = entries.filter(item => item['.tag'] === 'file');

      setFolders(folderItems);
      setFiles(fileItems);
    } catch (err) {
      setError(`Failed to load files: ${err.message}`);
    }
    setLoadingFiles(false);
  };

  // Check if file is supported
  const isFileSupported = (file) => {
    const name = file.name.toLowerCase();
    return SUPPORTED_EXTENSIONS.some(ext => name.endsWith(ext));
  };

  // Check if file size is within limit
  const isFileSizeOk = (file) => {
    return file.size <= MAX_FILE_SIZE_BYTES;
  };

  // Open picker
  const openPicker = () => {
    setShowPicker(true);
    setPickerSelectedFiles([]);
    setCurrentPath('');
    setPathStack([]);
    fetchFolder('');
  };

  // Navigate to folder
  const navigateToFolder = (folder) => {
    setPathStack([...pathStack, { path: currentPath, name: currentPath || 'Dropbox' }]);
    setCurrentPath(folder.path_lower);
    fetchFolder(folder.path_lower);
  };

  // Go back
  const goBack = () => {
    if (pathStack.length > 0) {
      const prev = pathStack[pathStack.length - 1];
      setPathStack(pathStack.slice(0, -1));
      setCurrentPath(prev.path);
      fetchFolder(prev.path);
    }
  };

  // Toggle file selection in picker
  const toggleFile = (file) => {
    if (!isFileSupported(file)) return;
    if (!isFileSizeOk(file)) return;

    if (pickerSelectedFiles.find(f => f.id === file.id)) {
      setPickerSelectedFiles(pickerSelectedFiles.filter(f => f.id !== file.id));
    } else {
      setPickerSelectedFiles([...pickerSelectedFiles, file]);
    }
  };

  // Confirm selection - adds to staged files
  const confirmSelection = () => {
    // Merge with existing staged files, avoiding duplicates
    const existingIds = new Set(stagedFiles.map(f => f.id));
    const newFiles = pickerSelectedFiles.filter(f => !existingIds.has(f.id));
    const merged = [...stagedFiles, ...newFiles];
    onFilesStaged?.(merged);
    setShowPicker(false);
  };

  const handleConnect = () => {
    if (!DROPBOX_APP_KEY) {
      setError('Dropbox App Key not configured');
      return;
    }

    setIsLoading(true);
    setError(null);

    const authUrl = new URL('https://www.dropbox.com/oauth2/authorize');
    authUrl.searchParams.set('client_id', DROPBOX_APP_KEY);
    authUrl.searchParams.set('response_type', 'code');
    authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
    authUrl.searchParams.set('token_access_type', 'offline');

    // Open popup window for OAuth
    const width = 500;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    popupRef.current = window.open(
      authUrl.toString(),
      'dropbox-auth',
      `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes`
    );

    // Check if popup was blocked
    if (!popupRef.current || popupRef.current.closed) {
      setError('Popup blocked. Please allow popups for this site.');
      setIsLoading(false);
      return;
    }

    // Monitor popup - if user closes it manually
    popupCheckInterval.current = setInterval(() => {
      if (popupRef.current && popupRef.current.closed) {
        clearInterval(popupCheckInterval.current);
        setIsLoading(false);
      }
    }, 500);
  };

  const handleDisconnect = () => {
    setAccessToken(null);
    setIsSignedIn(false);
    setShowPicker(false);
    onAccessTokenChange?.(null);
    onFilesStaged?.([]);
  };

  // Get display name for current path
  const getCurrentFolderName = () => {
    if (!currentPath) return 'Dropbox';
    const parts = currentPath.split('/');
    return parts[parts.length - 1] || 'Dropbox';
  };

  // Format file size
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (!DROPBOX_APP_KEY) {
    return (
      <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-3 text-sm text-yellow-400" role="alert">
        <p className="font-medium">Dropbox not configured</p>
        <p className="text-xs mt-1 text-yellow-500">Set VITE_DROPBOX_APP_KEY in environment</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-400" role="alert">
          {error}
        </div>
      )}

      {!isSignedIn ? (
        <div className="space-y-3">
          <button
            type="button"
            onClick={handleConnect}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-sm font-medium text-slate-200 hover:bg-slate-600 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-all duration-200"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#0061FF">
                <path d="M12 6.5l-6 3.75L12 14l6-3.75L12 6.5zM6 14l6 3.75L18 14l-6 3.75L6 14zM6 10.25L0 6.5l6-3.75 6 3.75-6 3.75zM18 10.25l6-3.75-6-3.75-6 3.75 6 3.75z"/>
              </svg>
            )}
            Connect Dropbox
          </button>
          <p className="text-xs text-slate-500 text-center">
            Supports {SUPPORTED_EXTENSIONS.join(', ')} (max {MAX_FILE_SIZE_MB} MB)
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Connection status */}
          <div className="flex items-center justify-between text-sm bg-green-900/30 border border-green-700 rounded-lg px-3 py-2">
            <div className="flex items-center gap-2 text-green-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Connected to Dropbox</span>
            </div>
            <button
              type="button"
              onClick={handleDisconnect}
              className="text-xs text-green-400 hover:text-green-300 font-medium"
              aria-label="Disconnect from Dropbox"
            >
              Disconnect
            </button>
          </div>

          {/* Select files button */}
          <button
            type="button"
            onClick={openPicker}
            className="w-full flex items-center justify-center gap-2 bg-slate-700 border border-slate-600 text-slate-200 rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-slate-600 active:scale-[0.98] shadow-sm transition-all duration-200"
          >
            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            {stagedFiles.length > 0 ? 'Add More Files' : 'Select Files'}
          </button>

          {/* File type hints */}
          <p className="text-xs text-slate-500 text-center">
            Supports {SUPPORTED_EXTENSIONS.join(', ')} (max {MAX_FILE_SIZE_MB} MB)
          </p>
        </div>
      )}

      {/* File Picker Modal */}
      {showPicker && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-xl">
            {/* Header */}
            <div className="p-4 border-b border-slate-700 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {pathStack.length > 0 && (
                  <button
                    type="button"
                    onClick={goBack}
                    className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                    aria-label="Go back"
                  >
                    <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                  </button>
                )}
                <h3 className="font-medium text-slate-100">{getCurrentFolderName()}</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowPicker(false)}
                className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                aria-label="Close picker"
              >
                <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* File list */}
            <div className="flex-1 overflow-auto p-3">
              {loadingFiles ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : (
                <div className="space-y-1">
                  {folders.map(folder => (
                    <div
                      key={folder.id}
                      onClick={() => navigateToFolder(folder)}
                      className="flex items-center gap-3 p-2.5 hover:bg-slate-700 rounded-lg cursor-pointer transition-colors"
                    >
                      <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
                      </svg>
                      <span className="text-sm text-slate-200">{folder.name}</span>
                    </div>
                  ))}
                  {files.map(file => {
                    const supported = isFileSupported(file);
                    const sizeOk = isFileSizeOk(file);
                    const selectable = supported && sizeOk;
                    const isSelected = pickerSelectedFiles.find(f => f.id === file.id);

                    return (
                      <div
                        key={file.id}
                        onClick={() => selectable && toggleFile(file)}
                        className={`flex items-center gap-3 p-2.5 rounded-lg transition-colors ${
                          !selectable
                            ? 'opacity-50 cursor-not-allowed'
                            : isSelected
                            ? 'bg-blue-900/40 border border-blue-700 cursor-pointer'
                            : 'hover:bg-slate-700 cursor-pointer'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={!!isSelected}
                          disabled={!selectable}
                          onChange={() => {}}
                          className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500"
                        />
                        <svg className="w-5 h-5 text-slate-500" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 2l5 5h-5V4z"/>
                        </svg>
                        <div className="flex-1 min-w-0">
                          <span className="text-sm text-slate-200 truncate block">{file.name}</span>
                          <span className="text-xs text-slate-500">
                            {formatSize(file.size)}
                            {!supported && ' - Unsupported format'}
                            {supported && !sizeOk && ' - File too large'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                  {folders.length === 0 && files.length === 0 && (
                    <div className="text-center py-12">
                      <svg className="w-12 h-12 text-slate-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                      </svg>
                      <p className="text-slate-500 text-sm">This folder is empty</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-slate-700 flex items-center justify-between bg-slate-800/50 rounded-b-xl">
              <span className="text-sm text-slate-400">
                {pickerSelectedFiles.length} file(s) selected
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowPicker(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmSelection}
                  disabled={pickerSelectedFiles.length === 0}
                  className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                  Add Selected
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
