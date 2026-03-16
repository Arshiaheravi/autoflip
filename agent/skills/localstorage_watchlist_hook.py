"""
Skill: localStorage Watchlist Hook (React)

A React hook that persists a set of saved items to localStorage.
Returns toggle, isSaved, count — no backend needed for v1.

Pattern: useWatchlist() in utils-app.js

Usage:
  const { isSaved, toggle, count } = useWatchlist();
  // In a row component:
  <button onClick={(e) => { e.stopPropagation(); toggle(listing); }}>
    <Bookmark fill={isSaved(listing) ? 'currentColor' : 'none'} />
  </button>
  // Tab toggle:
  {activeTab === 'saved' ? listings.filter(l => isSaved(l)) : listings}

Key rules:
- Use a stable ID: l.id || l._id || l.url
- Always stopPropagation on nested buttons inside clickable rows
- Mock useWatchlist in jest.mock('@/lib/utils-app') so tests don't crash
- fill prop on lucide icons = filled (active) vs outline (inactive)
"""

# JavaScript implementation (for reference):
IMPLEMENTATION = """
import { useState, useCallback } from 'react';

const WATCHLIST_KEY = 'autoflip_watchlist';
function listingId(l) { return l.id || l._id || l.url || ''; }

export function useWatchlist() {
  const [saved, setSaved] = useState(() => {
    try { return JSON.parse(localStorage.getItem(WATCHLIST_KEY) || '{}'); }
    catch { return {}; }
  });

  const toggle = useCallback((listing) => {
    const id = listingId(listing);
    if (!id) return;
    setSaved(prev => {
      const next = { ...prev };
      if (next[id]) delete next[id];
      else next[id] = { id, title: listing.title, price: listing.price };
      localStorage.setItem(WATCHLIST_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const isSaved = useCallback((listing) => !!saved[listingId(listing)], [saved]);
  return { saved, toggle, isSaved, count: Object.keys(saved).length };
}
"""
