import { useState, useEffect } from 'react';
import api from './api';
import Sidebar from './components/Sidebar';

const MetadataViewer = ({ metadata }) => {
  if (!metadata) return null;

  const { format, first_frame_metadata } = metadata;
  const streams = metadata.streams || [];

  // Find Video/Audio streams
  const videoStream = streams.find(s => s.codec_type === 'video');
  const audioStream = streams.find(s => s.codec_type === 'audio');

  return (
    <div className="bg-gray-900/50 p-4 rounded-lg border border-gray-700/50 space-y-4">
      <div className="flex gap-4 items-start">
        {/* Basic Info */}
        <div className="bg-gray-800 p-3 rounded-md flex-1">
          <h4 className="text-xs text-gray-500 uppercase tracking-widest mb-2 border-b border-gray-700 pb-1">Format</h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div><span className="text-gray-400">Duration:</span> <span className="text-gray-200 font-mono">{format?.duration_seconds ? format.duration_seconds.toFixed(2) + 's' : 'N/A'}</span></div>
            <div><span className="text-gray-400">Bitrate:</span> <span className="text-gray-200 font-mono">{format?.bit_rate ? (format.bit_rate / 1000).toFixed(0) + ' kbps' : 'N/A'}</span></div>
            <div><span className="text-gray-400">Size:</span> <span className="text-gray-200 font-mono">{format?.size_bytes ? (format.size_bytes / 1024 / 1024).toFixed(2) + ' MB' : 'N/A'}</span></div>
            <div><span className="text-gray-400">Container:</span> <span className="text-gray-200">{format?.format_name}</span></div>
          </div>
        </div>

        {/* Video Stream */}
        {videoStream && (
          <div className="bg-gray-800 p-3 rounded-md flex-1">
            <h4 className="text-xs text-blue-400 uppercase tracking-widest mb-2 border-b border-gray-700 pb-1">Video</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-gray-400">Codec:</span> <span className="text-gray-200">{videoStream.codec_name}</span></div>
              <div><span className="text-gray-400">Res:</span> <span className="text-gray-200 font-mono">{videoStream.width}x{videoStream.height}</span></div>
              <div><span className="text-gray-400">FPS:</span> <span className="text-gray-200 font-mono">{videoStream.frame_rate}</span></div>
              <div><span className="text-gray-400">Pix Fmt:</span> <span className="text-gray-200">{videoStream.pix_fmt}</span></div>
            </div>
          </div>
        )}

        {/* Audio Stream */}
        {audioStream && (
          <div className="bg-gray-800 p-3 rounded-md flex-1">
            <h4 className="text-xs text-green-400 uppercase tracking-widest mb-2 border-b border-gray-700 pb-1">Audio</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-gray-400">Codec:</span> <span className="text-gray-200">{audioStream.codec_name}</span></div>
              <div><span className="text-gray-400">Channels:</span> <span className="text-gray-200">{audioStream.channels}</span></div>
              <div><span className="text-gray-400">Rate:</span> <span className="text-gray-200 font-mono">{audioStream.sample_rate} Hz</span></div>
            </div>
          </div>
        )}
      </div>

      {/* Extra Metadata (Exif/First Frame) */}
      {(first_frame_metadata && Object.keys(first_frame_metadata).length > 0) && (
        <div className="bg-gray-800 p-3 rounded-md">
          <h4 className="text-xs text-purple-400 uppercase tracking-widest mb-2 border-b border-gray-700 pb-1">Extended Metadata</h4>
          <div className="grid grid-cols-3 gap-2 text-xs font-mono text-gray-300">
            {Object.entries(first_frame_metadata).map(([k, v]) => (
              <div key={k} className="truncate"><span className="text-gray-500">{k.split(':').pop()}:</span> {String(v)}</div>
            ))}
          </div>
        </div>
      )}

      {/* NEW: Binary Scan Strings */}
      {metadata.embedded_strings && metadata.embedded_strings.length > 0 && (
        <div className="bg-gray-800 p-3 rounded-md">
          <h4 className="text-xs text-yellow-400 uppercase tracking-widest mb-2 border-b border-gray-700 pb-1">Binary Scan (Strings)</h4>
          <div className="max-h-48 overflow-y-auto space-y-1 font-mono text-xs text-gray-300 scrollbar-thin scrollbar-thumb-gray-600">
            {metadata.embedded_strings.map((str, idx) => (
              <div key={idx} className="hover:bg-gray-700 p-1 rounded border-b border-gray-700/30 break-all select-all">
                {str}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

function Search() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('default');
  const [results, setResults] = useState([]);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(false);
  const [idxStatus, setIdxStatus] = useState({ status: 'idle', total: 0, current: 0, message: '' });
  const [selectedFile, setSelectedFile] = useState(null);

  // Poll for indexing status
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await api.get('/status');
        setIdxStatus(r.data);
      } catch (e) { console.error('Status poll error', e); }
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    api.get('/recent', { params: { mode } }).then(r => setRecent(r.data));
  }, [mode]);

  const performSearch = async (searchQuery, overrideMode = null) => {
    if (!searchQuery) return;
    setLoading(true);
    const searchMode = overrideMode || mode;
    try {
      const r = await api.get('/search', { params: { q: searchQuery, mode: searchMode } });
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
    setMode(newMode);
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
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-6">
          <h1 className="text-3xl font-bold text-gray-100">Search</h1>

          {/* Indexing Status Indicator */}
          <div className="flex items-center gap-3 bg-gray-800 px-4 py-2 rounded-full border border-gray-600 shadow-sm">
            <div className={`w-3 h-3 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.5)] ${getStatusColor()}`}></div>
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-gray-300 uppercase tracking-widest leading-none">
                {idxStatus.status === 'scanning' ? 'INDEXING' : 'READY'}
              </span>
              {idxStatus.status === 'scanning' && (
                <span className="text-[10px] text-gray-500 font-mono leading-none mt-1">
                  {Math.round((idxStatus.current / (idxStatus.total || 1)) * 100)}%
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Configuration Area */}
        <div className="bg-gray-800/50 p-6 rounded-2xl border border-gray-700 shadow-2xl backdrop-blur-md space-y-6">

          {/* Search Mode (Standard/Regex) */}
          <div className="flex flex-col gap-2 max-w-md">
            <label className="text-blue-400 text-[10px] font-black uppercase tracking-widest">Search Algorithm</label>
            <select
              value={mode}
              onChange={e => setMode(e.target.value)}
              className="bg-gray-900 border border-gray-700 text-gray-100 text-sm rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-blue-500 transition-all outline-none"
            >
              <option value="default">Standard (Phrase Matching)</option>
              <option value="regex">Regex (Advanced Patterns)</option>
              <option value="deep">Deep Search (Substring Scan)</option>
            </select>
          </div>

          <div className="space-y-4 pt-4 border-t border-gray-700/50">
            {/* Search Bar */}
            <div className="relative">
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={`Search keywords...`}
                className="w-full bg-gray-900 border border-gray-700 text-gray-100 p-4 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all"
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
              <button onClick={() => applyQuickFilter('email')} className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg hover:bg-gray-800 hover:border-blue-500/50 transition-all text-sm font-medium text-gray-300">
                All Email
              </button>
              <button onClick={() => applyQuickFilter('ip')} className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg hover:bg-gray-800 hover:border-blue-500/50 transition-all text-sm font-medium text-gray-300">
                All IP
              </button>
              <button onClick={() => applyQuickFilter('url')} className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg hover:bg-gray-800 hover:border-blue-500/50 transition-all text-sm font-medium text-gray-300">
                All Urls
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Results Section */}
      <div className="flex justify-between items-center bg-gray-800/50 p-4 rounded-lg border border-gray-700">
        <span className="text-gray-400">Results: {results.length}</span>
        {results.length > 0 && (
          <button onClick={exportCSV} className="text-blue-400 hover:text-blue-300 text-sm font-medium">
            Export CSV
          </button>
        )}
      </div>

      {loading && <div className="text-center py-8 text-gray-400">Searching...</div>}

      <div className="space-y-4 pb-20">
        {results.map((r, i) => (
          <div
            key={i}
            className="bg-gray-800 border border-gray-700 p-6 rounded-xl hover:border-gray-500 transition-all shadow-sm cursor-pointer group"
            onClick={() => setSelectedFile(r)}
          >
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-3">
                <span className="text-gray-100 font-bold text-lg group-hover:text-blue-400 transition-colors">{r.filename}</span>
                {r.risk_level && (
                  <span className={`px-2 py-0.5 rounded text-[10px] font-black tracking-tighter shadow-md ${r.risk_level === 'CRITICAL' ? 'bg-red-600 text-white' :
                    r.risk_level === 'HIGH' ? 'bg-orange-500 text-white' :
                      r.risk_level === 'MEDIUM' ? 'bg-yellow-500 text-black' :
                        r.risk_level === 'LOW' ? 'bg-green-500 text-white' : 'bg-gray-600'
                    }`}>
                    {r.risk_level}
                  </span>
                )}
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-900/50 text-blue-300 border border-blue-800/50 uppercase tracking-widest">
                  {r.src || 'content'}
                </span>
              </div>
              <span className="text-gray-500 text-xs font-mono bg-gray-900 px-3 py-1 rounded-full border border-gray-700">{r.path}</span>
            </div>

            {/* Snippet / Content */}
            {r.snippet && (
              <div className="bg-gray-900/80 p-4 rounded-xl border border-gray-700/50 mb-4 shadow-inner">
                <div className="text-sm text-gray-300 font-mono break-words leading-relaxed" dangerouslySetInnerHTML={{ __html: r.snippet }} />
              </div>
            )}

            {/* Metadata Viewer (Inline preview) - Could remove if Sidebar covers it, but keeping for quick glance */}
            {r.metadata && (
              <MetadataViewer metadata={r.metadata} />
            )}

            {r.match_count > 0 && (
              <div className="mt-2 text-xs text-blue-400 font-bold uppercase tracking-widest">
                Matches found: {r.match_count}
              </div>
            )}

            <div className="mt-4 text-center text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity uppercase font-bold tracking-widest">
              Click to view full details
            </div>
          </div>
        ))}

        {!loading && results.length === 0 && query && (
          <div className="text-center py-20 bg-gray-800/20 rounded-2xl border-2 border-dashed border-gray-700/50 flex flex-col items-center gap-4">
            <svg className="w-12 h-12 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-gray-500 text-lg font-medium">No results found for <span className="text-gray-300 font-bold">"{query}"</span></p>
          </div>
        )}
      </div>

      <Sidebar file={selectedFile} onClose={() => setSelectedFile(null)} />
    </div>
  );
}

export default Search;