import { Outlet, useLocation } from 'react-router-dom';
import { Bell, Search, User } from 'lucide-react';
import Sidebar from './Sidebar';

const PAGE_TITLES: Record<string, string> = {
  '/':          'Dashboard',
  '/incidents': 'Incidents',
  '/agents':    'Agents',
  '/policies':  'Policies',
  '/analytics': 'Analytics',
  '/settings':  'Settings',
};

export default function Layout() {
  const { pathname } = useLocation();
  const title = PAGE_TITLES[pathname] ?? 'HECATE';

  return (
    <div className="flex min-h-screen bg-surface-950 text-white font-sans">
      <Sidebar />

      <div className="flex flex-col flex-1 min-w-0">
        {/* Top bar */}
        <header className="flex items-center justify-between px-6 h-14 border-b border-white/5 bg-surface-900/50 backdrop-blur-sm sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-semibold text-white/90">{title}</h1>
            <span className="text-white/20">·</span>
            <span className="text-xs text-white/30 font-mono">
              {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Search */}
            <button
              id="topbar-search"
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/8 text-white/40 hover:text-white/70 hover:bg-white/8 transition-all duration-200 text-xs"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search…</span>
              <kbd className="ml-2 px-1.5 py-0.5 rounded border border-white/10 text-[10px] font-mono bg-white/5">⌘K</kbd>
            </button>

            {/* Notifications */}
            <button
              id="topbar-notifications"
              className="relative flex items-center justify-center w-8 h-8 rounded-lg hover:bg-white/5 transition-colors"
            >
              <Bell className="w-4 h-4 text-white/50" />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-accent-red" />
            </button>

            {/* Avatar */}
            <button
              id="topbar-profile"
              className="flex items-center justify-center w-8 h-8 rounded-lg bg-hecate-600/40 border border-hecate-500/30 hover:bg-hecate-600/60 transition-colors"
            >
              <User className="w-4 h-4 text-hecate-300" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6 bg-grid-pattern">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
