import { useState, useEffect, useCallback } from 'react';
import { listingsApi, statsApi } from '@/lib/api';
import { fmt, fmtNum, sourceLabel, sourceColor, scoreBadge, fmtDate, hasPriceDrop, priceDroplabel, useWatchlist } from '@/lib/utils-app';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import ListingDetail from '@/components/shared/ListingDetail';
import { useLanguage } from '@/lib/LanguageContext';
import {
  Search, RefreshCw, ArrowUpDown, Car, Gauge, Wrench,
  TrendingUp, TrendingDown, AlertTriangle, SlidersHorizontal,
  Target, X, Settings, CheckCircle2, Shield, Eye, Radio, Tag, Bookmark,
} from 'lucide-react';

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

function FilterField({ label, children }) {
  return (
    <div>
      <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">{label}</label>
      {children}
    </div>
  );
}

function ListingRow({ listing, index, onClick, isSaved, onToggleSave }) {
  const { t } = useLanguage();
  const l = listing;
  const hasPrice = l.price && l.price > 0;
  const hasProfit = l.profit_best !== null && l.profit_best !== undefined;
  const saved = isSaved ? isSaved(l) : false;

  return (
    <>
      {/* Desktop */}
      <div className="hidden lg:grid grid-cols-[3fr_0.8fr_1fr_1fr_1fr_1fr_1fr_1.2fr_0.7fr_0.7fr_0.8fr_0.4fr] gap-2 items-center px-4 py-3 bg-card border border-border/50 rounded-sm listing-row cursor-pointer" onClick={onClick} data-testid={`listing-row-${l.id || index}`}>
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-16 h-12 bg-secondary rounded-sm overflow-hidden shrink-0">
            {l.photo ? <img src={l.photo} alt="" className="w-full h-full object-cover" loading="lazy" /> : <div className="flex items-center justify-center h-full"><Car className="h-4 w-4 text-muted-foreground/30" /></div>}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold truncate" style={{ fontFamily: 'Barlow Condensed' }}>{l.title}</p>
            <div className="flex items-center gap-1.5 flex-wrap">
              {l.brand && <span className={`text-[9px] px-1.5 py-0.5 rounded-sm ${l.brand.toUpperCase().includes('SALVAGE') ? 'bg-red-500/15 text-red-400' : 'bg-emerald-500/10 text-emerald-500'}`}>{l.brand.toUpperCase().includes('SALVAGE') ? t('dashboard.salvageBadge') : t('dashboard.clean')}</span>}
              {l.status === 'coming_soon' && <span className="text-[9px] px-1.5 py-0.5 rounded-sm bg-purple-500/15 text-purple-400">{t('dashboard.comingSoonBadge')}</span>}
              {hasPriceDrop(l) && <span className="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded-sm bg-teal-500/15 text-teal-400 font-semibold" title="Price dropped since first listed" data-testid="price-drop-badge"><TrendingDown className="h-2.5 w-2.5" />{priceDroplabel(l)}</span>}
            </div>
          </div>
        </div>
        <div><span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-sm ${sourceColor(l.source)}`}>{sourceLabel(l.source).split(' ')[0]}</span></div>
        <div className="text-right"><span className="text-sm font-bold font-data text-primary">{hasPrice ? fmt(l.price) : l.price_raw?.substring(0, 10) || t('detail.tbd')}</span></div>
        <div className="text-right text-xs text-muted-foreground font-data">{l.mileage ? `${fmtNum(l.mileage)} km` : '--'}</div>
        <div>
          <span className="text-xs text-muted-foreground">{l.damage || '--'}</span>
          {l.ai_damage_detected && <span className="text-[8px] ml-1 px-1 py-0.5 rounded-sm bg-blue-500/15 text-blue-400">AI</span>}
        </div>
        <div className="text-right"><span className="text-xs font-data">{l.market_value ? fmt(l.market_value) : t('detail.na')}</span></div>
        <div className="text-right"><span className="text-[11px] font-data text-muted-foreground">{fmt(l.repair_low)} – {fmt(l.repair_high)}</span></div>
        <div className="text-right">
          {hasProfit ? (
            <div>
              <span className={`text-xs font-bold font-data ${l.profit_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>{fmt(l.profit_best)}</span>
              <span className="text-[10px] text-muted-foreground block font-data">{t('dashboard.to')} {fmt(l.profit_worst)}</span>
            </div>
          ) : <span className="text-xs text-muted-foreground">{t('detail.na')}</span>}
        </div>
        <div className="text-right">
          {l.roi_best != null ? <span className={`text-xs font-bold font-data ${l.roi_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>{l.roi_best}%</span> : <span className="text-xs text-muted-foreground">--</span>}
        </div>
        <div className="text-center">
          {l.deal_score && l.deal_label ? (
            <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-sm border ${scoreBadge(l.deal_label)}`}>{l.deal_score}/10 {l.deal_label}</span>
          ) : <span className="text-xs text-muted-foreground">--</span>}
        </div>
        <div className="text-right">
          <span className="text-[11px] text-muted-foreground font-data" data-testid={`listing-date-${l.id || index}`}>{fmtDate(l.first_seen)}</span>
        </div>
        <div className="flex justify-center">
          <button
            onClick={(e) => { e.stopPropagation(); onToggleSave && onToggleSave(l); }}
            className={`p-1 rounded-sm transition-colors ${saved ? 'text-amber-400 hover:text-amber-300' : 'text-muted-foreground/30 hover:text-muted-foreground'}`}
            title={saved ? 'Remove from saved' : 'Save listing'}
            data-testid={`save-btn-${l.id || index}`}
          >
            <Bookmark className="h-3.5 w-3.5" fill={saved ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>
      {/* Mobile */}
      <div className="lg:hidden bg-card border border-border/50 rounded-sm p-3 cursor-pointer listing-row" onClick={onClick} data-testid={`listing-card-${l.id || index}`}>
        <div className="flex gap-3">
          <div className="w-20 h-16 bg-secondary rounded-sm overflow-hidden shrink-0">
            {l.photo ? <img src={l.photo} alt="" className="w-full h-full object-cover" loading="lazy" /> : <div className="flex items-center justify-center h-full"><Car className="h-5 w-5 text-muted-foreground/30" /></div>}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-bold truncate" style={{ fontFamily: 'Barlow Condensed' }}>{l.title}</p>
              <div className="flex items-center gap-1 shrink-0">
                {l.deal_label && <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm border ${scoreBadge(l.deal_label)}`}>{l.deal_score}/10</span>}
                <button
                  onClick={(e) => { e.stopPropagation(); onToggleSave && onToggleSave(l); }}
                  className={`p-0.5 rounded-sm transition-colors ${saved ? 'text-amber-400' : 'text-muted-foreground/30 hover:text-muted-foreground'}`}
                  title={saved ? 'Remove from saved' : 'Save listing'}
                  data-testid={`save-btn-mobile-${l.id || index}`}
                >
                  <Bookmark className="h-3.5 w-3.5" fill={saved ? 'currentColor' : 'none'} />
                </button>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-1 text-xs flex-wrap">
              <span className="font-bold font-data text-primary">{hasPrice ? fmt(l.price) : t('detail.tbd')}</span>
              {hasPriceDrop(l) && <span className="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded-sm bg-teal-500/15 text-teal-400 font-semibold" data-testid="price-drop-badge-mobile"><TrendingDown className="h-2.5 w-2.5" />{priceDroplabel(l)}</span>}
              <span className="text-muted-foreground">{l.mileage ? `${fmtNum(l.mileage)} km` : ''}</span>
              <span className={`text-[9px] px-1 py-0.5 rounded-sm ${sourceColor(l.source)}`}>{sourceLabel(l.source).split(' ')[0]}</span>
              <span className="text-[10px] text-muted-foreground font-data ml-auto">{fmtDate(l.first_seen)}</span>
            </div>
            {hasProfit && (
              <div className="flex items-center gap-3 mt-1 text-xs">
                <span className="text-muted-foreground">{t('dashboard.profitLabel')}</span>
                <span className={`font-data font-bold ${l.profit_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>{fmt(l.profit_best)} {t('dashboard.to')} {fmt(l.profit_worst)}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

export default function Dashboard() {
  const { t } = useLanguage();
  const [listings, setListings] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedListing, setSelectedListing] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  const { isSaved, toggle, count: savedCount } = useWatchlist();
  const [filters, setFilters] = useState({
    source: '', search: '', min_profit: '', max_price: '',
    min_score: '', damage_type: '', sort_by: 'deal_score', sort_order: 'desc',
    status: '', brand_type: '', price_drop_only: false,
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
      if (filters.status) params.status = filters.status;
      if (filters.brand_type) params.brand_type = filters.brand_type;
      if (filters.price_drop_only) params.price_drop_only = true;
      params.sort_by = filters.sort_by;
      params.sort_order = filters.sort_order;
      const [listRes, statsRes] = await Promise.all([listingsApi.getAll(params), statsApi.get()]);
      setListings(listRes.data);
      setStats(statsRes.data);
    } catch (e) {
      console.error('Failed to fetch', e);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => {
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const updateFilter = (key, value) => setFilters(prev => ({ ...prev, [key]: value }));

  const displayListings = activeTab === 'saved' ? listings.filter(l => isSaved(l)) : listings;

  return (
    <main className="max-w-[1600px] mx-auto px-4 md:px-8 py-6 space-y-5" data-testid="dashboard-page">
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3" data-testid="stats-bar">
          <StatCard label={t('dashboard.totalListings')} value={stats.total_listings} icon={Car} />
          <StatCard label={t('dashboard.buyDeals')} value={stats.buy_count} icon={Target} color="text-emerald-500" />
          <StatCard label={t('dashboard.watch')} value={stats.watch_count} icon={Eye} color="text-amber-500" />
          <StatCard label={t('dashboard.skip')} value={stats.skip_count} icon={X} color="text-red-500" />
          <StatCard label={t('dashboard.topProfit')} value={fmt(stats.top_profit || 0)} icon={TrendingUp} color="text-emerald-500" />
          <StatCard label="Price Drops" value={stats.price_drop_count || 0} icon={TrendingDown} color="text-teal-400" />
        </div>
      )}
      {stats?.last_scrape && (
        <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground bg-card/50 border border-border/30 rounded-sm px-4 py-2" data-testid="scan-info-bar">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
            {t('dashboard.lastScan')} {stats.last_scrape.finished_at ? new Date(stats.last_scrape.finished_at).toLocaleString() : t('dashboard.running')}
          </div>
          <Separator orientation="vertical" className="h-3 bg-border/50" />
          <div>{t('dashboard.sources')} Cathcart Rebuilders ({stats.source_counts?.cathcart_rebuilders || 0}), Used ({stats.source_counts?.cathcart_used || 0}), Pic N Save ({stats.source_counts?.picnsave || 0}), SalvageReseller ({stats.source_counts?.salvagereseller || 0})</div>
          {stats.best_deal && (
            <>
              <Separator orientation="vertical" className="h-3 bg-border/50" />
              <div className="text-emerald-400">{t('dashboard.bestDeal')} {stats.best_deal.title} ({stats.best_deal.score}/10 — {fmt(stats.best_deal.profit_best)})</div>
            </>
          )}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3" data-testid="filter-bar">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder={t('dashboard.searchPlaceholder')} value={filters.search} onChange={(e) => updateFilter('search', e.target.value)} className="pl-9 bg-card border-border/50 text-sm" data-testid="search-input" />
        </div>
        <Select value={filters.source || 'all'} onValueChange={(v) => updateFilter('source', v === 'all' ? '' : v)}>
          <SelectTrigger className="w-[180px] bg-card border-border/50 text-sm" data-testid="source-filter"><SelectValue placeholder={t('dashboard.allSources')} /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('dashboard.allSources')}</SelectItem>
            <SelectItem value="cathcart_rebuilders">{t('dashboard.cathcartRebuilders')}</SelectItem>
            <SelectItem value="cathcart_used">{t('dashboard.cathcartUsed')}</SelectItem>
            <SelectItem value="picnsave">{t('dashboard.picnsave')}</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.brand_type || 'all'} onValueChange={(v) => updateFilter('brand_type', v === 'all' ? '' : v)}>
          <SelectTrigger className="w-[150px] bg-card border-border/50 text-sm" data-testid="brand-type-filter">
            <Shield className="h-3 w-3 mr-1" /><SelectValue placeholder={t('dashboard.allTitles')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('dashboard.allTitles')}</SelectItem>
            <SelectItem value="salvagereseller">SalvageReseller</SelectItem>
            <SelectItem value="clean">{t('dashboard.clean')}</SelectItem>
            <SelectItem value="rebuilt">{t('dashboard.rebuilt')}</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.status || 'all'} onValueChange={(v) => updateFilter('status', v === 'all' ? '' : v)}>
          <SelectTrigger className="w-[160px] bg-card border-border/50 text-sm" data-testid="status-filter">
            <Radio className="h-3 w-3 mr-1" /><SelectValue placeholder={t('dashboard.allStatuses')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('dashboard.allStatuses')}</SelectItem>
            <SelectItem value="for_sale">{t('dashboard.forSale')}</SelectItem>
            <SelectItem value="coming_soon">{t('dashboard.comingSoon')}</SelectItem>
            <SelectItem value="sold">{t('dashboard.soldInactive')}</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.sort_by} onValueChange={(v) => updateFilter('sort_by', v)}>
          <SelectTrigger className="w-[150px] bg-card border-border/50 text-sm" data-testid="sort-filter">
            <ArrowUpDown className="h-3 w-3 mr-1" /><SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="deal_score">{t('dashboard.dealScore')}</SelectItem>
            <SelectItem value="profit">{t('dashboard.profit')}</SelectItem>
            <SelectItem value="price">{t('dashboard.price')}</SelectItem>
            <SelectItem value="mileage">{t('dashboard.mileage')}</SelectItem>
            <SelectItem value="date">{t('dashboard.dateFound')}</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)} className="border-border/50 text-xs" data-testid="toggle-filters-btn">
          <SlidersHorizontal className="h-3 w-3 mr-1" />{t('dashboard.moreFilters')}
        </Button>
        <Button variant="outline" size="sm" onClick={fetchData} className="border-border/50" data-testid="refresh-btn"><RefreshCw className="h-3 w-3" /></Button>
        <div className="flex items-center gap-1 ml-auto" data-testid="listing-tabs">
          <button
            onClick={() => setActiveTab('all')}
            className={`text-xs px-3 py-1.5 rounded-sm border transition-colors ${activeTab === 'all' ? 'bg-primary/10 text-primary border-primary/30' : 'bg-card border-border/50 text-muted-foreground hover:text-foreground'}`}
            data-testid="tab-all"
          >
            {t('dashboard.results') ? `${listings.length} ${t('dashboard.results')}` : `${listings.length} results`}
          </button>
          <button
            onClick={() => setActiveTab('saved')}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-sm border transition-colors ${activeTab === 'saved' ? 'bg-amber-500/15 text-amber-400 border-amber-500/30' : 'bg-card border-border/50 text-muted-foreground hover:text-foreground'}`}
            data-testid="tab-saved"
          >
            <Bookmark className="h-3 w-3" fill={activeTab === 'saved' ? 'currentColor' : 'none'} />
            Saved{savedCount > 0 ? ` (${savedCount})` : ''}
          </button>
        </div>
      </div>
      {showFilters && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 bg-card border border-border/50 rounded-sm animate-slide-up" data-testid="expanded-filters">
          <FilterField label={t('dashboard.minProfit')}><Input type="number" placeholder={t('dashboard.minProfitPlaceholder')} value={filters.min_profit} onChange={(e) => updateFilter('min_profit', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="min-profit-filter" /></FilterField>
          <FilterField label={t('dashboard.maxPrice')}><Input type="number" placeholder={t('dashboard.maxPricePlaceholder')} value={filters.max_price} onChange={(e) => updateFilter('max_price', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="max-price-filter" /></FilterField>
          <FilterField label={t('dashboard.minScore')}><Input type="number" placeholder={t('dashboard.minScorePlaceholder')} value={filters.min_score} onChange={(e) => updateFilter('min_score', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="min-score-filter" /></FilterField>
          <FilterField label={t('dashboard.damageType')}><Input placeholder={t('dashboard.damageTypePlaceholder')} value={filters.damage_type} onChange={(e) => updateFilter('damage_type', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="damage-filter" /></FilterField>
          <FilterField label="Price Drops">
            <button
              type="button"
              onClick={() => updateFilter('price_drop_only', !filters.price_drop_only)}
              className={`flex items-center gap-2 h-9 px-3 rounded-sm border text-sm transition-colors ${filters.price_drop_only ? 'bg-teal-500/15 border-teal-500/30 text-teal-400' : 'bg-background border-border/50 text-muted-foreground hover:text-foreground'}`}
              data-testid="price-drop-filter"
            >
              <TrendingDown className="h-3.5 w-3.5" />
              Price drops only
            </button>
          </FilterField>
        </div>
      )}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4" data-testid="loading-state">
          <RefreshCw className="h-10 w-10 text-primary animate-spin" />
          <p className="text-sm text-muted-foreground">{t('dashboard.loading')}</p>
        </div>
      )}
      {!loading && (activeTab === 'all' ? listings.length > 0 : displayListings.length > 0) && (
        <div className="space-y-2" data-testid="listings-container">
          <div className="hidden lg:grid grid-cols-[3fr_0.8fr_1fr_1fr_1fr_1fr_1fr_1.2fr_0.7fr_0.7fr_0.8fr_0.4fr] gap-2 px-4 py-2 text-[10px] text-muted-foreground uppercase tracking-wider">
            <div>{t('dashboard.vehicle')}</div><div>{t('dashboard.source')}</div><div className="text-right">{t('dashboard.price')}</div><div className="text-right">{t('dashboard.mileage')}</div><div>{t('detail.damage')}</div><div className="text-right">{t('dashboard.marketValue')}</div><div className="text-right">{t('dashboard.repairEst')}</div><div className="text-right">{t('dashboard.profitRange')}</div><div className="text-right">{t('dashboard.roi')}</div><div className="text-center">{t('dashboard.score')}</div><div className="text-right">{t('dashboard.found')}</div><div></div>
          </div>
          {displayListings.map((listing, i) => (
            <ListingRow key={listing.id || listing.url} listing={listing} index={i} onClick={() => setSelectedListing(listing)} isSaved={isSaved} onToggleSave={toggle} />
          ))}
        </div>
      )}
      {!loading && activeTab === 'all' && listings.length === 0 && (
        <div className="text-center py-20" data-testid="empty-state">
          <Car className="h-16 w-16 mx-auto mb-4 text-muted-foreground/20" />
          <p className="text-lg text-muted-foreground mb-2">{t('dashboard.noListings')}</p>
          <p className="text-sm text-muted-foreground">{t('dashboard.noListingsHint')}</p>
        </div>
      )}
      {!loading && activeTab === 'saved' && displayListings.length === 0 && (
        <div className="text-center py-20" data-testid="saved-empty-state">
          <Bookmark className="h-16 w-16 mx-auto mb-4 text-muted-foreground/20" />
          <p className="text-lg text-muted-foreground mb-2">No saved listings yet</p>
          <p className="text-sm text-muted-foreground">Click the <Bookmark className="h-3.5 w-3.5 inline mx-0.5" /> bookmark on any listing to save it here.</p>
        </div>
      )}
      {selectedListing && <ListingDetail listing={selectedListing} onClose={() => setSelectedListing(null)} />}
    </main>
  );
}
