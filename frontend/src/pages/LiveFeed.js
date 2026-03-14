import { useState, useEffect, useCallback } from 'react';
import { useAppStore } from '@/lib/store';
import { listingsApi, statsApi, watchlistApi } from '@/lib/api';
import { formatCurrency, formatNumber, timeAgo, daysSince, getSourceLabel, getSourceBadgeClass, getScoreBadgeClass, getStaleClass } from '@/lib/utils-app';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import {
  Search, SlidersHorizontal, ArrowUpDown, BookmarkPlus,
  Eye, AlertTriangle, TrendingUp, Clock, Car, Gauge,
  Wrench, DollarSign, Target, Camera, Shield, ChevronRight,
  RefreshCw,
} from 'lucide-react';

export default function LiveFeed() {
  const { listings, setListings, filters, setFilters, stats, setStats } = useAppStore();
  const [loading, setLoading] = useState(true);
  const [selectedListing, setSelectedListing] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const params = {};
      if (filters.source) params.source = filters.source;
      if (filters.min_price) params.min_price = filters.min_price;
      if (filters.max_price) params.max_price = filters.max_price;
      if (filters.min_score) params.min_score = filters.min_score;
      if (filters.damage_type) params.damage_type = filters.damage_type;
      if (filters.make) params.make = filters.make;
      params.sort_by = filters.sort_by;
      params.sort_order = filters.sort_order;
      const [listRes, statsRes] = await Promise.all([
        listingsApi.getAll(params),
        statsApi.get(),
      ]);
      setListings(listRes.data);
      setStats(statsRes.data);
    } catch (e) {
      console.error('Failed to fetch listings', e);
    } finally {
      setLoading(false);
    }
  }, [filters, setListings, setStats]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleAddToWatchlist = async (listing) => {
    try {
      await watchlistApi.add({ listing_id: listing.id, notes: '', tags: [] });
      toast.success('Added to watchlist');
    } catch (e) {
      if (e.response?.status === 400) toast.info('Already in watchlist');
      else toast.error('Failed to add');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="loading-spinner">
        <RefreshCw className="h-8 w-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="live-feed-page">
      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="stats-bar">
          <StatCard label="Total Profit Potential" value={formatCurrency(stats.total_profit_potential)} accent="text-emerald-500" />
          <StatCard label="Buy Now Deals" value={stats.buy_now_count} accent="text-emerald-500" />
          <StatCard label="Watch List" value={stats.watch_count} accent="text-amber-500" />
          <StatCard label="Portfolio ROI" value={`${stats.portfolio?.avg_roi || 0}%`} accent="text-primary" />
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3" data-testid="filter-bar">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search make/model..."
            value={filters.make}
            onChange={(e) => setFilters({ make: e.target.value })}
            className="pl-9 bg-card border-border/50 text-sm"
            data-testid="search-input"
          />
        </div>

        <Select value={filters.source || 'all'} onValueChange={(v) => setFilters({ source: v === 'all' ? '' : v })}>
          <SelectTrigger className="w-[180px] bg-card border-border/50 text-sm" data-testid="source-filter">
            <SelectValue placeholder="All Sources" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Sources</SelectItem>
            <SelectItem value="cathcart_rebuilders">Cathcart Rebuilders</SelectItem>
            <SelectItem value="cathcart_used">Cathcart Used</SelectItem>
            <SelectItem value="picnsave">Pic N Save</SelectItem>
          </SelectContent>
        </Select>

        <Select value={filters.sort_by} onValueChange={(v) => setFilters({ sort_by: v })}>
          <SelectTrigger className="w-[160px] bg-card border-border/50 text-sm" data-testid="sort-filter">
            <ArrowUpDown className="h-3 w-3 mr-1" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="deal_score">Deal Score</SelectItem>
            <SelectItem value="price">Price</SelectItem>
            <SelectItem value="profit">Profit</SelectItem>
            <SelectItem value="first_seen_at">Newest</SelectItem>
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className="border-border/50"
          data-testid="toggle-filters-btn"
        >
          <SlidersHorizontal className="h-4 w-4 mr-1" />
          Filters
        </Button>

        <Button variant="outline" size="sm" onClick={fetchData} className="border-border/50" data-testid="refresh-btn">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Expanded Filters */}
      {showFilters && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 bg-card border border-border/50 rounded-sm animate-slide-up" data-testid="expanded-filters">
          <Input type="number" placeholder="Min Price" value={filters.min_price} onChange={(e) => setFilters({ min_price: e.target.value })} className="bg-background border-border/50 text-sm" data-testid="min-price-filter" />
          <Input type="number" placeholder="Max Price" value={filters.max_price} onChange={(e) => setFilters({ max_price: e.target.value })} className="bg-background border-border/50 text-sm" data-testid="max-price-filter" />
          <Input type="number" placeholder="Min Score" value={filters.min_score} onChange={(e) => setFilters({ min_score: e.target.value })} className="bg-background border-border/50 text-sm" data-testid="min-score-filter" />
          <Input placeholder="Damage Type" value={filters.damage_type} onChange={(e) => setFilters({ damage_type: e.target.value })} className="bg-background border-border/50 text-sm" data-testid="damage-type-filter" />
        </div>
      )}

      {/* Listings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" data-testid="listings-grid">
        {listings.map((listing, i) => (
          <ListingCard
            key={listing.id}
            listing={listing}
            index={i}
            onSelect={() => setSelectedListing(listing)}
            onWatch={() => handleAddToWatchlist(listing)}
          />
        ))}
      </div>

      {listings.length === 0 && (
        <div className="text-center py-16 text-muted-foreground" data-testid="empty-state">
          <Car className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">No listings match your filters</p>
        </div>
      )}

      {/* Detail Dialog */}
      {selectedListing && (
        <ListingDetailDialog
          listing={selectedListing}
          onClose={() => setSelectedListing(null)}
          onWatch={() => handleAddToWatchlist(selectedListing)}
        />
      )}
    </div>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <div className="bg-card border border-border/50 p-4 rounded-sm">
      <p className="text-xs text-muted-foreground tracking-wider uppercase mb-1">{label}</p>
      <p className={`text-2xl font-bold font-mono-data ${accent}`}>{value}</p>
    </div>
  );
}

function ListingCard({ listing, index, onSelect, onWatch }) {
  const pc = listing.profit_calc;
  const days = daysSince(listing.first_seen_at);
  const staleClass = getStaleClass(days);
  const photo = listing.photos?.[0];

  return (
    <div
      className="listing-card bg-card border border-border/50 rounded-sm overflow-hidden cursor-pointer"
      style={{ animationDelay: `${index * 50}ms` }}
      onClick={onSelect}
      data-testid={`listing-card-${listing.id}`}
    >
      {/* Photo */}
      <div className="relative h-40 bg-secondary overflow-hidden">
        {photo ? (
          <img src={photo} alt={listing.title} className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <div className="flex items-center justify-center h-full">
            <Car className="h-10 w-10 text-muted-foreground/30" />
          </div>
        )}
        {/* Badges overlay */}
        <div className="absolute top-2 left-2 flex gap-1.5">
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-sm ${getSourceBadgeClass(listing.source)}`}>
            {getSourceLabel(listing.source).split(' ')[0]}
          </span>
          {listing.status === 'coming_soon' && (
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-sm bg-purple-500/20 text-purple-400">
              COMING SOON
            </span>
          )}
        </div>
        {/* Score */}
        {pc && (
          <div className="absolute top-2 right-2">
            <div className={`text-xs font-bold px-2 py-1 rounded-sm ${getScoreBadgeClass(pc.recommendation)}`} data-testid={`deal-score-${listing.id}`}>
              {pc.deal_score}/100
            </div>
          </div>
        )}
        {/* Days on market */}
        {days > 0 && (
          <div className="absolute bottom-2 right-2">
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-sm ${staleClass || 'bg-black/60 text-zinc-300'}`}>
              {days}d
            </span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3 space-y-2">
        <h3 className="text-sm font-bold tracking-tight truncate" style={{ fontFamily: 'Barlow Condensed' }}>
          {listing.title}
        </h3>

        <div className="flex items-center justify-between">
          <span className="text-lg font-bold font-mono-data text-primary">
            {formatCurrency(listing.price)}
          </span>
          {pc && (
            <Badge variant="outline" className={`text-[10px] ${pc.recommendation === 'BUY NOW' ? 'border-emerald-500/50 text-emerald-500' : pc.recommendation === 'WATCH' ? 'border-amber-500/50 text-amber-500' : 'border-red-500/50 text-red-500'}`}>
              {pc.recommendation}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
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

        {pc && (
          <div className="flex items-center justify-between pt-1 border-t border-border/30">
            <div>
              <span className="text-[10px] text-muted-foreground block">Net Profit</span>
              <span className={`text-sm font-bold font-mono-data ${pc.net_profit_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                {formatCurrency(pc.net_profit_best)}
              </span>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-muted-foreground block">ROI</span>
              <span className={`text-sm font-bold font-mono-data ${pc.roi_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                {pc.roi_best}%
              </span>
            </div>
          </div>
        )}

        <div className="flex gap-1.5 pt-1">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 h-7 text-xs border-border/50"
            onClick={(e) => { e.stopPropagation(); onWatch(); }}
            data-testid={`watch-btn-${listing.id}`}
          >
            <BookmarkPlus className="h-3 w-3 mr-1" />
            Watch
          </Button>
          <Button
            size="sm"
            className="flex-1 h-7 text-xs"
            onClick={(e) => { e.stopPropagation(); onSelect(); }}
            data-testid={`details-btn-${listing.id}`}
          >
            <Eye className="h-3 w-3 mr-1" />
            Details
          </Button>
        </div>
      </div>
    </div>
  );
}

function ListingDetailDialog({ listing, onClose, onWatch }) {
  const pc = listing.profit_calc;
  const ai = listing.ai_analysis;

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] bg-card border-border/50 p-0 overflow-hidden" data-testid="listing-detail-dialog">
        <ScrollArea className="max-h-[85vh]">
          <div className="p-6 space-y-6">
            <DialogHeader>
              <DialogTitle className="text-2xl font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>
                {listing.title}
              </DialogTitle>
            </DialogHeader>

            {/* Photos */}
            {listing.photos?.length > 0 && (
              <div className="flex gap-2 overflow-x-auto pb-2">
                {listing.photos.map((photo, i) => (
                  <img key={i} src={photo} alt={`Photo ${i + 1}`} className="h-48 rounded-sm object-cover shrink-0" />
                ))}
              </div>
            )}

            {/* Quick Info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <InfoCell icon={DollarSign} label="Price" value={formatCurrency(listing.price)} />
              <InfoCell icon={Gauge} label="Mileage" value={`${formatNumber(listing.mileage)} km`} />
              <InfoCell icon={Wrench} label="Damage" value={listing.damage_text || 'None'} />
              <InfoCell icon={Shield} label="Brand" value={listing.brand_text || 'N/A'} />
            </div>

            {/* Deal Score */}
            {pc && (
              <>
                <Separator className="bg-border/30" />
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>
                      Deal Analysis
                    </h3>
                    <div className={`text-xl font-bold px-4 py-1.5 rounded-sm ${getScoreBadgeClass(pc.recommendation)}`}>
                      {pc.deal_score}/100 - {pc.recommendation}
                    </div>
                  </div>

                  {/* Score Breakdown */}
                  {pc.score_breakdown && (
                    <div className="grid grid-cols-4 gap-2">
                      <ScoreBar label="Profit" value={pc.score_breakdown.profit_margin} max={35} />
                      <ScoreBar label="Demand" value={pc.score_breakdown.market_demand} max={25} />
                      <ScoreBar label="Repair" value={pc.score_breakdown.repair_risk} max={20} />
                      <ScoreBar label="Timing" value={pc.score_breakdown.timing} max={20} />
                    </div>
                  )}

                  {/* Profit Table */}
                  <div className="bg-background/50 border border-border/30 rounded-sm p-4 space-y-2">
                    <ProfitRow label="Market Value" value={formatCurrency(pc.market_value)} />
                    <ProfitRow label="Flip Price" value={formatCurrency(pc.flip_price)} />
                    <ProfitRow label="Repair (Best)" value={formatCurrency(pc.repair_best)} negative />
                    <ProfitRow label="Repair (Worst)" value={formatCurrency(pc.repair_worst)} negative />
                    <ProfitRow label="Ontario Fees" value={formatCurrency(pc.total_fees)} negative />
                    <Separator className="bg-border/30" />
                    <ProfitRow label="Net Profit (Best)" value={formatCurrency(pc.net_profit_best)} highlight={pc.net_profit_best > 0} />
                    <ProfitRow label="Net Profit (Worst)" value={formatCurrency(pc.net_profit_worst)} highlight={pc.net_profit_worst > 0} />
                    <ProfitRow label="ROI Range" value={`${pc.roi_worst}% - ${pc.roi_best}%`} />
                    <ProfitRow label="Profit/Day (30d flip)" value={formatCurrency(pc.profit_per_day)} />
                  </div>

                  {/* Seasonal Advice */}
                  {pc.seasonal_hold_advice && (
                    <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-sm">
                      <TrendingUp className="h-4 w-4 text-amber-500 shrink-0" />
                      <span className="text-sm text-amber-500">{pc.seasonal_hold_advice}</span>
                    </div>
                  )}

                  {/* Red Flags */}
                  {pc.red_flags?.length > 0 && (
                    <div className="space-y-1.5">
                      {pc.red_flags.map((flag, i) => (
                        <div key={i} className="flex items-center gap-2 p-2 bg-red-500/10 border border-red-500/20 rounded-sm">
                          <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
                          <span className="text-sm text-red-400">{flag}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* AI Analysis */}
            {ai && (
              <>
                <Separator className="bg-border/30" />
                <div className="space-y-3">
                  <h3 className="text-lg font-bold tracking-tight uppercase flex items-center gap-2" style={{ fontFamily: 'Barlow Condensed' }}>
                    <Camera className="h-5 w-5 text-primary" />
                    AI Photo Analysis
                  </h3>
                  <p className="text-sm text-muted-foreground">{ai.summary}</p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <AiTag label="Severity" value={ai.damage_severity} />
                    <AiTag label="Airbags" value={ai.airbag_status} />
                    <AiTag label="Interior" value={ai.interior_condition} />
                    <AiTag label="Rust" value={ai.rust_detected ? 'Yes' : 'No'} />
                    <AiTag label="Frame Damage" value={ai.frame_damage_suspected ? 'Suspected' : 'No'} />
                    <AiTag label="Confidence" value={ai.confidence_level} />
                  </div>
                  {ai.red_flags?.length > 0 && (
                    <div className="space-y-1">
                      {ai.red_flags.map((flag, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs text-red-400">
                          <AlertTriangle className="h-3 w-3" />
                          {flag}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <Button className="flex-1" onClick={onWatch} data-testid="detail-watch-btn">
                <BookmarkPlus className="h-4 w-4 mr-2" />
                Add to Watchlist
              </Button>
              <Button variant="outline" className="flex-1" asChild>
                <a href={listing.url} target="_blank" rel="noopener noreferrer" data-testid="view-listing-btn">
                  View Original Listing
                  <ChevronRight className="h-4 w-4 ml-1" />
                </a>
              </Button>
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

function InfoCell({ icon: Icon, label, value }) {
  return (
    <div className="bg-background/50 border border-border/30 rounded-sm p-3">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className="h-3 w-3 text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground tracking-wider uppercase">{label}</span>
      </div>
      <p className="text-sm font-bold font-mono-data">{value}</p>
    </div>
  );
}

function ScoreBar({ label, value, max }) {
  const pct = (value / max) * 100;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px]">
        <span className="text-muted-foreground uppercase tracking-wider">{label}</span>
        <span className="font-mono-data font-bold">{value}/{max}</span>
      </div>
      <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
        <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ProfitRow({ label, value, negative, highlight }) {
  return (
    <div className="flex justify-between items-center text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-mono-data font-bold ${highlight === true ? 'text-emerald-500' : highlight === false ? 'text-red-500' : negative ? 'text-red-400/70' : ''}`}>
        {negative && '- '}{value}
      </span>
    </div>
  );
}

function AiTag({ label, value }) {
  const color = value === 'minor' || value === 'intact' || value === 'excellent' || value === 'high' || value === 'No'
    ? 'text-emerald-500 bg-emerald-500/10'
    : value === 'moderate' || value === 'good' || value === 'medium' || value === 'unknown'
    ? 'text-amber-500 bg-amber-500/10'
    : 'text-red-500 bg-red-500/10';
  return (
    <div className={`px-3 py-2 rounded-sm ${color}`}>
      <span className="text-[10px] block opacity-70 uppercase tracking-wider">{label}</span>
      <span className="text-sm font-bold capitalize">{value}</span>
    </div>
  );
}
