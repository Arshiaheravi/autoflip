import { useState, useEffect, useCallback } from 'react';
import '@/App.css';
import { listingsApi, statsApi, scrapeApi } from '@/lib/api';
import { fmt, fmtNum, sourceLabel, sourceColor, scoreBadge } from '@/lib/utils-app';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';
import {
  Search, RefreshCw, ArrowUpDown, Car, Gauge, Wrench,
  DollarSign, TrendingUp, ExternalLink, AlertTriangle, Zap,
  SlidersHorizontal, Clock, Target, ChevronDown, ChevronUp,
  X,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [listings, setListings] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [selectedListing, setSelectedListing] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    source: '', search: '', min_profit: '', max_price: '',
    min_score: '', damage_type: '', sort_by: 'deal_score', sort_order: 'desc',
  });

  const fetchData = useCallback(async () => {
    try {
      const params = {};
      if (filters.source) params.source = filters.source;
      if (filters.search) params.search = filters.search;
      if (filters.min_profit) params.min_profit = parseFloat(filters.min_profit);
      if (filters.max_price) params.max_price = parseFloat(filters.max_price);
      if (filters.min_score) params.min_score = parseInt(filters.min_score);
      if (filters.damage_type) params.damage_type = filters.damage_type;
      params.sort_by = filters.sort_by;
      params.sort_order = filters.sort_order;

      const [listRes, statsRes] = await Promise.all([
        listingsApi.getAll(params),
        statsApi.get(),
      ]);
      setListings(listRes.data);
      setStats(statsRes.data);
    } catch (e) {
      console.error('Failed to fetch', e);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Poll for scrape status
  useEffect(() => {
    if (!scraping) return;
    const interval = setInterval(async () => {
      try {
        const res = await scrapeApi.status();
        if (res.data?.status === 'completed') {
          setScraping(false);
          toast.success('Scrape complete! Refreshing...');
          fetchData();
        }
      } catch {}
    }, 5000);
    return () => clearInterval(interval);
  }, [scraping, fetchData]);

  const handleScrape = async () => {
    setScraping(true);
    try {
      const res = await scrapeApi.trigger();
      if (res.data?.status === 'already_running') {
        toast.info('Scrape already in progress');
      } else {
        toast.info('Scrape started — this takes 2-3 minutes...');
      }
    } catch (e) {
      toast.error('Failed to start scrape');
      setScraping(false);
    }
  };

  const updateFilter = (key, value) => setFilters(prev => ({ ...prev, [key]: value }));

  return (
    <div className="App min-h-screen grid-bg">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-[#09090b]/80 backdrop-blur-xl border-b border-border/30">
        <div className="max-w-[1600px] mx-auto px-4 md:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 bg-primary/20 rounded-sm">
              <Zap className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-sm font-black tracking-tighter uppercase leading-none" data-testid="app-title">
                AutoFlip Intelligence
              </h1>
              <span className="text-[10px] text-muted-foreground tracking-widest uppercase">
                Ontario Car Profit Calculator
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {stats?.last_scrape && (
              <span className="text-[10px] text-muted-foreground hidden md:block">
                Last scrape: {stats.last_scrape.finished_at ? new Date(stats.last_scrape.finished_at).toLocaleString() : 'Running...'}
              </span>
            )}
            <Button
              size="sm"
              onClick={handleScrape}
              disabled={scraping}
              className="text-xs"
              data-testid="scrape-btn"
            >
              <RefreshCw className={`h-3 w-3 mr-1 ${scraping ? 'animate-spin' : ''}`} />
              {scraping ? 'Scraping...' : 'Scrape Now'}
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-4 md:px-8 py-6 space-y-6">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="stats-bar">
            <StatCard label="Total Listings" value={stats.total_listings} icon={Car} />
            <StatCard label="BUY Deals" value={stats.buy_count} icon={Target} color="text-emerald-500" />
            <StatCard label="WATCH" value={stats.watch_count} icon={Clock} color="text-amber-500" />
            <StatCard label="SKIP" value={stats.skip_count} icon={X} color="text-red-500" />
            <StatCard label="Top Profit" value={fmt(stats.top_profit || stats.avg_profit_best)} icon={TrendingUp} color="text-emerald-500" />
          </div>
        )}

        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3" data-testid="filter-bar">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search year, make, model..."
              value={filters.search}
              onChange={(e) => updateFilter('search', e.target.value)}
              className="pl-9 bg-card border-border/50 text-sm"
              data-testid="search-input"
            />
          </div>

          <Select value={filters.source || 'all'} onValueChange={(v) => updateFilter('source', v === 'all' ? '' : v)}>
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

          <Select value={filters.sort_by} onValueChange={(v) => updateFilter('sort_by', v)}>
            <SelectTrigger className="w-[150px] bg-card border-border/50 text-sm" data-testid="sort-filter">
              <ArrowUpDown className="h-3 w-3 mr-1" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="deal_score">Deal Score</SelectItem>
              <SelectItem value="profit">Profit</SelectItem>
              <SelectItem value="price">Price</SelectItem>
              <SelectItem value="mileage">Mileage</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className="border-border/50 text-xs"
            data-testid="toggle-filters-btn"
          >
            <SlidersHorizontal className="h-3 w-3 mr-1" />
            More Filters
          </Button>

          <Button variant="outline" size="sm" onClick={fetchData} className="border-border/50" data-testid="refresh-btn">
            <RefreshCw className="h-3 w-3" />
          </Button>

          <span className="text-xs text-muted-foreground ml-auto">
            {listings.length} results
          </span>
        </div>

        {/* Expanded Filters */}
        {showFilters && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 bg-card border border-border/50 rounded-sm animate-slide-up" data-testid="expanded-filters">
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Min Profit ($)</label>
              <Input type="number" placeholder="e.g. 2000" value={filters.min_profit} onChange={(e) => updateFilter('min_profit', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="min-profit-filter" />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Max Price ($)</label>
              <Input type="number" placeholder="e.g. 15000" value={filters.max_price} onChange={(e) => updateFilter('max_price', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="max-price-filter" />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Min Score (1-10)</label>
              <Input type="number" placeholder="e.g. 5" value={filters.min_score} onChange={(e) => updateFilter('min_score', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="min-score-filter" />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Damage Type</label>
              <Input placeholder="e.g. FRONT" value={filters.damage_type} onChange={(e) => updateFilter('damage_type', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="damage-filter" />
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 gap-4" data-testid="loading-state">
            <RefreshCw className="h-10 w-10 text-primary animate-spin" />
            <p className="text-sm text-muted-foreground">Loading listings...</p>
          </div>
        )}

        {/* Listings Table/Cards */}
        {!loading && listings.length > 0 && (
          <div className="space-y-2" data-testid="listings-container">
            {/* Table Header */}
            <div className="hidden lg:grid grid-cols-12 gap-2 px-4 py-2 text-[10px] text-muted-foreground uppercase tracking-wider">
              <div className="col-span-3">Vehicle</div>
              <div>Source</div>
              <div className="text-right">Price</div>
              <div className="text-right">Mileage</div>
              <div>Damage</div>
              <div className="text-right">Market Value</div>
              <div className="text-right">Repair Est.</div>
              <div className="text-right">Profit Range</div>
              <div className="text-right">ROI</div>
              <div className="text-center">Score</div>
            </div>

            {listings.map((listing, i) => (
              <ListingRow
                key={listing.id || listing.url}
                listing={listing}
                index={i}
                onClick={() => setSelectedListing(listing)}
              />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && listings.length === 0 && (
          <div className="text-center py-20" data-testid="empty-state">
            <Car className="h-16 w-16 mx-auto mb-4 text-muted-foreground/20" />
            <p className="text-lg text-muted-foreground mb-2">No listings found</p>
            <p className="text-sm text-muted-foreground mb-4">
              {stats?.total_listings === 0
                ? 'Click "Scrape Now" to fetch listings from dealer websites'
                : 'Try adjusting your filters'}
            </p>
            {stats?.total_listings === 0 && (
              <Button onClick={handleScrape} disabled={scraping} data-testid="empty-scrape-btn">
                <RefreshCw className={`h-4 w-4 mr-2 ${scraping ? 'animate-spin' : ''}`} />
                {scraping ? 'Scraping...' : 'Scrape Now'}
              </Button>
            )}
          </div>
        )}
      </main>

      {/* Detail Dialog */}
      {selectedListing && (
        <DetailDialog listing={selectedListing} onClose={() => setSelectedListing(null)} />
      )}

      <Toaster position="bottom-right" theme="dark" />
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color }) {
  return (
    <div className="bg-card border border-border/50 rounded-sm p-3">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className="h-3 w-3 text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground tracking-wider uppercase">{label}</span>
      </div>
      <p className={`text-xl font-bold font-data ${color || ''}`}>{value}</p>
    </div>
  );
}

function ListingRow({ listing, index, onClick }) {
  const l = listing;
  const hasPrice = l.price && l.price > 0;
  const hasProfit = l.profit_best !== null && l.profit_best !== undefined;

  return (
    <>
      {/* Desktop Row */}
      <div
        className="hidden lg:grid grid-cols-12 gap-2 items-center px-4 py-3 bg-card border border-border/50 rounded-sm listing-row cursor-pointer"
        style={{ animationDelay: `${Math.min(index, 20) * 30}ms` }}
        onClick={onClick}
        data-testid={`listing-row-${l.id || index}`}
      >
        {/* Vehicle */}
        <div className="col-span-3 flex items-center gap-3 min-w-0">
          <div className="w-16 h-12 bg-secondary rounded-sm overflow-hidden shrink-0">
            {l.photo ? (
              <img src={l.photo} alt="" className="w-full h-full object-cover" loading="lazy" />
            ) : (
              <div className="flex items-center justify-center h-full"><Car className="h-4 w-4 text-muted-foreground/30" /></div>
            )}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold truncate" style={{ fontFamily: 'Barlow Condensed' }}>{l.title}</p>
            <div className="flex items-center gap-1.5">
              {l.brand && (
                <span className={`text-[9px] px-1.5 py-0.5 rounded-sm ${l.brand.toUpperCase().includes('SALVAGE') ? 'bg-red-500/15 text-red-400' : 'bg-emerald-500/10 text-emerald-500'}`}>
                  {l.brand.toUpperCase().includes('SALVAGE') ? 'SALVAGE' : 'CLEAN'}
                </span>
              )}
              {l.status === 'coming_soon' && <span className="text-[9px] px-1.5 py-0.5 rounded-sm bg-purple-500/15 text-purple-400">COMING SOON</span>}
            </div>
          </div>
        </div>

        {/* Source */}
        <div>
          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-sm ${sourceColor(l.source)}`}>
            {sourceLabel(l.source).split(' ')[0]}
          </span>
        </div>

        {/* Price */}
        <div className="text-right">
          <span className="text-sm font-bold font-data text-primary">
            {hasPrice ? fmt(l.price) : l.price_raw || 'TBD'}
          </span>
        </div>

        {/* Mileage */}
        <div className="text-right text-xs text-muted-foreground font-data">
          {l.mileage ? `${fmtNum(l.mileage)} km` : '—'}
        </div>

        {/* Damage */}
        <div>
          <span className="text-xs text-muted-foreground">{l.damage || '—'}</span>
        </div>

        {/* Market Value */}
        <div className="text-right">
          <span className="text-xs font-data">{l.market_value ? fmt(l.market_value) : 'N/A'}</span>
        </div>

        {/* Repair */}
        <div className="text-right">
          <span className="text-[11px] font-data text-muted-foreground">
            {fmt(l.repair_low)} – {fmt(l.repair_high)}
          </span>
        </div>

        {/* Profit */}
        <div className="text-right">
          {hasProfit ? (
            <div>
              <span className={`text-xs font-bold font-data ${l.profit_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                {fmt(l.profit_best)}
              </span>
              <span className="text-[10px] text-muted-foreground block font-data">
                to {fmt(l.profit_worst)}
              </span>
            </div>
          ) : (
            <span className="text-xs text-muted-foreground">N/A</span>
          )}
        </div>

        {/* ROI */}
        <div className="text-right">
          {l.roi_best !== null && l.roi_best !== undefined ? (
            <span className={`text-xs font-bold font-data ${l.roi_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
              {l.roi_best}%
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">—</span>
          )}
        </div>

        {/* Score */}
        <div className="text-center">
          {l.deal_score && l.deal_label ? (
            <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-sm border ${scoreBadge(l.deal_label)}`}>
              {l.deal_score}/10 {l.deal_label}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">—</span>
          )}
        </div>
      </div>

      {/* Mobile Card */}
      <div
        className="lg:hidden bg-card border border-border/50 rounded-sm p-3 cursor-pointer listing-row"
        onClick={onClick}
        data-testid={`listing-card-${l.id || index}`}
      >
        <div className="flex gap-3">
          <div className="w-20 h-16 bg-secondary rounded-sm overflow-hidden shrink-0">
            {l.photo ? (
              <img src={l.photo} alt="" className="w-full h-full object-cover" loading="lazy" />
            ) : (
              <div className="flex items-center justify-center h-full"><Car className="h-5 w-5 text-muted-foreground/30" /></div>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-bold truncate" style={{ fontFamily: 'Barlow Condensed' }}>{l.title}</p>
              {l.deal_label && (
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm border shrink-0 ${scoreBadge(l.deal_label)}`}>
                  {l.deal_score}/10
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1 text-xs">
              <span className="font-bold font-data text-primary">{hasPrice ? fmt(l.price) : 'TBD'}</span>
              <span className="text-muted-foreground">{l.mileage ? `${fmtNum(l.mileage)} km` : ''}</span>
              <span className={`text-[9px] px-1 py-0.5 rounded-sm ${sourceColor(l.source)}`}>{sourceLabel(l.source).split(' ')[0]}</span>
            </div>
            {hasProfit && (
              <div className="flex items-center gap-3 mt-1 text-xs">
                <span className="text-muted-foreground">Profit:</span>
                <span className={`font-data font-bold ${l.profit_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                  {fmt(l.profit_best)} to {fmt(l.profit_worst)}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function DetailDialog({ listing, onClose }) {
  const l = listing;
  const hasPrice = l.price && l.price > 0;

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[85vh] bg-card border-border/50 p-0 overflow-hidden" data-testid="detail-dialog">
        <ScrollArea className="max-h-[85vh]">
          <div className="p-6 space-y-5">
            <DialogHeader>
              <DialogTitle className="text-2xl font-bold tracking-tight uppercase pr-8" style={{ fontFamily: 'Barlow Condensed' }}>
                {l.title}
              </DialogTitle>
            </DialogHeader>

            {/* Photos */}
            {l.photos?.length > 0 && (
              <div className="flex gap-2 overflow-x-auto pb-2">
                {l.photos.map((photo, i) => (
                  <img key={i} src={photo} alt={`Photo ${i + 1}`} className="h-40 rounded-sm object-cover shrink-0" loading="lazy" />
                ))}
              </div>
            )}
            {!l.photos?.length && l.photo && (
              <img src={l.photo} alt="" className="w-full h-48 rounded-sm object-cover" />
            )}

            {/* Info Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <InfoCell icon={DollarSign} label="Price" value={hasPrice ? fmt(l.price) : l.price_raw || 'TBD'} />
              <InfoCell icon={Gauge} label="Mileage" value={l.mileage ? `${fmtNum(l.mileage)} km` : 'Unknown'} />
              <InfoCell icon={Wrench} label="Damage" value={l.damage || 'None listed'} />
              <InfoCell icon={Car} label="Brand" value={l.brand || 'Unknown'} />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <InfoCell label="Source" value={sourceLabel(l.source)} />
              <InfoCell label="Colour" value={l.colour || 'Unknown'} />
              <InfoCell label="Status" value={l.status?.replace('_', ' ').toUpperCase() || 'Unknown'} />
            </div>

            {l.description && (
              <div className="bg-background/50 border border-border/30 rounded-sm p-3">
                <p className="text-xs text-muted-foreground">{l.description}</p>
              </div>
            )}

            <Separator className="bg-border/30" />

            {/* Profit Breakdown */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>
                  Profit Analysis
                </h3>
                {l.deal_label && (
                  <span className={`text-base font-bold px-3 py-1 rounded-sm border ${scoreBadge(l.deal_label)}`}>
                    {l.deal_score}/10 — {l.deal_label}
                  </span>
                )}
              </div>

              <div className="bg-background/50 border border-border/30 rounded-sm p-4 space-y-2 font-data text-sm">
                <Row label="Market Value" value={l.market_value ? fmt(l.market_value) : 'N/A'} note={l.brand?.toUpperCase().includes('SALVAGE') ? '(25% salvage penalty applied)' : ''} />
                <Row label="Purchase Price" value={hasPrice ? fmt(l.price) : 'TBD'} />
                <Row label="Repair Estimate (Low)" value={fmt(l.repair_low)} dim />
                <Row label="Repair Estimate (High)" value={fmt(l.repair_high)} dim />
                <Row label="Ontario Fees" value={l.fees ? fmt(l.fees) : 'N/A'} dim note="HST 13% + OMVIC $22 + MTO $32 + Safety $100" />
                <Separator className="bg-border/30" />
                <Row label="Best Case Profit" value={l.profit_best !== null ? fmt(l.profit_best) : 'N/A'} highlight={l.profit_best > 0} />
                <Row label="Worst Case Profit" value={l.profit_worst !== null ? fmt(l.profit_worst) : 'N/A'} highlight={l.profit_worst > 0} />
                <Row label="ROI (Best)" value={l.roi_best !== null ? `${l.roi_best}%` : 'N/A'} />
                <Row label="ROI (Worst)" value={l.roi_worst !== null ? `${l.roi_worst}%` : 'N/A'} />
              </div>

              {/* Warnings */}
              {l.profit_worst !== null && l.profit_worst < 0 && (
                <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-sm">
                  <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
                  <span className="text-sm text-red-400">
                    Worst case scenario results in a loss of {fmt(Math.abs(l.profit_worst))}
                  </span>
                </div>
              )}
              {l.status === 'coming_soon' && (
                <div className="flex items-center gap-2 p-3 bg-purple-500/10 border border-purple-500/20 rounded-sm">
                  <Clock className="h-4 w-4 text-purple-400 shrink-0" />
                  <span className="text-sm text-purple-400">This listing is marked COMING SOON — price may change</span>
                </div>
              )}
              {!hasPrice && (
                <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-sm">
                  <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                  <span className="text-sm text-amber-400">Price not yet available — profit calculation incomplete</span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1 border-border/50" asChild>
                <a href={l.url} target="_blank" rel="noopener noreferrer" data-testid="view-original-btn">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View Original Listing
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
    <div className="bg-background/50 border border-border/30 rounded-sm p-2.5">
      <div className="flex items-center gap-1 mb-0.5">
        {Icon && <Icon className="h-3 w-3 text-muted-foreground" />}
        <span className="text-[10px] text-muted-foreground tracking-wider uppercase">{label}</span>
      </div>
      <p className="text-sm font-bold">{value}</p>
    </div>
  );
}

function Row({ label, value, highlight, dim, note }) {
  return (
    <div className="flex justify-between items-center">
      <div className="flex items-center gap-2">
        <span className={dim ? 'text-muted-foreground' : ''}>{label}</span>
        {note && <span className="text-[10px] text-muted-foreground">({note})</span>}
      </div>
      <span className={`font-bold ${highlight === true ? 'text-emerald-500' : highlight === false ? 'text-red-500' : ''}`}>
        {value}
      </span>
    </div>
  );
}

export default App;
