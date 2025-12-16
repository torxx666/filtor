import React from 'react';
import { createPortal } from 'react-dom';

const Sidebar = ({ file, onClose }) => {
    if (!file) return null;

    let details = {};
    try {
        details = JSON.parse(file.details || '{}');
    } catch (e) {
        details = { error: "Invalid details format" };
    }

    const { risk_level, risk_score, detections, metadata, recommendations } = details;

    const riskColor =
        risk_level === 'CRITICAL' ? 'bg-red-600' :
            risk_level === 'HIGH' ? 'bg-orange-500' :
                risk_level === 'MEDIUM' ? 'bg-yellow-500' : 'bg-green-500';

    return createPortal(
        <div className="fixed inset-y-0 right-0 w-96 bg-gray-900 border-l border-gray-700 shadow-2xl transform transition-transform duration-300 ease-in-out overflow-y-auto z-[9999] p-6">
            <div className="flex justify-between items-start mb-6">
                <h2 className="text-xl font-bold text-gray-100 truncate w-64" title={file.filename}>
                    {file.filename}
                </h2>
                <button onClick={onClose} className="text-gray-400 hover:text-white">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            {/* Risk Header */}
            <div className={`${riskColor} p-4 rounded-lg mb-6 shadow-lg`}>
                <div className="flex justify-between items-center text-white">
                    <span className="font-bold text-lg">{risk_level || 'UNKNOWN'}</span>
                    <span className="bg-black/20 px-2 py-1 rounded text-sm font-mono">
                        Score: {risk_score?.toFixed(1) || 0}
                    </span>
                </div>
            </div>

            {/* Recommendations */}
            {recommendations && recommendations.length > 0 && (
                <div className="mb-6">
                    <h3 className="text-sm uppercase text-gray-400 font-bold mb-3">Recommendations</h3>
                    <ul className="space-y-2">
                        {recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start text-sm text-yellow-200 bg-yellow-900/20 p-2 rounded">
                                <span className="mr-2">⚠️</span>
                                {rec}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Detections */}
            {detections && Object.keys(detections).length > 0 && (
                <div className="mb-6">
                    <h3 className="text-sm uppercase text-gray-400 font-bold mb-3">Detections</h3>
                    <div className="space-y-3">
                        {Object.entries(detections).map(([key, val]) => {
                            // Filter out empty detections
                            if (!val.risk_points && !val.indicators?.length && !val.findings) return null;
                            if (val.indicators?.length === 0 && !val.findings) return null;

                            return (
                                <div key={key} className="bg-gray-800 rounded p-3 text-sm border border-gray-700">
                                    <div className="flex justify-between mb-1">
                                        <span className="font-semibold text-gray-300 capitalize">{key.replace('_', ' ')}</span>
                                        {val.risk_points > 0 && (
                                            <span className="text-red-400 text-xs">+{val.risk_points} pts</span>
                                        )}
                                    </div>

                                    {val.indicators && (
                                        <ul className="list-disc list-inside text-gray-400 text-xs space-y-1">
                                            {val.indicators.map((ind, i) => (
                                                <li key={i}>{ind}</li>
                                            ))}
                                        </ul>
                                    )}

                                    {val.findings && (
                                        <div className="mt-1 space-y-1">
                                            {Object.entries(val.findings).map(([fKey, fVal]) => (
                                                <div key={fKey} className="text-xs text-red-300">
                                                    <span className="font-mono">{fKey}: </span>
                                                    {typeof fVal === 'object' && fVal !== null
                                                        ? (fVal.count ? `${fVal.count} matches` : fVal.value)
                                                        : fVal}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* File Info */}
            <div className="mb-6">
                <h3 className="text-sm uppercase text-gray-400 font-bold mb-3">File Info</h3>
                <div className="bg-gray-800 rounded p-4 text-xs font-mono text-gray-300 space-y-2 border border-gray-700">
                    <div className="flex justify-between">
                        <span className="text-gray-500">Path:</span>
                        <span className="text-right truncate ml-4" title={file.path}>{file.path}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-500">Type:</span>
                        <span className="text-right">{file.type}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-500">Size:</span>
                        <span className="text-right">{metadata?.size_human || file.size}</span>
                    </div>
                </div>
            </div>

            {/* Metadata */}
            {metadata && (
                <div className="mb-6">
                    <h3 className="text-sm uppercase text-gray-400 font-bold mb-3">System Metadata</h3>
                    <div className="bg-gray-800 rounded p-4 text-xs font-mono text-gray-400 space-y-1 border border-gray-700">
                        {Object.entries(metadata).map(([k, v]) => (
                            <div key={k} className="flex justify-between" title={k === 'hash' ? String(v) : ''}>
                                <span className="text-gray-500 capitalize">{k.replace('_', ' ')}:</span>
                                <span className="text-gray-300 text-right truncate ml-4">
                                    {k === 'hash' && String(v).length > 20
                                        ? `${String(v).substring(0, 8)}...${String(v).substring(String(v).length - 8)}`
                                        : String(v)}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

        </div>,
        document.body
    );
};

export default Sidebar;
