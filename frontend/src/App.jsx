import { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [recent, setRecent] = useState([]);
  const [results, setResults] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const loadDump = () => {
    setLoading(true);
    axios.post('http://127.0.0.1:8000/load').then(() => {
      setLoading(false);
      loadRecent();
    });
  };

  const loadRecent = () => {
    axios.get('http://127.0.0.1:8000/recent').then(r => setRecent(r.data));
  };

  useEffect(() => { loadRecent(); }, []);

  useEffect(() => {
    if (!query.trim()) { setResults([]); return; }
    const t = setTimeout(() => {
      axios.get(`http://127.0.0.1:8000/search?q=${encodeURIComponent(query)}`).then(r => setResults(r.data));
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  return (
    <div style={{fontFamily: 'system-ui', padding: 20, maxWidth: 1200, margin: '0 auto'}}>
      <h1>Leak Searcher 2025</h1>
      
      <button onClick={loadDump} disabled={loading} style={{padding: 15, fontSize: 18, marginBottom: 20}}>
        {loading ? "Indexation en cours..." : "CHARGER LE DUMP (dossier entier)"}
      </button>

      <h2>10 derniers enregistrements</h2>
      <div>{recent.map((r,i) => (
        <div key={i} style={{background:'#222', color:'#0f0', padding:10, margin:5, borderRadius:8, fontFamily:'monospace'}}>
          <strong>{r.filename}:{r.lineno}</strong> → <span dangerouslySetInnerHTML={{__html: r.highlight}} />
        </div>
      ))}</div>

      <h2>Recherche instantanée</h2>
      <input
        type="text" placeholder="bitcoin OR seed OR @gmail.com OR 0x[a-f0-9]{40}..."
        value={query} onChange={e => setQuery(e.target.value)}
        style={{width:'100%', padding:15, fontSize:18}}
      />

      <div>
        {results.map((r,i) => (
          <div key={i} style={{background:'#111', color:'#fff', padding:12, margin:8, borderRadius:8, fontFamily:'monospace'}}>
            <strong>{r.filename}:{r.lineno}</strong> → <span dangerouslySetInnerHTML={{__html: r.highlight}} />
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;