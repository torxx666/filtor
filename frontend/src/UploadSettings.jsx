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
            Indexation terminée !<br/>
            → {res.data.files_detected} fichier(s) détecté(s)<br/>
            → {res.data.lines_indexed.toLocaleString()} ligne(s) indexée(s)
        </span>
        );
    } catch (e) {
        setStatus(<span className="text-red-400">Erreur lors de l'indexation</span>);
    }
    };

  // Drag & drop logic
  const handleDrop = (e) => {
    e.preventDefault();
    // Logique pour upload files (plus tard avec FastAPI upload endpoint)
    console.log(e.dataTransfer.files);
    handleUpload();
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl mb-4">Upload & Settings</h1>
      <div onDrop={handleDrop} onDragOver={e => e.preventDefault()} className="border-2 border-dashed p-8 mb-4 rounded-lg">
        Drag & drop ZIP/RAR/PDF ici ou clique pour upload
      </div>
        <button onClick={handleUpload} className="p-3 bg-green-600 rounded hover:bg-green-700 text-lg">
        Charger et indexer tout
        </button>

        {progress > 0 && (
        <div className="mt-4">
            <div className="h-3 bg-gray-700 rounded overflow-hidden">
            <div className="h-full bg-green-500 transition-all duration-300" style={{width: `${progress}%`}}></div>
            </div>
        </div>
        )}

        {status && <div className="mt-4 text-lg font-mono" dangerouslySetInnerHTML={{__html: status}} />}
      <div className="mt-8">
        <h2>Settings</h2>
        <select value={mode} onChange={e => setMode(e.target.value)} className="p-2 bg-gray-700 rounded">
          <option value="default">Default (query*)</option>
          <option value="deep">Deep (substring)</option>
        </select>
      </div>
    </div>
  );
}

export default UploadSettings;