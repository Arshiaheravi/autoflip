import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import {
  LayoutDashboard,
  BookmarkCheck,
  Briefcase,
  BarChart3,
  Settings,
  Radio,
  ChevronLeft,
  ChevronRight,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { id: 'feed', label: 'Live Feed', icon: LayoutDashboard },
  { id: 'watchlist', label: 'Watchlist', icon: BookmarkCheck },
  { id: 'portfolio', label: 'Portfolio', icon: Briefcase },
  { id: 'market', label: 'Market Intel', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export default function AppLayout({ children }) {
  const { activePage, setActivePage, wsConnected, stats } = useAppStore();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden" data-testid="app-layout">
      {/* Sidebar */}
      <aside
        className={cn(
          'flex flex-col border-r border-border/50 bg-card transition-all duration-300 z-30',
          collapsed ? 'w-16' : 'w-56'
        )}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 h-16 border-b border-border/50">
          <div className="flex items-center justify-center w-8 h-8 bg-primary/20 rounded-sm">
            <Zap className="h-5 w-5 text-primary" />
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <h1 className="text-sm font-black tracking-tighter uppercase leading-none" style={{ fontFamily: 'Barlow Condensed' }}>
                AutoFlip
              </h1>
              <span className="text-[10px] text-muted-foreground tracking-widest uppercase">Intelligence</span>
            </div>
          )}
        </div>

        {/* Nav Items */}
        <nav className="flex-1 py-4 space-y-1 px-2" data-testid="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setActivePage(item.id)}
              data-testid={`nav-${item.id}`}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-all duration-200 rounded-sm',
                activePage === item.id
                  ? 'nav-active'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* Status */}
        <div className="px-3 py-3 border-t border-border/50">
          <div className="flex items-center gap-2">
            <Radio className={cn('h-3 w-3', wsConnected ? 'text-emerald-500' : 'text-red-500')} />
            {!collapsed && (
              <span className="text-[10px] text-muted-foreground tracking-wider uppercase">
                {wsConnected ? 'Live' : 'Offline'}
              </span>
            )}
          </div>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          data-testid="sidebar-toggle"
          className="flex items-center justify-center h-10 border-t border-border/50 text-muted-foreground hover:text-foreground transition-colors"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto grid-texture" data-testid="main-content">
        {/* Top bar */}
        <header className="sticky top-0 z-20 glass border-b border-border/30 px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2
              className="text-xl font-bold tracking-tight uppercase"
              style={{ fontFamily: 'Barlow Condensed' }}
              data-testid="page-title"
            >
              {NAV_ITEMS.find(n => n.id === activePage)?.label || 'Dashboard'}
            </h2>
          </div>
          <div className="flex items-center gap-4">
            {stats && (
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">Active:</span>
                  <span className="font-mono-data font-bold">{stats.total_listings}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span className="font-mono-data font-bold text-emerald-500">{stats.buy_now_count}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <span className="font-mono-data font-bold text-amber-500">{stats.watch_count}</span>
                </div>
              </div>
            )}
          </div>
        </header>

        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
