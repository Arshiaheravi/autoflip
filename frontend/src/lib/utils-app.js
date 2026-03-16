export function fmt(value) {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value);
}

export function fmtNum(value) {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-CA').format(value);
}

export function sourceLabel(source) {
  return { cathcart_rebuilders: 'Cathcart Rebuilders', cathcart_used: 'Cathcart Used', picnsave: 'Pic N Save' }[source] || source;
}

export function sourceColor(source) {
  return {
    cathcart_rebuilders: 'bg-blue-500/15 text-blue-400',
    cathcart_used: 'bg-violet-500/15 text-violet-400',
    picnsave: 'bg-amber-500/15 text-amber-400',
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
