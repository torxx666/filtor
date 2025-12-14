import { useState, useEffect } from 'react';
import axios from 'axios';

function Search({ mode }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios.get('http://localhost:8000/recent', { params: { mode } }).then(r => setRecent(r.data));
  }, [mode]);

  const performSearch = async (searchQuery, overrideMode = null) => {
    if (!searchQuery) return;
    setLoading(true);
    // Use overrideMode if provided, else fall back to prop mode
    const searchMode = overrideMode || mode;
    try {
      const r = await axios.get('http://localhost:8000/search', { params: { q: searchQuery, mode: searchMode } });
      setResults(r.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      performSearch(query);
    }
  };

  const applyQuickFilter = (filterType) => {
    let newQuery = '';
    let newMode = 'default';

    switch (filterType) {
      case 'email':
        newQuery = '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}';
        newMode = 'regex';
        break;
      case 'ip':
        // Regex permisstive pour IP (inclus les non-cohérentes > 255)
        newQuery = '\\d+\\.\\d+\\.\\d+\\.\\d+';
        newMode = 'regex';
        break;
      case 'url':
        newQuery = 'https?:\\/\\/[\\w\\.-]+';
        newMode = 'regex';
        break;
      default: return;
    }
    setQuery(newQuery);
    performSearch(newQuery, newMode);
  };

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
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        <h1 className="text-3xl font-bold text-gray-100">Search</h1>

        {/* Search Bar */}
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Search keywords... (Mode: ${mode})`}
            className="w-full bg-gray-800 border border-gray-700 text-gray-100 p-4 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
          />
          <button
            onClick={() => performSearch(query)}
            className="absolute right-2 top-2 bottom-2 px-6 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            Search
          </button>
        </div>

        {/* Quick Filters */}
        <div className="flex gap-3">
          <button onClick={() => applyQuickFilter('email')} className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 hover:border-blue-500/50 transition-all text-sm font-medium text-gray-300">
            All Email
          </button>
          <button onClick={() => applyQuickFilter('ip')} className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 hover:border-blue-500/50 transition-all text-sm font-medium text-gray-300">
            All IP
          </button>
          <button onClick={() => applyQuickFilter('url')} className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 hover:border-blue-500/50 transition-all text-sm font-medium text-gray-300">
            All Urls
          </button>
        </div>
      </div>

      <div className="flex justify-between items-center bg-gray-800/50 p-4 rounded-lg border border-gray-700">
        <span className="text-gray-400">Results: {results.length}</span>
        {results.length > 0 && (
          <button onClick={exportCSV} className="text-blue-400 hover:text-blue-300 text-sm font-medium">
            Export CSV
          </button>
        )}
      </div>

      {loading && <div className="text-center py-8 text-gray-400">Searching...</div>}

      <div className="space-y-4">
        {results.map((r, i) => (
          <div key={i} className="bg-gray-800 border border-gray-700 p-6 rounded-xl hover:border-gray-600 transition-all shadow-sm">
            <div className="flex justify-between text-sm text-gray-500 mb-2 font-mono">
              <span>{r.filename}</span>
              <span>Line: {r.lineno}</span>
            </div>
            <div className="prose prose-invert max-w-none font-mono text-sm break-all" dangerouslySetInnerHTML={{ __html: r.highlight }} />
          </div>
        ))}
      </div>

      {recent.length > 0 && results.length === 0 && !loading && (
        <div className="space-y-4 opacity-75">
          <h2 className="text-xl font-semibold text-gray-400">Recent Searches</h2>
          {recent.map((r, i) => (
            <div key={i} className="bg-gray-800/50 border border-gray-700/50 p-4 rounded-lg" dangerouslySetInnerHTML={{ __html: r.highlight }} />
          ))}
        </div>
      )}
    </div>
  );
}

export default Search;