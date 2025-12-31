import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const Layout = ({ children, onLogout }) => {
    const navigate = useNavigate();
    const location = useLocation();

    const isActive = (path) => location.pathname === path;

    // Custom Icon Components for "Pro" look without external deps
    const SearchIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
    );

    const SettingsIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
    );

    const LogOutIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
        </svg>
    );

    const handleLogout = () => {
        if (onLogout) {
            onLogout();
        } else {
            navigate('/login');
        }
    };

    return (
        <div className="flex h-screen bg-gray-900 text-gray-100 font-sans overflow-hidden">
            {/* Sidebar */}
            <aside className="w-20 md:w-64 bg-gray-800 border-r border-gray-700 flex flex-col justify-between transition-all duration-300">
                <div>
                    {/* Logo / Brand */}
                    <div className="h-16 flex items-center justify-center md:justify-start md:px-6 border-b border-gray-700">
                        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-white text-xl">
                            F
                        </div>
                        <span className="ml-3 font-semibold text-lg hidden md:block tracking-wide">Filtor Pro</span>
                    </div>

                    {/* Navigation */}
                    <nav className="mt-6 px-2 space-y-2">
                        <button
                            onClick={() => navigate('/search')}
                            className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-200 group ${isActive('/search')
                                ? 'bg-blue-600/10 text-blue-400 font-medium'
                                : 'hover:bg-gray-700/50 text-gray-400 hover:text-gray-100'
                                }`}
                        >
                            <div className={`${isActive('/search') ? 'text-blue-400' : 'text-gray-400 group-hover:text-gray-100'}`}>
                                <SearchIcon />
                            </div>
                            <span className="hidden md:block">Analysis</span>
                        </button>

                        <button
                            onClick={() => navigate('/stats')}
                            className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-200 group ${isActive('/stats')
                                ? 'bg-blue-600/10 text-blue-400 font-medium'
                                : 'hover:bg-gray-700/50 text-gray-400 hover:text-gray-100'
                                }`}
                        >
                            <div className={`${isActive('/stats') ? 'text-blue-400' : 'text-gray-400 group-hover:text-gray-100'}`}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                    <polyline points="14 2 14 8 20 8"></polyline>
                                    <line x1="16" y1="13" x2="8" y2="13"></line>
                                    <line x1="16" y1="17" x2="8" y2="17"></line>
                                    <polyline points="10 9 9 9 8 9"></polyline>
                                </svg>
                            </div>
                            <span className="hidden md:block">File Stats</span>
                        </button>

                        <button
                            onClick={() => navigate('/settings')}
                            className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-200 group ${isActive('/settings')
                                ? 'bg-blue-600/10 text-blue-400 font-medium'
                                : 'hover:bg-gray-700/50 text-gray-400 hover:text-gray-100'
                                }`}
                        >
                            <div className={`${isActive('/settings') ? 'text-blue-400' : 'text-gray-400 group-hover:text-gray-100'}`}>
                                <SettingsIcon />
                            </div>
                            <span className="hidden md:block">Settings</span>
                        </button>
                    </nav>
                </div>

                {/* Bottom Actions */}
                <div className="p-4 border-t border-gray-700">
                    <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-red-500/10 text-gray-400 hover:text-red-400 transition-all duration-200 group"
                    >
                        <div className="text-gray-400 group-hover:text-red-400">
                            <LogOutIcon />
                        </div>
                        <span className="hidden md:block">Logout</span>
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto bg-gray-900 relative">
                <div className="max-w-7xl mx-auto p-4 md:p-8">
                    <div className="animate-fade-in">
                        {children}
                    </div>
                </div>
            </main>
        </div>
    );
};

export default Layout;
