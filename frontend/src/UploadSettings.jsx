import { useState } from 'react';
import axios from 'axios';



function UploadSettings({ mode, setMode }) {
  const [status, setStatus] = useState('');
  const [progress, setProgress] = useState(0);

  const handleUpload = async () => {
    setProgress(20);
    setStatus('Indexation en cours...');
    try {
      const res = await axios.post('http://localhost:8000/load');
      setProgress(100);
      setStatus(
        <span className="text-green-400">
          Indexation terminée !<br />
          → {res.data.files_detected || 0} fichier(s) détecté(s)<br />
          → {(res.data.lines_indexed || 0).toLocaleString()} ligne(s) indexée(s)
        </span>
      );
    } catch (e) {
      console.error(e);
      const msg = e.response?.data?.detail || e.message;
      setStatus(<span className="text-red-400">Erreur: {msg}</span>);
    }
  };

  // Drag & drop logic
  const handleDrop = async (e) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    setProgress(10);
    setStatus(`Uploading ${files.length} file(s)...`);

    try {
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append('file', files[i]);
        await axios.post('http://localhost:8000/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        setProgress(10 + ((i + 1) / files.length) * 40); // Upload takes up to 50%
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
      <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
        <h2 className="text-xl font-semibold text-gray-300 mb-4">Data Indexing</h2>
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          className="border-2 border-dashed border-gray-600 bg-gray-700/30 p-12 rounded-xl text-center cursor-pointer hover:border-gray-500 hover:bg-gray-700/50 transition-all"
        >
          <p className="text-gray-400 text-lg">Drag & drop ZIP/RAR/PDF files here</p>
          <p className="text-gray-500 text-sm mt-2">or click to browse</p>
        </div>

        <div className="mt-6 flex flex-col gap-4">
          <button
            onClick={handleUpload}
            className="w-full py-4 bg-green-600 hover:bg-green-700 text-white text-lg font-bold rounded-xl transition-colors shadow-lg shadow-green-900/20"
          >
            Load & Index All Data
          </button>

          {progress > 0 && (
            <div className="w-full bg-gray-700 rounded-full h-4 overflow-hidden">
              <div
                className="bg-green-500 h-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          )}

          {status && (
            <div className="p-4 bg-gray-900 rounded-lg border border-gray-700 font-mono text-sm">
              {status}
            </div>
          )}
        </div>
      </div>

      {/* Configuration Section */}
      <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
        <h2 className="text-xl font-semibold text-gray-300 mb-4">Search Configuration</h2>
        <div className="flex flex-col gap-2">
          <label className="text-gray-400 text-sm">Search Logic</label>
          <select
            value={mode}
            onChange={e => setMode(e.target.value)}
            className="w-full md:w-1/2 p-3 bg-gray-900 border border-gray-600 rounded-lg text-gray-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            <option value="default">Standard (Fast Phrase Match)</option>
            <option value="deep">Deep Search (Thorough Substring)</option>
          </select>
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
              onClick={() => window.location.href = 'http://localhost:8000/export-db'}
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

                  if (!confirm("Attention: This will replace the entire current database. Continue?")) {
                    e.target.value = null; // Reset input
                    return;
                  }

                  const formData = new FormData();
                  formData.append('file', file);

                  setStatus('Importing database...');
                  try {
                    await axios.post('http://localhost:8000/import-db', formData, {
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