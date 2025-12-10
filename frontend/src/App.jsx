import { useState } from 'react';
import axios from 'axios';

function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [status, setStatus] = useState('Prêt');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  if (!loggedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 to-black flex items-center justify-center">
        <div className="bg-gray-900 p-12 rounded-2xl shadow-2xl border border-purple-500">
          <h1 className="text-5xl font-bold text-purple-400 mb-8 text-center">Leak Hunter 2025</h1>
          <button 
            onClick={() => setLoggedIn(true)}
            className="w-full py-6 bg-purple-600 hover:bg-purple-700 text-white text-2xl rounded-xl font-bold"
          >
            CONNEXION DEMO
          </button>
          <p className="text-center text-gray-400 mt-4">demo / demo</p>
        </div>
      </div>
    );
  }

  const load = async () => {
    setStatus('Indexation en cours...');
    const res = await axios.post('http://localhost:8000/load');
    setStatus(`Indexé ! ${res.data.indexed} lignes`);
  };

  const search = async () => {
    if (!query) return;
    const res = await axios.get(`http://localhost:8000/search?q=${query}`);
    setResults(res.data);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto p-8">
        <h1 className="text-6xl font-bold text-purple-400 mb-8 text-center">Leak Hunter 2025</h1>
        
        <div className="max-w-4xl mx-auto bg-gray-800 rounded-2xl p-8 shadow-2xl">
          <button onClick={load} className="w-full py-6 bg-green-600 hover:bg-green-700 text-3xl rounded-xl mb-6">
            CHARGER TOUT (incoming/)
          </button>
          <p className="text-xl mb-6 text-center">{status}</p>

          <div className="flex gap-4 mb-8">
            <input 
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && search()}
              placeholder="Recherche dans tous les PDF, ZIP, RAR..."
              className="flex-1 p-6 text-black text-xl rounded-xl"
            />
            <button onClick={search} className="px-12 py-6 bg-purple-600 hover:bg-purple-700 rounded-xl text-2xl">
              CHERCHER
            </button>
          </div>

          <div className="space-y-4">
            {results.map((r, i) => (
              <div key={i} className="bg-gray-700 p-6 rounded-xl" dangerouslySetInnerHTML={{__html: r.highlight}} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;