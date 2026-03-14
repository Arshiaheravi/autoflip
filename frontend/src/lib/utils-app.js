export function formatCurrency(value) {
  if (value === null || value === undefined) return '$0';
  return new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value) {
  if (value === null || value === undefined) return '0';
  return new Intl.NumberFormat('en-CA').format(value);
}

export function timeAgo(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

export function daysSince(dateStr) {
  if (!dateStr) return 0;
  const date = new Date(dateStr);
  const now = new Date();
  return Math.floor((now - date) / 86400000);
}

export function getSourceLabel(source) {
  const labels = {
    cathcart_rebuilders: 'Cathcart Rebuilders',
    cathcart_used: 'Cathcart Used',
    picnsave: 'Pic N Save',
  };
  return labels[source] || source;
}

export function getSourceBadgeClass(source) {
  return `source-${source}`;
}

export function getScoreBadgeClass(recommendation) {
  if (recommendation === 'BUY NOW') return 'score-buy';
  if (recommendation === 'WATCH') return 'score-watch';
  return 'score-skip';
}

export function getStaleClass(days) {
  if (days > 14) return 'stale-danger';
  if (days > 7) return 'stale-warning';
  return '';
}
