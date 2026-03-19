import { useState, useCallback } from 'react';

export function fmt(value) {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value);
}

export function fmtNum(value) {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-CA').format(value);
}

export function sourceLabel(source) {
  return { cathcart_rebuilders: 'Cathcart Rebuilders', cathcart_used: 'Cathcart Used', picnsave: 'Pic N Save', salvagereseller: 'SalvageReseller', copart_on: 'Copart Ontario' }[source] || source;
}

export function sourceColor(source) {
  return {
    cathcart_rebuilders: 'bg-blue-500/15 text-blue-400',
    cathcart_used: 'bg-violet-500/15 text-violet-400',
    picnsave: 'bg-amber-500/15 text-amber-400',
    salvagereseller: 'bg-orange-500/15 text-orange-400',
    copart_on: 'bg-teal-500/15 text-teal-400',
  }[source] || 'bg-zinc-500/15 text-zinc-400';
}

export function scoreBadge(label) {
  if (label === 'BUY') return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
  if (label === 'WATCH') return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
  return 'bg-red-500/15 text-red-400 border-red-500/30';
}

export function daysSince(dateStr) {
  if (!dateStr) return 0;
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000);
}

export function fmtDate(dateStr) {
  if (!dateStr) return '--';
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now - d;
  const diffH = Math.floor(diffMs / 3600000);
  const diffD = Math.floor(diffMs / 86400000);
  if (diffH < 1) return 'Just now';
  if (diffH < 24) return `${diffH}h ago`;
  if (diffD === 1) return 'Yesterday';
  if (diffD < 7) return `${diffD}d ago`;
  return d.toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
}

/**
 * Builds an AutoTrader.ca search URL pre-filtered by title keyword + Ontario province.
 * title: "2019 Toyota Camry XLE" → https://www.autotrader.ca/cars/?kw=2019+Toyota+Camry+XLE&prv=Ontario
 */
export function buildAutotraderUrl(title) {
  if (!title) return null;
  const kw = encodeURIComponent(title.trim());
  return `https://www.autotrader.ca/cars/?kw=${kw}&prv=Ontario`;
}

/**
 * Returns true if the listing has recorded a price drop.
 */
export function hasPriceDrop(listing) {
  return listing?.has_price_drop === true && (listing?.price_drop_amount || 0) > 0;
}

/**
 * Returns a short human-readable price-drop label, e.g. "↓ $500 (8%)"
 */
export function priceDroplabel(listing) {
  const amt = listing?.price_drop_amount || 0;
  const pct = listing?.price_drop_pct || 0;
  if (!amt) return null;
  return `↓ $${Math.abs(amt).toLocaleString('en-CA')} (${Math.abs(pct)}%)`;
}

const WATCHLIST_KEY = 'autoflip_watchlist';

function listingId(l) {
  return l.id || l._id || l.url || '';
}

/**
 * Hook: localStorage-backed watchlist. Returns { saved, isSaved, toggle, count }.
 * saved = { [id]: { id, title, price, deal_label } }
 */
export function useWatchlist() {
  const [saved, setSaved] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(WATCHLIST_KEY) || '{}');
    } catch {
      return {};
    }
  });

  const toggle = useCallback((listing) => {
    const id = listingId(listing);
    if (!id) return;
    setSaved(prev => {
      const next = { ...prev };
      if (next[id]) {
        delete next[id];
      } else {
        next[id] = { id, title: listing.title, price: listing.price, deal_label: listing.deal_label };
      }
      localStorage.setItem(WATCHLIST_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const isSaved = useCallback((listing) => !!saved[listingId(listing)], [saved]);

  return { saved, toggle, isSaved, count: Object.keys(saved).length };
}
