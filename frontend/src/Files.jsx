import { useState, useEffect } from 'react';
import axios from 'axios';

function Files() {
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Filters
    const [filterFound, setFilterFound] = useState('all'); // all, yes, no
    const [filterType, setFilterType] = useState('all');
    const [filterSize, setFilterSize] = useState('');
    const [filterSizeOp, setFilterSizeOp] = useState('>');

    useEffect(() => {
        fetchFiles();
    }, []);

    const fetchFiles = async () => {
        try {
            const res = await axios.get('http://localhost:8000/files');
            setFiles(res.data);
            setLoading(false);
        } catch (e) {
            console.error(e);
            setError('Impossible de charger la liste des fichiers.');
            setLoading(false);
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
        return new Date(timestamp * 1000).toLocaleString();
    };

    // Derived state for filters
    const uniqueTypes = [...new Set(files.map(f => f.type))].sort();

    const filteredFiles = files.filter(file => {
        // Filter Found
        if (filterFound === 'yes' && !file.has_text) return false;
        if (filterFound === 'no' && file.has_text) return false;

        // Filter Type
        if (filterType !== 'all' && file.type !== filterType) return false;

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

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold text-gray-100">File Statistics</h1>
                <button
                    onClick={fetchFiles}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                    Refresh
                </button>
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

            {loading && <div className="text-gray-400">Chargement des données...</div>}
            {error && <div className="text-red-400">{error}</div>}

            {!loading && !error && (
                <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-gray-400">
                            <thead className="bg-gray-900 text-gray-200 uppercase font-medium">
                                <tr>
                                    <th className="px-6 py-4 text-center">Text Found</th>
                                    <th className="px-6 py-4">Filename</th>
                                    <th className="px-6 py-4">True Type</th>
                                    <th className="px-6 py-4">Path</th>
                                    <th className="px-6 py-4">Size</th>
                                    <th className="px-6 py-4">Info</th>
                                    <th className="px-6 py-4">Created At</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-700">
                                {filteredFiles.map((file, idx) => (
                                    <tr key={idx} className="hover:bg-gray-700/50 transition-colors">
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
                                        <td className="px-6 py-4">{file.type}</td>
                                        <td className="px-6 py-4 font-mono text-xs">{file.path}</td>
                                        <td className="px-6 py-4">{formatSize(file.size)}</td>
                                        <td className="px-6 py-4 text-xs text-gray-400 font-mono">{file.info || '-'}</td>
                                        <td className="px-6 py-4">{formatDate(file.created_at)}</td>
                                    </tr>
                                ))}
                                {filteredFiles.length === 0 && (
                                    <tr>
                                        <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                                            Aucun fichier ne correspond aux critères (ou aucun indexé).
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
