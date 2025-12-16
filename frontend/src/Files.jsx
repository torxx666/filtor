import { useState, useEffect } from 'react';
import axios from 'axios';
import Sidebar from './components/Sidebar';

function Files() {
    const [files, setFiles] = useState([]);
    const [selectedFile, setSelectedFile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [indexingStatus, setIndexingStatus] = useState({ status: 'idle', current: 0, total: 0 });

    // Filters
    const [filterFound, setFilterFound] = useState('all'); // all, yes, no
    const [filterType, setFilterType] = useState('all');
    const [filterStatus, setFilterStatus] = useState('All'); // NEW: Backend filter
    const [filterSize, setFilterSize] = useState('');
    const [filterSizeOp, setFilterSizeOp] = useState('>');

    useEffect(() => {
        fetchFiles();

        // Polling for indexing status
        const interval = setInterval(async () => {
            try {
                const res = await axios.get('http://localhost:8000/status');
                setIndexingStatus(res.data);

                // Reload files if finished just now (simple check)
                if (res.data.status === 'finished' && indexingStatus.status === 'scanning') {
                    fetchFiles();
                }
            } catch (e) {
                console.error("Status check failed", e);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [indexingStatus.status, filterStatus]); // Re-fetch on filter change

    const fetchFiles = async () => {
        try {
            // Pass risk_level filter to backend
            const params = filterStatus !== 'All' ? { risk_level: filterStatus } : {};
            const res = await axios.get('http://localhost:8000/files', { params });
            setFiles(res.data.files || res.data); // Handle {files: []} or []
            setLoading(false);
        } catch (e) {
            console.error(e);
            setError('Unable to load file list.');
            setLoading(false);
        }
    };

    const triggerLoad = async () => {
        try {
            await axios.post('http://localhost:8000/load');
            // Status polling will pick it up
        } catch (e) {
            alert("Error starting index: " + e.message);
        }
    };

    const formatSize = (bytes) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const formatDate = (timestamp) => {
        if (!timestamp) return 'N/A';
        // Handle both Unix timestamp (number) and ISO string
        const date = typeof timestamp === 'number'
            ? new Date(timestamp * 1000)
            : new Date(timestamp);
        return date.toLocaleString();
    };

    // Derived state for filters (client-side filters for type/found/size)
    const uniqueTypes = [...new Set(files.map(f => f.true_type || f.type))].sort();

    const filteredFiles = files.filter(file => {
        // Filter Found
        if (filterFound === 'yes' && !file.has_text) return false;
        if (filterFound === 'no' && file.has_text) return false;

        // Filter Type
        if (filterType !== 'all' && (file.true_type || file.type) !== filterType) return false;

        // Filter Size
        if (filterSize !== '') {
            const sizeLimit = parseInt(filterSize, 10);
            if (!isNaN(sizeLimit)) {
                if (filterSizeOp === '>' && file.size <= sizeLimit) return false;
                if (filterSizeOp === '<' && file.size >= sizeLimit) return false;
            }
        }

        return true;
    });

    const handleRowClick = (file) => {
        setSelectedFile(file);
    };

    return (
        <div className="space-y-6 relative">
            {selectedFile && (
                <Sidebar
                    file={selectedFile}
                    onClose={() => setSelectedFile(null)}
                />
            )}
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold text-gray-100">File Statistics</h1>
                <div className="flex gap-2 items-center">
                    {indexingStatus.status === 'scanning' && (
                        <div className="bg-gray-800 text-blue-400 px-4 py-2 rounded-lg border border-blue-900/50 flex items-center gap-2">
                            <svg className="animate-spin h-4 w-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span className="text-sm font-mono">
                                Scanning: {indexingStatus.current}/{indexingStatus.total || '?'}
                            </span>
                        </div>
                    )}
                    <button
                        onClick={triggerLoad}
                        disabled={indexingStatus.status === 'scanning'}
                        className={`px-4 py-2 text-white rounded-lg transition-colors ${indexingStatus.status === 'scanning' ? 'bg-gray-600 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
                    >
                        {indexingStatus.status === 'scanning' ? 'Scanning...' : 'Reload Index'}
                    </button>

                    <button
                        onClick={fetchFiles}
                        className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                    >
                        Refresh List
                    </button>
                </div>
            </div>

            {/* Filters Section */}
            <div className="bg-gray-800 p-4 rounded-xl border border-gray-700 flex flex-wrap gap-4 items-end">
                <div>
                    <label className="block text-xs text-gray-400 mb-1">Text Found</label>
                    <select
                        value={filterFound}
                        onChange={(e) => setFilterFound(e.target.value)}
                        className="bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-lg block w-32 p-2.5"
                    >
                        <option value="all">All</option>
                        <option value="yes">YES</option>
                        <option value="no">NO</option>
                    </select>
                </div>

                <div>
                    <label className="block text-xs text-gray-400 mb-1">Status (Risk)</label>
                    <select
                        value={filterStatus}
                        onChange={(e) => setFilterStatus(e.target.value)}
                        className="bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-lg block w-32 p-2.5"
                    >
                        <option value="All">All Levels</option>
                        <option value="CRITICAL">CRITICAL</option>
                        <option value="HIGH">HIGH</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="LOW">LOW</option>
                        <option value="UNKNOWN">UNKNOWN</option>
                    </select>
                </div>

                <div>
                    <label className="block text-xs text-gray-400 mb-1">True Type</label>
                    <select
                        value={filterType}
                        onChange={(e) => setFilterType(e.target.value)}
                        className="bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-lg block w-48 p-2.5"
                    >
                        <option value="all">All Types</option>
                        {uniqueTypes.map(t => (
                            <option key={t} value={t}>{t}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-xs text-gray-400 mb-1">Size (bytes)</label>
                    <div className="flex">
                        <select
                            value={filterSizeOp}
                            onChange={(e) => setFilterSizeOp(e.target.value)}
                            className="bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-l-lg block w-16 p-2.5 border-r-0"
                        >
                            <option value=">">&gt;</option>
                            <option value="<">&lt;</option>
                        </select>
                        <input
                            type="number"
                            placeholder="bytes"
                            value={filterSize}
                            onChange={(e) => setFilterSize(e.target.value)}
                            className="bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-r-lg block w-32 p-2.5"
                        />
                    </div>
                </div>
            </div>

            {loading && <div className="text-gray-400">Loading data...</div>}
            {error && <div className="text-red-400">{error}</div>}

            {!loading && !error && (
                <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-gray-400">
                            <thead className="bg-gray-900 text-gray-200 uppercase font-medium">
                                <tr>
                                    <th className="px-6 py-4 text-center">Risk</th>
                                    <th className="px-6 py-4 text-center">Score</th>
                                    <th className="px-6 py-4 text-center">Text Found</th>
                                    <th className="px-6 py-4">Filename</th>
                                    <th className="px-6 py-4">True Type</th>
                                    <th className="px-6 py-4">Path</th>
                                    <th className="px-6 py-4">Size</th>
                                    <th className="px-6 py-4">Created At</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-700">
                                {filteredFiles.map((file, idx) => (
                                    <tr
                                        key={idx}
                                        onClick={() => handleRowClick(file)}
                                        className={`hover:bg-gray-700/50 transition-colors cursor-pointer ${selectedFile?.path === file.path ? 'bg-gray-700 border-l-4 border-blue-500' : ''}`}
                                    >
                                        <td className="px-6 py-4 text-center">
                                            <span className={`px-2 py-1 rounded text-xs font-bold ${file.risk_level === 'CRITICAL' ? 'bg-red-600 text-white' :
                                                file.risk_level === 'HIGH' ? 'bg-orange-500 text-white' :
                                                    file.risk_level === 'MEDIUM' ? 'bg-yellow-500 text-black' :
                                                        file.risk_level === 'LOW' ? 'bg-green-500 text-white' : 'bg-gray-600'
                                                }`}>
                                                {file.risk_level || 'UNKNOWN'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-center font-mono text-gray-300">
                                            {file.risk_score ? file.risk_score.toFixed(1) : '0.0'}
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <span
                                                className={`px-2 py-1 rounded text-xs font-bold ${file.has_text
                                                    ? 'bg-green-900/50 text-green-400 border border-green-800'
                                                    : 'bg-red-900/50 text-red-400 border border-red-800'
                                                    }`}
                                            >
                                                {file.has_text ? 'YES' : 'NO'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 font-medium text-gray-200">{file.filename}</td>
                                        <td className="px-6 py-4">{file.true_type || file.type}</td>
                                        <td className="px-6 py-4 font-mono text-xs">{file.path}</td>
                                        <td className="px-6 py-4">{formatSize(file.size)}</td>
                                        <td className="px-6 py-4">{formatDate(file.created_at)}</td>
                                    </tr>
                                ))}
                                {filteredFiles.length === 0 && (
                                    <tr>
                                        <td colSpan="9" className="px-6 py-8 text-center text-gray-500">
                                            No files match criteria (or none indexed).
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Files;
