import { useState, useEffect } from 'react';
import axios from 'axios';

function Search() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('default');
  const [results, setResults] = useState([]);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(false);
  const [idxStatus, setIdxStatus] = useState({ status: 'idle', total: 0, current: 0, message: '' });

  // Poll for indexing status
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await axios.get('http://localhost:8000/status');
        setIdxStatus(r.data);
      } catch (e) { console.error('Status poll error', e); }
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    axios.get('http://localhost:8000/recent', { params: { mode } }).then(r => setRecent(r.data));
  }, [mode]);

  const performSearch = async (searchQuery, overrideMode = null) => {
    if (!searchQuery) return;
    setLoading(true);
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
    if (e.key === 'Enter') performSearch(query);
  };

  const applyQuickFilter = (filterType) => {
    let newQuery = '';
    let newMode = 'regex';

    switch (filterType) {
      case 'email': newQuery = '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'; break;
      case 'ip': newQuery = '\\d+\\.\\d+\\.\\d+\\.\\d+'; break;
      case 'url': newQuery = 'https?:\\/\\/[\\w\\.-]+'; break;
      default: return;
    }
    setQuery(newQuery);
    setMode(newMode); // Auto-switch mode
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

  // Status Light Color
  const getStatusColor = () => {
    if (idxStatus.status === 'scanning') return 'bg-yellow-500 animate-pulse';
    if (idxStatus.status === 'error') return 'bg-red-500';
    if (idxStatus.status === 'idle') return 'bg-green-500';
    return 'bg-gray-500';
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-6">
          <h1 className="text-3xl font-bold text-gray-100">Search</h1>

          {/* Indexing Status Indicator (Loupiote) */}
          <div className="flex items-center gap-3 bg-gray-800 px-4 py-2 rounded-full border border-gray-600 shadow-sm">
            <div className={`w-3 h-3 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.5)] ${getStatusColor()}`}></div>
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-gray-300 uppercase tracking-widest leading-none">
                {idxStatus.status === 'scanning' ? 'INDEXING' : 'READY'}
              </span>
              {idxStatus.status === 'scanning' && (
                <span className="text-[10px] text-gray-500 font-mono leading-none mt-1">
                  {Math.round((idxStatus.current / idxStatus.total) * 100)}%
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Configuration moved here */}
        <div className="flex items-center gap-2 mb-2">
          <label className="text-gray-400 text-sm">Mode:</label>
          <select
            value={mode}
            onChange={e => setMode(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg p-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="default">Standard (Phrase)</option>
            <option value="regex">Regex (Advanced)</option>
            <option value="deep">Deep Search (Substring)</option>
          </select>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Search keywords...`}
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

      {/* ... keeping rest of results UI same ... */}
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
            <div className="flex justify-between items-start mb-3">
              <div>
                <span className="text-gray-100 font-medium">{r.filename}</span>
                {r.risk_level && (
                  <span className={`ml-3 px-2 py-1 rounded text-xs font-bold ${r.risk_level === 'CRITICAL' ? 'bg-red-600 text-white' :
                    r.risk_level === 'HIGH' ? 'bg-orange-500 text-white' :
                      r.risk_level === 'MEDIUM' ? 'bg-yellow-500 text-black' :
                        r.risk_level === 'LOW' ? 'bg-green-500 text-white' : 'bg-gray-600'
                    }`}>
                    {r.risk_level}
                  </span>
                )}
              </div>
              <span className="text-gray-500 text-sm font-mono">{r.path}</span>
            </div>
            {r.snippet && (
              <div className="bg-gray-900/50 p-4 rounded-lg border border-gray-700/50">
                <div className="text-sm text-gray-300 font-mono break-words" dangerouslySetInnerHTML={{ __html: r.snippet }} />
              </div>
            )}
            {/* Show match count if regex */}
            {r.match_count > 0 && (
              <div className="mt-2 text-xs text-blue-400">Matches found: {r.match_count}</div>
            )}
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