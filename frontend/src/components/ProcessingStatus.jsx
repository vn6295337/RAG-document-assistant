const steps = [
  { id: 'read', label: 'Reading from cloud storage' },
  { id: 'chunk', label: 'Chunking in your browser' },
  { id: 'clear', label: 'Clearing old index data' },
  { id: 'embed', label: 'Generating embeddings' },
  { id: 'discard', label: 'Text discarded (never stored)' },
  { id: 'save', label: 'Embeddings + file positions saved' },
];

export default function ProcessingStatus({ currentStep, fileName, progress }) {
  const getStepStatus = (stepId) => {
    const stepIndex = steps.findIndex(s => s.id === stepId);
    const currentIndex = steps.findIndex(s => s.id === currentStep);

    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex === currentIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <div className="animate-spin w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full"></div>
        <span className="font-medium text-slate-100 text-sm truncate">
          Indexing: {fileName}
        </span>
      </div>

      <div className="space-y-2.5 mb-4">
        {steps.map((step) => {
          const status = getStepStatus(step.id);
          return (
            <div key={step.id} className="flex items-center gap-2.5 text-sm">
              {status === 'completed' && (
                <div className="w-5 h-5 bg-green-900/50 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}
              {status === 'active' && (
                <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
              )}
              {status === 'pending' && (
                <div className="w-5 h-5 border-2 border-slate-600 rounded-full"></div>
              )}
              <span className={
                status === 'completed' ? 'text-green-400' :
                status === 'active' ? 'text-blue-400 font-medium' :
                'text-slate-500'
              }>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      {progress !== undefined && (
        <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
          <div
            className="bg-gradient-to-r from-blue-500 to-blue-400 h-2 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      )}
    </div>
  );
}
