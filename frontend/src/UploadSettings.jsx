import { useState, useEffect } from 'react';
import api from './api';



function UploadSettings() {
  const [status, setStatus] = useState('');
  const [progress, setProgress] = useState(0);
  const [scanMode, setScanMode] = useState('FAST');

  // Custom Keywords State
  const [keywords, setKeywords] = useState([]);
  const [newKeyword, setNewKeyword] = useState('');

  const fetchKeywords = async () => {
    try {
      const res = await api.get('/keywords');
      setKeywords(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchKeywords();
  }, []);

  const handleAddKeyword = async () => {
    if (!newKeyword.trim()) return;
    try {
      await api.post('/keywords', { keyword: newKeyword });
      setNewKeyword('');
      fetchKeywords();
    } catch (e) {
      alert(e.response?.data?.detail || "Error adding keyword");
    }
  };

  const handleDeleteKeyword = async (id) => {
    try {
      await api.delete(`/keywords/${id}`);
      fetchKeywords();
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpload = async () => {
    setProgress(20);
    setStatus('Indexing in progress...');
    try {
      const res = await api.post('/load', null, { params: { mode: scanMode } });
      setProgress(100);
      setStatus(
        <span className="text-green-400">
          {res.data.message || 'Indexing started in background!'}<br />
          Check the File Statistics page to see results.
        </span>
      );
    } catch (e) {
      console.error(e);
      const msg = e.response?.data?.detail || e.message;
      setStatus(<span className="text-red-400">Error: {msg}</span>);
    }
  };

  // Drag & drop logic
  const [isDragging, setIsDragging] = useState(false);

  // Common DND prevent defaults
  const preventDefaults = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragEnter = (e) => {
    preventDefaults(e);
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    preventDefaults(e);
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    preventDefaults(e);
    // Explicitly show copy effect
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleDrop = async (e) => {
    preventDefaults(e);
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    setProgress(10);
    setStatus(`Uploading ${files.length} file(s)...`);

    try {
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append('file', files[i]);
        await api.post('/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        setProgress(10 + ((i + 1) / files.length) * 40);
      }
      setStatus('Upload finished. Indexing...');
      handleUpload(); // Trigger indexing after upload
    } catch (e) {
      console.error(e);
      setStatus(<span className="text-red-400">Error uploading files</span>);
    }
  };

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-gray-100">Settings & Upload</h1>

      {/* Upload Section */}
      <div className="bg-gray-800 p-8 rounded-2xl border border-gray-700 shadow-2xl">
        <h2 className="text-2xl font-black text-gray-100 mb-8 uppercase tracking-tighter italic">Data Indexing</h2>

        <div className="flex flex-col gap-8">

          <div
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed p-16 rounded-2xl text-center cursor-pointer transition-all ${isDragging
              ? 'border-blue-500 bg-blue-500/10 scale-[1.01]'
              : 'border-gray-700 bg-gray-900/40 hover:border-gray-500 hover:bg-gray-900/60'
              }`}
          >
            <div className="pointer-events-none space-y-4">
              <div className="flex justify-center">
                <svg className="w-12 h-12 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <div>
                <p className={`text-xl font-bold ${isDragging ? 'text-blue-400' : 'text-gray-300'}`}>
                  {isDragging ? 'Release to upload!' : 'Drop Forensic Data Here'}
                </p>
                <p className="text-gray-500 text-sm mt-1">Accepts ZIP, RAR, PDF, Videos, Images</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between bg-gray-900/50 p-4 rounded-xl border-2 border-blue-500/50 shadow-[0_0_20px_rgba(59,130,246,0.15)] animate-pulse-slow">
              <span className="text-white font-black uppercase tracking-widest text-sm flex items-center gap-2">
                <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                Select Analysis Mode:
              </span>
              <div className="flex bg-gray-950 p-1.5 rounded-lg border border-gray-600">
                <button
                  onClick={() => setScanMode('FAST')}
                  className={`px-6 py-2 rounded-md transition-all text-sm font-black uppercase tracking-widest ${scanMode === 'FAST' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-gray-200'}`}
                >
                  FAST
                </button>
                <button
                  onClick={() => setScanMode('DEEP')}
                  className={`px-6 py-2 rounded-md transition-all text-sm font-black uppercase tracking-widest ${scanMode === 'DEEP' ? 'bg-red-600 text-white shadow-lg' : 'text-gray-400 hover:text-gray-200'}`}
                >
                  DEEP
                </button>
              </div>
            </div>

            <button
              onClick={handleUpload}
              className={`w-full py-5 text-white text-xl font-black uppercase tracking-tighter rounded-2xl transition-all shadow-2xl bg-green-600 hover:bg-green-500 border-b-4 border-green-800 active:border-b-0 active:translate-y-1`}
            >
              Load & index All Data ({scanMode})
            </button>
          </div>

          {progress > 0 && (
            <div className="w-full bg-gray-900 rounded-full h-4 overflow-hidden border border-gray-700">
              <div
                className={`h-full transition-all duration-500 ease-out ${scanMode === 'FAST' ? 'bg-blue-500' : 'bg-red-500'}`}
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          )}

          {status && (
            <div className="p-4 bg-gray-900 rounded-xl border border-gray-700 font-mono text-sm shadow-inner leading-relaxed">
              <div className="text-xs text-gray-500 mb-1">Engine Status [Mode: {scanMode}]</div>
              {status}
            </div>
          )}
        </div>
      </div>



      {/* Internal Use Keywords (Custom Alerts) */}
      <div className="bg-gray-800 p-8 rounded-2xl border border-gray-700 shadow-2xl">
        <h2 className="text-2xl font-black text-gray-100 mb-6 uppercase tracking-tighter italic">Internal Use Keywords</h2>
        <div className="flex flex-col gap-6">
          {/* Add Keyword */}
          <div className="flex gap-4">
            <input
              type="text"
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              placeholder="Enter keyword (e.g., CONFIDENTIAL, ProjectX)..."
              className="flex-1 bg-gray-900 border border-gray-600 rounded-xl px-4 py-3 text-gray-200 focus:outline-none focus:border-blue-500 transition-colors"
              onKeyDown={(e) => e.key === 'Enter' && handleAddKeyword()}
            />
            <button
              onClick={handleAddKeyword}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl transition-all shadow-lg"
            >
              ADD
            </button>
          </div>

          {/* Keywords List */}
          <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-700 max-h-60 overflow-y-auto">
            {keywords.length === 0 ? (
              <p className="text-gray-500 text-center py-4 italic">No custom keywords defined.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {keywords.map((k) => (
                  <div key={k.id} className="flex items-center gap-2 bg-gray-800 border border-gray-600 px-3 py-1.5 rounded-lg group">
                    <span className="text-gray-200 font-mono text-sm">{k.keyword}</span>
                    <button
                      onClick={() => handleDeleteKeyword(k.id)}
                      className="text-gray-500 hover:text-red-400 transition-colors"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          <p className="text-xs text-gray-500">
            * These keywords will be flagged as <span className="text-yellow-500 font-bold">"Internal Use Kw"</span> secrets during file analysis.
          </p>
        </div>
      </div>

      {/* Database Management Section */}
      <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
        <h2 className="text-xl font-semibold text-gray-300 mb-4">Database Management</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Export */}
          <div className="bg-gray-700/30 p-4 rounded-lg border border-gray-600">
            <h3 className="text-gray-200 font-medium mb-2">Export Database</h3>
            <p className="text-gray-400 text-sm mb-4">Download the current SQLite database (leak.db) to backup your data.</p>
            <button
              onClick={() => window.location.href = `${api.defaults.baseURL}/export-db`}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
            >
              Export DB
            </button>
          </div>

          {/* Import */}
          <div className="bg-gray-700/30 p-4 rounded-lg border border-gray-600">
            <h3 className="text-gray-200 font-medium mb-2">Import Database</h3>
            <p className="text-gray-400 text-sm mb-4">Replace current database with a backup (.db file). This will overwrite existing data.</p>
            <div className="flex gap-2">
              <input
                type="file"
                accept=".db"
                className="hidden"
                id="db-upload"
                onChange={async (e) => {
                  const file = e.target.files[0];
                  if (!file) return;

                  if (!confirm("Warning: This will replace the entire current database. Continue?")) {
                    e.target.value = null; // Reset input
                    return;
                  }

                  const formData = new FormData();
                  formData.append('file', file);

                  setStatus('Importing database...');
                  try {
                    await api.post('/import-db', formData, {
                      headers: { 'Content-Type': 'multipart/form-data' }
                    });
                    setStatus(<span className="text-green-400">Database successfully imported and re-indexed!</span>);
                  } catch (err) {
                    console.error(err);
                    setStatus(<span className="text-red-400">Import failed: {err.response?.data?.detail || err.message}</span>);
                  }
                  e.target.value = null; // Reset input
                }}
              />
              <label
                htmlFor="db-upload"
                className="w-full py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors font-medium text-center cursor-pointer"
              >
                Import DB
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default UploadSettings;
// Force refresh