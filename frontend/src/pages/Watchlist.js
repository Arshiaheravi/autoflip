import { useState, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { watchlistApi } from '@/lib/api';
import { formatCurrency, formatNumber, daysSince, getSourceLabel, getScoreBadgeClass, getStaleClass } from '@/lib/utils-app';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import {
  BookmarkX, StickyNote, Tag, Clock, TrendingDown, TrendingUp,
  Gauge, Wrench, DollarSign, RefreshCw, Car, ExternalLink,
} from 'lucide-react';

export default function Watchlist() {
  const { watchlist, setWatchlist } = useAppStore();
  const [loading, setLoading] = useState(true);
  const [editingNotes, setEditingNotes] = useState(null);
  const [noteText, setNoteText] = useState('');

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const res = await watchlistApi.getAll();
      setWatchlist(res.data);
    } catch (e) {
      console.error('Failed to fetch watchlist', e);
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (id) => {
    try {
      await watchlistApi.remove(id);
      setWatchlist(watchlist.filter(w => w.id !== id));
      toast.success('Removed from watchlist');
    } catch (e) {
      toast.error('Failed to remove');
    }
  };

  const handleSaveNotes = async (id) => {
    try {
      await watchlistApi.update(id, { notes: noteText });
      setEditingNotes(null);
      fetchWatchlist();
      toast.success('Notes saved');
    } catch (e) {
      toast.error('Failed to save notes');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="watchlist-loading">
        <RefreshCw className="h-8 w-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="watchlist-page">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">
            {watchlist.length} vehicle{watchlist.length !== 1 ? 's' : ''} being tracked
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchWatchlist} className="border-border/50" data-testid="refresh-watchlist-btn">
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>

      {watchlist.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground" data-testid="watchlist-empty">
          <Car className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg mb-2">No vehicles in watchlist</p>
          <p className="text-sm">Add listings from the Live Feed to track them here</p>
        </div>
      ) : (
        <div className="space-y-4">
          {watchlist.map((item) => {
            const listing = item.listing;
            const pc = item.profit_calc;
            if (!listing) return null;
            const days = daysSince(listing.first_seen_at);
            const watchDays = daysSince(item.added_at);
            const staleClass = getStaleClass(days);

            return (
              <div key={item.id} className="bg-card border border-border/50 rounded-sm p-4" data-testid={`watchlist-item-${item.id}`}>
                <div className="flex gap-4">
                  {/* Photo */}
                  <div className="w-32 h-24 bg-secondary rounded-sm overflow-hidden shrink-0">
                    {listing.photos?.[0] ? (
                      <img src={listing.photos[0]} alt={listing.title} className="w-full h-full object-cover" />
                    ) : (
                      <div className="flex items-center justify-center h-full">
                        <Car className="h-8 w-8 text-muted-foreground/30" />
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="text-base font-bold tracking-tight truncate" style={{ fontFamily: 'Barlow Condensed' }}>
                          {listing.title}
                        </h3>
                        <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                          <span>{getSourceLabel(listing.source)}</span>
                          <span className="flex items-center gap-1">
                            <Gauge className="h-3 w-3" />
                            {formatNumber(listing.mileage)} km
                          </span>
                          {listing.damage_text && (
                            <span className="flex items-center gap-1">
                              <Wrench className="h-3 w-3" />
                              {listing.damage_text}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {pc && (
                          <div className={`text-xs font-bold px-2 py-1 rounded-sm ${getScoreBadgeClass(pc.recommendation)}`}>
                            {pc.deal_score}/100
                          </div>
                        )}
                        <span className="text-lg font-bold font-mono-data text-primary">
                          {formatCurrency(listing.price)}
                        </span>
                      </div>
                    </div>

                    {/* Metrics Row */}
                    <div className="flex items-center gap-4 mt-3 text-xs">
                      {pc && (
                        <>
                          <div>
                            <span className="text-muted-foreground">Net Profit: </span>
                            <span className={`font-mono-data font-bold ${pc.net_profit_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                              {formatCurrency(pc.net_profit_best)}
                            </span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">ROI: </span>
                            <span className="font-mono-data font-bold">{pc.roi_best}%</span>
                          </div>
                        </>
                      )}
                      <div className={`flex items-center gap-1 ${staleClass ? staleClass : ''}`}>
                        <Clock className="h-3 w-3" />
                        <span>{days}d on market</span>
                      </div>
                      <div className="text-muted-foreground">
                        Watching {watchDays}d
                      </div>
                    </div>

                    {/* Notes */}
                    {editingNotes === item.id ? (
                      <div className="mt-3 space-y-2">
                        <Textarea
                          value={noteText}
                          onChange={(e) => setNoteText(e.target.value)}
                          placeholder="Add your notes..."
                          className="bg-background border-border/50 text-sm h-20"
                          data-testid={`notes-input-${item.id}`}
                        />
                        <div className="flex gap-2">
                          <Button size="sm" onClick={() => handleSaveNotes(item.id)} data-testid={`save-notes-btn-${item.id}`}>Save</Button>
                          <Button size="sm" variant="outline" onClick={() => setEditingNotes(null)}>Cancel</Button>
                        </div>
                      </div>
                    ) : item.notes ? (
                      <div className="mt-2 p-2 bg-background/50 border border-border/30 rounded-sm text-xs text-muted-foreground cursor-pointer" onClick={() => { setEditingNotes(item.id); setNoteText(item.notes); }}>
                        <StickyNote className="h-3 w-3 inline mr-1" />
                        {item.notes}
                      </div>
                    ) : null}

                    {/* Actions */}
                    <div className="flex gap-2 mt-3">
                      <Button size="sm" variant="outline" className="h-7 text-xs border-border/50" onClick={() => { setEditingNotes(item.id); setNoteText(item.notes || ''); }} data-testid={`edit-notes-btn-${item.id}`}>
                        <StickyNote className="h-3 w-3 mr-1" />
                        Notes
                      </Button>
                      <Button size="sm" variant="outline" className="h-7 text-xs border-border/50" asChild>
                        <a href={listing.url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="h-3 w-3 mr-1" />
                          View
                        </a>
                      </Button>
                      <Button size="sm" variant="outline" className="h-7 text-xs border-red-500/30 text-red-500 hover:bg-red-500/10" onClick={() => handleRemove(item.id)} data-testid={`remove-watchlist-btn-${item.id}`}>
                        <BookmarkX className="h-3 w-3 mr-1" />
                        Remove
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
