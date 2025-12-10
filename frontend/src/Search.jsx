import { useState, useEffect } from 'react';
import axios from 'axios';

function Search({ mode }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8000/recent', { params: { mode } }).then(r => setRecent(r.data));
  }, [mode]);

  useEffect(() => {
    if (!query) { setResults([]); return; }
    const t = setTimeout(() => {
      axios.get('http://localhost:8000/search', { params: { q: query, mode } }).then(r => setResults(r.data));
    }, 300);
    return () => clearTimeout(t);
  }, [query, mode]);

  const exportCSV = () => {
    const csv = results.map(r => `${r.filename},${r.lineno},"${r.highlight.replace(/"/g, '""')}"`).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'results.csv';
    a.click();
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl mb-4">Search</h1>
      <input type="text" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search (mode: {mode})" className="w-full p-2 bg-gray-700 rounded mb-4" />
      <button onClick={exportCSV} className="p-2 bg-blue-600 rounded hover:bg-blue-700 mb-4">Export CSV</button>
      <h2>Recent</h2>
      {recent.map((r, i) => (
        <div key={i} className="bg-dark-card p-4 rounded mb-2" dangerouslySetInnerHTML={{__html: r.highlight}} />
      ))}
      <h2>Results</h2>
      {results.map((r, i) => (
        <div key={i} className="bg-dark-card p-4 rounded mb-2" dangerouslySetInnerHTML={{__html: r.highlight}} />
      ))}
    </div>
  );
}

export default Search;