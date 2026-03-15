import { useState, useEffect, useCallback, useRef } from 'react';
import '@/App.css';
import { listingsApi, statsApi, scrapeApi, settingsApi } from '@/lib/api';
import { fmt, fmtNum, sourceLabel, sourceColor, scoreBadge, fmtDate } from '@/lib/utils-app';
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
  SlidersHorizontal, Clock, Target, X, Info, Settings,
  LayoutDashboard, Radio, Timer, CheckCircle2, ChevronRight,
  Shield, Calculator, BarChart3, Globe, Eye, Crosshair,
} from 'lucide-react';

function App() {
  const [page, setPage] = useState('dashboard');

  return (
    <div className="App min-h-screen grid-bg">
      <NavBar page={page} setPage={setPage} />
      {page === 'dashboard' && <Dashboard />}
      {page === 'about' && <AboutPage />}
      {page === 'settings' && <SettingsPage />}
      <Toaster position="bottom-right" theme="dark" />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   NAVIGATION BAR + LIVE STATUS
   ═══════════════════════════════════════════════════════ */

function NavBar({ page, setPage }) {
  const [scrapeStatus, setScrapeStatus] = useState(null);
  const [countdown, setCountdown] = useState(null);
  const [scraping, setScraping] = useState(false);

  // Poll scrape status every 10s
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await scrapeApi.status();
        setScrapeStatus(res.data);
        setScraping(res.data?.is_scanning || false);
      } catch {}
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  // Countdown timer
  useEffect(() => {
    if (!scrapeStatus?.finished_at || !scrapeStatus?.scan_interval) return;
    const update = () => {
      const lastScan = new Date(scrapeStatus.finished_at).getTime();
      const nextScan = lastScan + scrapeStatus.scan_interval * 1000;
      const remaining = Math.max(0, Math.floor((nextScan - Date.now()) / 1000));
      setCountdown(remaining);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [scrapeStatus]);

  const handleScrape = async () => {
    setScraping(true);
    try {
      await scrapeApi.trigger();
      toast.info('Scan started...');
    } catch {
      toast.error('Failed');
      setScraping(false);
    }
  };

  const formatCountdown = (s) => {
    if (s === null || s === undefined) return '--:--';
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const intervalMin = scrapeStatus?.scan_interval ? Math.round(scrapeStatus.scan_interval / 60) : 10;

  return (
    <header className="sticky top-0 z-40 bg-[#09090b]/90 backdrop-blur-xl border-b border-border/30" data-testid="navbar">
      <div className="max-w-[1600px] mx-auto px-4 md:px-8">
        <div className="h-14 flex items-center justify-between">
          {/* Left: Logo + Nav */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => setPage('dashboard')}>
              <div className="flex items-center justify-center w-8 h-8 bg-primary/20 rounded-sm">
                <Zap className="h-5 w-5 text-primary" />
              </div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-black tracking-tighter uppercase leading-none" style={{ fontFamily: 'Barlow Condensed' }} data-testid="app-title">
                  AutoFlip
                </h1>
                <span className="text-[9px] text-muted-foreground tracking-[0.2em] uppercase">Intelligence</span>
              </div>
            </div>

            <nav className="flex items-center gap-1" data-testid="nav-tabs">
              {[
                { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
                { id: 'about', label: 'About', icon: Info },
                { id: 'settings', label: 'Settings', icon: Settings },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setPage(id)}
                  data-testid={`nav-${id}`}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-sm transition-all ${
                    page === id
                      ? 'bg-primary/15 text-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span className="hidden md:inline">{label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Right: Live Status + Scan Button */}
          <div className="flex items-center gap-3">
            {/* Live indicator */}
            <div className="hidden md:flex items-center gap-4 text-[11px] mr-2">
              <div className="flex items-center gap-1.5">
                <span className={`relative flex h-2 w-2 ${scraping ? '' : ''}`}>
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${scraping ? 'bg-amber-400' : 'bg-emerald-400'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${scraping ? 'bg-amber-400' : 'bg-emerald-400'}`}></span>
                </span>
                <span className={scraping ? 'text-amber-400' : 'text-emerald-400'}>
                  {scraping ? 'Scanning...' : 'Live'}
                </span>
              </div>

              {!scraping && countdown !== null && countdown > 0 && (
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Timer className="h-3 w-3" />
                  <span className="font-data">{formatCountdown(countdown)}</span>
                </div>
              )}

              <div className="text-muted-foreground">
                Every {intervalMin}m
              </div>
            </div>

            <Button
              size="sm"
              variant={scraping ? "outline" : "default"}
              onClick={handleScrape}
              disabled={scraping}
              className="text-xs"
              data-testid="scrape-btn"
            >
              <RefreshCw className={`h-3 w-3 mr-1 ${scraping ? 'animate-spin' : ''}`} />
              {scraping ? 'Scanning' : 'Scan Now'}
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}

/* ═══════════════════════════════════════════════════════
   DASHBOARD PAGE
   ═══════════════════════════════════════════════════════ */

function Dashboard() {
  const [listings, setListings] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedListing, setSelectedListing] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    source: '', search: '', min_profit: '', max_price: '',
    min_score: '', damage_type: '', sort_by: 'deal_score', sort_order: 'desc',
    status: '', brand_type: '',
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
      params.sort_by = filters.sort_by;
      params.sort_order = filters.sort_order;
      const [listRes, statsRes] = await Promise.all([
        listingsApi.getAll(params), statsApi.get(),
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

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const updateFilter = (key, value) => setFilters(prev => ({ ...prev, [key]: value }));

  return (
    <main className="max-w-[1600px] mx-auto px-4 md:px-8 py-6 space-y-5" data-testid="dashboard-page">
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="stats-bar">
          <StatCard label="Total Listings" value={stats.total_listings} icon={Car} />
          <StatCard label="BUY Deals" value={stats.buy_count} icon={Target} color="text-emerald-500" />
          <StatCard label="WATCH" value={stats.watch_count} icon={Eye} color="text-amber-500" />
          <StatCard label="SKIP" value={stats.skip_count} icon={X} color="text-red-500" />
          <StatCard label="Top Profit" value={fmt(stats.top_profit || 0)} icon={TrendingUp} color="text-emerald-500" />
        </div>
      )}

      {/* Scan Info Bar */}
      {stats?.last_scrape && (
        <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground bg-card/50 border border-border/30 rounded-sm px-4 py-2" data-testid="scan-info-bar">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
            Last scan: {stats.last_scrape.finished_at ? new Date(stats.last_scrape.finished_at).toLocaleString() : 'Running...'}
          </div>
          <Separator orientation="vertical" className="h-3 bg-border/50" />
          <div>Sources: Cathcart Rebuilders ({stats.source_counts?.cathcart_rebuilders || 0}), Used ({stats.source_counts?.cathcart_used || 0}), Pic N Save ({stats.source_counts?.picnsave || 0})</div>
          {stats.best_deal && (
            <>
              <Separator orientation="vertical" className="h-3 bg-border/50" />
              <div className="text-emerald-400">
                Best deal: {stats.best_deal.title} ({stats.best_deal.score}/10 — {fmt(stats.best_deal.profit_best)})
              </div>
            </>
          )}
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3" data-testid="filter-bar">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search year, make, model..." value={filters.search} onChange={(e) => updateFilter('search', e.target.value)} className="pl-9 bg-card border-border/50 text-sm" data-testid="search-input" />
        </div>
        <Select value={filters.source || 'all'} onValueChange={(v) => updateFilter('source', v === 'all' ? '' : v)}>
          <SelectTrigger className="w-[180px] bg-card border-border/50 text-sm" data-testid="source-filter"><SelectValue placeholder="All Sources" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Sources</SelectItem>
            <SelectItem value="cathcart_rebuilders">Cathcart Rebuilders</SelectItem>
            <SelectItem value="cathcart_used">Cathcart Used</SelectItem>
            <SelectItem value="picnsave">Pic N Save</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.brand_type || 'all'} onValueChange={(v) => updateFilter('brand_type', v === 'all' ? '' : v)}>
          <SelectTrigger className="w-[150px] bg-card border-border/50 text-sm" data-testid="brand-type-filter">
            <Shield className="h-3 w-3 mr-1" /><SelectValue placeholder="All Titles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Titles</SelectItem>
            <SelectItem value="salvage">Salvage</SelectItem>
            <SelectItem value="clean">Clean</SelectItem>
            <SelectItem value="rebuilt">Rebuilt</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.status || 'all'} onValueChange={(v) => updateFilter('status', v === 'all' ? '' : v)}>
          <SelectTrigger className="w-[160px] bg-card border-border/50 text-sm" data-testid="status-filter">
            <Radio className="h-3 w-3 mr-1" /><SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="for_sale">For Sale</SelectItem>
            <SelectItem value="coming_soon">Coming Soon</SelectItem>
            <SelectItem value="sold">Sold / Inactive</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.sort_by} onValueChange={(v) => updateFilter('sort_by', v)}>
          <SelectTrigger className="w-[150px] bg-card border-border/50 text-sm" data-testid="sort-filter">
            <ArrowUpDown className="h-3 w-3 mr-1" /><SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="deal_score">Deal Score</SelectItem>
            <SelectItem value="profit">Profit</SelectItem>
            <SelectItem value="price">Price</SelectItem>
            <SelectItem value="mileage">Mileage</SelectItem>
            <SelectItem value="date">Date Found</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)} className="border-border/50 text-xs" data-testid="toggle-filters-btn">
          <SlidersHorizontal className="h-3 w-3 mr-1" />More Filters
        </Button>
        <Button variant="outline" size="sm" onClick={fetchData} className="border-border/50" data-testid="refresh-btn"><RefreshCw className="h-3 w-3" /></Button>
        <span className="text-xs text-muted-foreground ml-auto">{listings.length} results</span>
      </div>

      {showFilters && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 bg-card border border-border/50 rounded-sm animate-slide-up" data-testid="expanded-filters">
          <FilterField label="Min Profit ($)"><Input type="number" placeholder="e.g. 2000" value={filters.min_profit} onChange={(e) => updateFilter('min_profit', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="min-profit-filter" /></FilterField>
          <FilterField label="Max Price ($)"><Input type="number" placeholder="e.g. 15000" value={filters.max_price} onChange={(e) => updateFilter('max_price', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="max-price-filter" /></FilterField>
          <FilterField label="Min Score (1-10)"><Input type="number" placeholder="e.g. 5" value={filters.min_score} onChange={(e) => updateFilter('min_score', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="min-score-filter" /></FilterField>
          <FilterField label="Damage Type"><Input placeholder="e.g. FRONT" value={filters.damage_type} onChange={(e) => updateFilter('damage_type', e.target.value)} className="bg-background border-border/50 text-sm" data-testid="damage-filter" /></FilterField>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4" data-testid="loading-state">
          <RefreshCw className="h-10 w-10 text-primary animate-spin" />
          <p className="text-sm text-muted-foreground">Loading listings...</p>
        </div>
      )}

      {/* Listings */}
      {!loading && listings.length > 0 && (
        <div className="space-y-2" data-testid="listings-container">
          <div className="hidden lg:grid grid-cols-[3fr_0.8fr_1fr_1fr_1fr_1fr_1fr_1.2fr_0.7fr_0.7fr_0.8fr] gap-2 px-4 py-2 text-[10px] text-muted-foreground uppercase tracking-wider">
            <div>Vehicle</div><div>Source</div><div className="text-right">Price</div><div className="text-right">Mileage</div><div>Damage</div><div className="text-right">Market Value</div><div className="text-right">Repair Est.</div><div className="text-right">Profit Range</div><div className="text-right">ROI</div><div className="text-center">Score</div><div className="text-right">Found</div>
          </div>
          {listings.map((listing, i) => (
            <ListingRow key={listing.id || listing.url} listing={listing} index={i} onClick={() => setSelectedListing(listing)} />
          ))}
        </div>
      )}

      {!loading && listings.length === 0 && (
        <div className="text-center py-20" data-testid="empty-state">
          <Car className="h-16 w-16 mx-auto mb-4 text-muted-foreground/20" />
          <p className="text-lg text-muted-foreground mb-2">No listings found</p>
          <p className="text-sm text-muted-foreground">Try adjusting your filters or wait for the next scan</p>
        </div>
      )}

      {selectedListing && <DetailDialog listing={selectedListing} onClose={() => setSelectedListing(null)} />}
    </main>
  );
}

/* ═══════════════════════════════════════════════════════
   ABOUT PAGE
   ═══════════════════════════════════════════════════════ */

function AboutPage() {
  return (
    <main className="max-w-4xl mx-auto px-4 md:px-8 py-10 space-y-12 animate-fade-in" data-testid="about-page">
      {/* Hero */}
      <section className="text-center space-y-4">
        <div className="flex items-center justify-center w-16 h-16 mx-auto bg-primary/20 rounded-sm mb-6">
          <Zap className="h-10 w-10 text-primary" />
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase" style={{ fontFamily: 'Barlow Condensed' }}>
          AutoFlip Intelligence
        </h1>
        <p className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          Automated car investment analysis for Ontario, Canada. We scan dealer websites, calculate repair costs, estimate market values, and tell you exactly how much profit you can make on every listing.
        </p>
      </section>

      <Separator className="bg-border/30" />

      {/* What it does */}
      <section className="space-y-6">
        <SectionTitle icon={Globe} title="What This App Does" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FeatureCard icon={Globe} title="Scans Dealer Websites" desc="Automatically monitors Cathcart Auto (rebuilders + used cars) and Pic N Save (rebuildable cars) every few minutes for new vehicle listings." />
          <FeatureCard icon={Calculator} title="Calculates Profit" desc="For every car found, we estimate the market value, repair costs, Ontario fees (HST, OMVIC, MTO, safety), and show you best/worst case profit." />
          <FeatureCard icon={Target} title="Scores Every Deal" desc="Each listing gets a deal score from 1-10 with a BUY, WATCH, or SKIP recommendation so you can act fast on the best deals." />
        </div>
      </section>

      {/* Websites monitored */}
      <section className="space-y-6">
        <SectionTitle icon={Eye} title="Websites We Monitor" />
        <div className="space-y-3">
          <WebsiteCard
            name="Cathcart Auto — Rebuilders"
            url="https://cathcartauto.com/vehicles/rebuilders/"
            desc="Salvage and rebuildable vehicles. Listings include damage type, brand status (Clean/Salvage), mileage, colour, and multiple photos. These are the primary profit opportunities."
            badge="cathcart_rebuilders"
          />
          <WebsiteCard
            name="Cathcart Auto — Used Cars"
            url="https://cathcartauto.com/vehicles/used-cars/"
            desc="Clean title used cars. Lower margins but less risk. Good for quick flips with minor reconditioning. Same listing format as rebuilders."
            badge="cathcart_used"
          />
          <WebsiteCard
            name="Pic N Save — Rebuildable Cars"
            url="https://picnsave.ca/rebuildable-cars/"
            desc="Located in Stoney Creek, ON. WooCommerce-based listings with pricing, mileage, and brand info. Damage details are on the detail page. Currently 4+ pages of inventory."
            badge="picnsave"
          />
        </div>
      </section>

      {/* How profit is calculated */}
      <section className="space-y-6">
        <SectionTitle icon={Calculator} title="How We Calculate Profit" />
        <div className="bg-card border border-border/50 rounded-sm p-6 space-y-4">
          <StepItem number="1" title="Market Value" desc="We estimate the Ontario retail market value based on the vehicle's year, make, model, trim, mileage, and body type. Salvage title vehicles get a 25% discount applied (Ontario salvage title resale penalty)." />
          <StepItem number="2" title="Repair Cost Estimate" desc="Based on the listed damage type, we estimate repair costs using Ontario body shop rates (~$110/hr). Each damage type maps to a low-high range. Plus $100 for mandatory Ontario Safety Inspection." />
          <StepItem number="3" title="Ontario Fees" desc="Every purchase includes: HST (13% of purchase price), OMVIC fee ($22), MTO transfer ($32), and Safety Inspection ($100). Total = Price x 0.13 + $154." />
          <StepItem number="4" title="Profit Calculation" desc="Profit = Market Value - Purchase Price - Repair Cost - Ontario Fees. We show best case (low repair) and worst case (high repair) scenarios." />
        </div>
      </section>

      {/* Repair cost table */}
      <section className="space-y-6">
        <SectionTitle icon={Wrench} title="Repair Cost Estimates" />
        <div className="bg-card border border-border/50 rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/30 text-[10px] text-muted-foreground uppercase tracking-wider">
                <th className="text-left px-4 py-2.5">Damage Type</th>
                <th className="text-right px-4 py-2.5">Low Estimate</th>
                <th className="text-right px-4 py-2.5">High Estimate</th>
              </tr>
            </thead>
            <tbody className="font-data text-xs">
              {[
                ['Left/Right Rear', '$1,900', '$3,600'],
                ['Front / Left/Right Front', '$2,600', '$5,600'],
                ['Left/Right Doors', '$1,600', '$3,100'],
                ['Rollover', '$5,100', '$14,100'],
                ['Flood or Fire', '$3,600', '$10,100'],
                ['Unknown / Hit', '$2,100', '$5,100'],
                ['Clean (no damage)', '$600', '$1,600'],
              ].map(([type, low, high], i) => (
                <tr key={i} className="border-b border-border/20 hover:bg-secondary/20">
                  <td className="px-4 py-2">{type}</td>
                  <td className="px-4 py-2 text-right text-emerald-500">{low}</td>
                  <td className="px-4 py-2 text-right text-red-400">{high}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted-foreground">
          All estimates include $100 for Ontario Safety Inspection. Based on average Ontario body shop rate of $110/hr.
        </p>
      </section>

      {/* Deal scoring */}
      <section className="space-y-6">
        <SectionTitle icon={Crosshair} title="Deal Scoring System" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ScoreExplainer score="8-10" label="BUY" color="bg-emerald-500/10 border-emerald-500/30 text-emerald-400" desc="Best case profit over $2,500. Strong flip opportunity. Act fast — these go quickly." />
          <ScoreExplainer score="5-7" label="WATCH" color="bg-amber-500/10 border-amber-500/30 text-amber-400" desc="Moderate profit potential ($1,000-$2,500). Worth monitoring for a price drop." />
          <ScoreExplainer score="1-4" label="SKIP" color="bg-red-500/10 border-red-500/30 text-red-400" desc="Low or negative profit potential. May lose money after repairs and fees." />
        </div>
      </section>

      {/* How to use */}
      <section className="space-y-6">
        <SectionTitle icon={BarChart3} title="How to Use This App" />
        <div className="bg-card border border-border/50 rounded-sm p-6 space-y-3">
          <HowToStep num="1" text="The app automatically scans all dealer websites on a regular interval. You can see the live status indicator in the top navigation bar." />
          <HowToStep num="2" text="Browse the dashboard to see all available listings sorted by deal score. The best money-making opportunities appear first." />
          <HowToStep num="3" text="Use the filters to narrow down by source, price range, minimum profit, damage type, or deal score." />
          <HowToStep num="4" text="Click any listing to see the full profit breakdown: market value, repair cost range, Ontario fees, and best/worst case profit." />
          <HowToStep num="5" text="Visit the Settings page to adjust the scan frequency (how often the app checks for new listings)." />
          <HowToStep num="6" text="Click 'Scan Now' anytime to force an immediate scan of all dealer websites." />
        </div>
      </section>

      {/* Important notes */}
      <section className="space-y-6">
        <SectionTitle icon={AlertTriangle} title="Important Notes" />
        <div className="bg-card border border-amber-500/20 rounded-sm p-6 space-y-2 text-sm text-muted-foreground">
          <p>Market values are <strong className="text-foreground">estimates</strong> based on Ontario market patterns for the vehicle's year, make, model, and mileage. Actual market prices may vary.</p>
          <p>Repair cost ranges are estimates using average Ontario body shop rates. Actual costs depend on the specific damage, parts availability, and shop pricing.</p>
          <p>Vehicles with <strong className="text-foreground">Salvage titles</strong> have their market value reduced by 25% to account for the Ontario salvage title resale penalty.</p>
          <p>Listings marked "COMING SOON" or with "####" pricing will show as price TBD and won't have profit calculations until a real price is listed.</p>
          <p>This tool is for <strong className="text-foreground">research and analysis only</strong>. Always inspect a vehicle in person before purchasing.</p>
        </div>
      </section>
    </main>
  );
}

/* ═══════════════════════════════════════════════════════
   SETTINGS PAGE
   ═══════════════════════════════════════════════════════ */

function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [scanHistory, setScanHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedInterval, setSelectedInterval] = useState('600');

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [settingsRes, historyRes] = await Promise.all([settingsApi.get(), scrapeApi.history()]);
        setSettings(settingsRes.data);
        setScanHistory(historyRes.data);
        setSelectedInterval(String(settingsRes.data?.scan_interval || 600));
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await settingsApi.update({ scan_interval: parseInt(selectedInterval) });
      setSettings(res.data);
      toast.success('Settings saved! New interval will apply on next scan cycle.');
    } catch {
      toast.error('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-20"><RefreshCw className="h-8 w-8 text-primary animate-spin" /></div>;
  }

  return (
    <main className="max-w-3xl mx-auto px-4 md:px-8 py-8 space-y-8 animate-fade-in" data-testid="settings-page">
      <h2 className="text-2xl font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>Settings</h2>

      {/* Scan Interval */}
      <section className="bg-card border border-border/50 rounded-sm p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Timer className="h-4 w-4 text-primary" />
          <h3 className="text-base font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>Scan Frequency</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          How often AutoFlip scans the dealer websites for new listings and price changes.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2" data-testid="interval-options">
          {[
            { value: '300', label: '5 min' },
            { value: '600', label: '10 min' },
            { value: '900', label: '15 min' },
            { value: '1800', label: '30 min' },
          ].map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setSelectedInterval(value)}
              data-testid={`interval-${value}`}
              className={`px-4 py-3 rounded-sm border text-sm font-bold transition-all ${
                selectedInterval === value
                  ? 'bg-primary/15 border-primary text-primary'
                  : 'bg-background border-border/50 text-muted-foreground hover:border-border'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <Button onClick={handleSave} disabled={saving} className="mt-2" data-testid="save-settings-btn">
          {saving ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle2 className="h-4 w-4 mr-2" />}
          Save Settings
        </Button>
      </section>

      {/* Scan History */}
      <section className="bg-card border border-border/50 rounded-sm p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-primary" />
          <h3 className="text-base font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>Scan History</h3>
        </div>
        {scanHistory.length === 0 ? (
          <p className="text-sm text-muted-foreground">No scans recorded yet.</p>
        ) : (
          <div className="space-y-1.5 max-h-64 overflow-y-auto" data-testid="scan-history-list">
            {scanHistory.map((scan, i) => (
              <div key={scan.id || i} className="flex items-center justify-between px-3 py-2 bg-background/50 rounded-sm text-xs">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                  <span className="font-data">{new Date(scan.timestamp).toLocaleString()}</span>
                </div>
                <span className="text-muted-foreground">
                  Every {Math.round((scan.interval || 600) / 60)}m
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* About the data */}
      <section className="bg-card border border-border/50 rounded-sm p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-primary" />
          <h3 className="text-base font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>Data Sources</h3>
        </div>
        <div className="space-y-2 text-sm text-muted-foreground">
          <p><strong className="text-foreground">Cathcart Auto — Rebuilders:</strong> cathcartauto.com/vehicles/rebuilders/</p>
          <p><strong className="text-foreground">Cathcart Auto — Used Cars:</strong> cathcartauto.com/vehicles/used-cars/</p>
          <p><strong className="text-foreground">Pic N Save — Rebuildable Cars:</strong> picnsave.ca/rebuildable-cars/</p>
          <p className="pt-2">Market values are estimated using vehicle age, make, model, body type, and Ontario market patterns. Actual AutoTrader/Kijiji scraping is planned for a future update.</p>
        </div>
      </section>
    </main>
  );
}

/* ═══════════════════════════════════════════════════════
   SHARED COMPONENTS
   ═══════════════════════════════════════════════════════ */

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

function ListingRow({ listing, index, onClick }) {
  const l = listing;
  const hasPrice = l.price && l.price > 0;
  const hasProfit = l.profit_best !== null && l.profit_best !== undefined;

  return (
    <>
      {/* Desktop */}
      <div className="hidden lg:grid grid-cols-[3fr_0.8fr_1fr_1fr_1fr_1fr_1fr_1.2fr_0.7fr_0.7fr_0.8fr] gap-2 items-center px-4 py-3 bg-card border border-border/50 rounded-sm listing-row cursor-pointer" onClick={onClick} data-testid={`listing-row-${l.id || index}`}>
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-16 h-12 bg-secondary rounded-sm overflow-hidden shrink-0">
            {l.photo ? <img src={l.photo} alt="" className="w-full h-full object-cover" loading="lazy" /> : <div className="flex items-center justify-center h-full"><Car className="h-4 w-4 text-muted-foreground/30" /></div>}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold truncate" style={{ fontFamily: 'Barlow Condensed' }}>{l.title}</p>
            <div className="flex items-center gap-1.5">
              {l.brand && <span className={`text-[9px] px-1.5 py-0.5 rounded-sm ${l.brand.toUpperCase().includes('SALVAGE') ? 'bg-red-500/15 text-red-400' : 'bg-emerald-500/10 text-emerald-500'}`}>{l.brand.toUpperCase().includes('SALVAGE') ? 'SALVAGE' : 'CLEAN'}</span>}
              {l.status === 'coming_soon' && <span className="text-[9px] px-1.5 py-0.5 rounded-sm bg-purple-500/15 text-purple-400">COMING SOON</span>}
            </div>
          </div>
        </div>
        <div><span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-sm ${sourceColor(l.source)}`}>{sourceLabel(l.source).split(' ')[0]}</span></div>
        <div className="text-right"><span className="text-sm font-bold font-data text-primary">{hasPrice ? fmt(l.price) : l.price_raw?.substring(0, 10) || 'TBD'}</span></div>
        <div className="text-right text-xs text-muted-foreground font-data">{l.mileage ? `${fmtNum(l.mileage)} km` : '--'}</div>
        <div>
          <span className="text-xs text-muted-foreground">{l.damage || '--'}</span>
          {l.ai_damage_detected && <span className="text-[8px] ml-1 px-1 py-0.5 rounded-sm bg-blue-500/15 text-blue-400">AI</span>}
        </div>
        <div className="text-right"><span className="text-xs font-data">{l.market_value ? fmt(l.market_value) : 'N/A'}</span></div>
        <div className="text-right"><span className="text-[11px] font-data text-muted-foreground">{fmt(l.repair_low)} – {fmt(l.repair_high)}</span></div>
        <div className="text-right">
          {hasProfit ? (
            <div>
              <span className={`text-xs font-bold font-data ${l.profit_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>{fmt(l.profit_best)}</span>
              <span className="text-[10px] text-muted-foreground block font-data">to {fmt(l.profit_worst)}</span>
            </div>
          ) : <span className="text-xs text-muted-foreground">N/A</span>}
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
              {l.deal_label && <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm border shrink-0 ${scoreBadge(l.deal_label)}`}>{l.deal_score}/10</span>}
            </div>
            <div className="flex items-center gap-2 mt-1 text-xs">
              <span className="font-bold font-data text-primary">{hasPrice ? fmt(l.price) : 'TBD'}</span>
              <span className="text-muted-foreground">{l.mileage ? `${fmtNum(l.mileage)} km` : ''}</span>
              <span className={`text-[9px] px-1 py-0.5 rounded-sm ${sourceColor(l.source)}`}>{sourceLabel(l.source).split(' ')[0]}</span>
              <span className="text-[10px] text-muted-foreground font-data ml-auto">{fmtDate(l.first_seen)}</span>
            </div>
            {hasProfit && (
              <div className="flex items-center gap-3 mt-1 text-xs">
                <span className="text-muted-foreground">Profit:</span>
                <span className={`font-data font-bold ${l.profit_best > 0 ? 'text-emerald-500' : 'text-red-500'}`}>{fmt(l.profit_best)} to {fmt(l.profit_worst)}</span>
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
              <DialogTitle className="text-2xl font-bold tracking-tight uppercase pr-8" style={{ fontFamily: 'Barlow Condensed' }}>{l.title}</DialogTitle>
            </DialogHeader>
            {l.photos?.length > 0 && (
              <div className="flex gap-2 overflow-x-auto pb-2">
                {l.photos.map((photo, i) => <img key={i} src={photo} alt={`Photo ${i + 1}`} className="h-40 rounded-sm object-cover shrink-0" loading="lazy" />)}
              </div>
            )}
            {!l.photos?.length && l.photo && <img src={l.photo} alt="" className="w-full h-48 rounded-sm object-cover" />}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <InfoCell icon={DollarSign} label="Price" value={hasPrice ? fmt(l.price) : l.price_raw || 'TBD'} />
              <InfoCell icon={Gauge} label="Mileage" value={l.mileage ? `${fmtNum(l.mileage)} km` : 'Unknown'} />
              <InfoCell icon={Wrench} label="Damage" value={l.damage || 'None listed'} />
              <InfoCell icon={Car} label="Brand" value={l.brand || 'Unknown'} />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <InfoCell label="Source" value={sourceLabel(l.source)} />
              <InfoCell label="Colour" value={l.colour || 'Unknown'} />
              <InfoCell label="Status" value={l.status?.replace('_', ' ').toUpperCase() || 'Unknown'} />
              <InfoCell icon={Clock} label="Date Found" value={l.first_seen ? new Date(l.first_seen).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' }) : 'Unknown'} />
            </div>
            {l.description && <div className="bg-background/50 border border-border/30 rounded-sm p-3"><p className="text-xs text-muted-foreground">{l.description}</p></div>}
            <Separator className="bg-border/30" />
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>Profit Analysis</h3>
                {l.deal_label && <span className={`text-base font-bold px-3 py-1 rounded-sm border ${scoreBadge(l.deal_label)}`}>{l.deal_score}/10 — {l.deal_label}</span>}
              </div>
              {l.ai_damage_detected && (
                <div className="flex items-center gap-2 p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-sm">
                  <Eye className="h-4 w-4 text-blue-400 shrink-0" />
                  <span className="text-xs text-blue-300">AI Vision detected damage: <strong>{l.damage}</strong> {l.ai_damage_details && `— ${l.ai_damage_details}`}</span>
                </div>
              )}
              <div className="bg-background/50 border border-border/30 rounded-sm p-4 space-y-2 font-data text-sm">
                <Row label="Market Value" value={l.market_value ? fmt(l.market_value) : 'N/A'} note={l.mv_breakdown?.title_status === 'salvage_title' ? 'Salvage: 55% of clean value' : l.mv_breakdown?.title_status === 'rebuilt_title' ? 'Rebuilt: 75% of clean' : ''} />
                <Row label="Purchase Price" value={hasPrice ? fmt(l.price) : 'TBD'} />
                <Row label="Repair Estimate (Low)" value={fmt(l.repair_low)} dim />
                <Row label="Repair Estimate (High)" value={fmt(l.repair_high)} dim />
                {l.repair_breakdown?.salvage_to_rebuilt_cost > 0 && (
                  <Row label="  Incl. Salvage→Rebuilt Process" value={fmt(l.repair_breakdown.salvage_to_rebuilt_cost)} dim note="Structural insp + VIN + Appraisal" />
                )}
                <Row label="Ontario Fees" value={l.fees ? fmt(l.fees) : 'N/A'} dim note="HST 13% + OMVIC $22 + MTO $32 + Safety $100" />
                <Separator className="bg-border/30" />
                <Row label="Best Case Profit" value={l.profit_best !== null ? fmt(l.profit_best) : 'N/A'} highlight={l.profit_best > 0} />
                <Row label="Worst Case Profit" value={l.profit_worst !== null ? fmt(l.profit_worst) : 'N/A'} highlight={l.profit_worst > 0} />
                <Row label="ROI (Best)" value={l.roi_best !== null ? `${l.roi_best}%` : 'N/A'} />
                <Row label="ROI (Worst)" value={l.roi_worst !== null ? `${l.roi_worst}%` : 'N/A'} />
              </div>
              {/* Market Value Breakdown */}
              {l.mv_breakdown && (
                <details className="group">
                  <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5">
                    <ChevronRight className="h-3 w-3 group-open:rotate-90 transition-transform" />
                    View calculation breakdown
                  </summary>
                  <div className="mt-2 bg-background/50 border border-border/30 rounded-sm p-3 space-y-1.5 font-data text-[11px]">
                    {l.mv_breakdown?.autotrader_median && (
                      <>
                        <Row label="AutoTrader Comps" value={`${l.mv_breakdown.autotrader_count} listings found`} dim note={l.mv_breakdown.blend_method?.replace(/_/g, ' ')} />
                        <Row label="  AT Median (clean)" value={fmt(l.mv_breakdown.autotrader_median)} dim />
                        <Row label="  AT Range" value={`${fmt(l.mv_breakdown.autotrader_low)} – ${fmt(l.mv_breakdown.autotrader_high)}`} dim />
                        <Row label="  AT Adjusted (title)" value={fmt(l.mv_breakdown.autotrader_adjusted)} dim />
                        <Separator className="bg-border/20 my-1" />
                      </>
                    )}
                    <Row label="Formula: Est. MSRP" value={fmt(l.mv_breakdown.msrp)} dim note={l.mv_breakdown.msrp_source === 'model_match' ? 'Model matched' : 'Estimated'} />
                    <Row label="Formula: Depreciation" value={`×${l.mv_breakdown.depreciation}`} dim note={`${l.mv_breakdown.age}yr old`} />
                    <Row label="Formula: Brand" value={`×${l.mv_breakdown.brand_mult}`} dim note={l.mv_breakdown.brand} />
                    <Row label="Formula: Body Type" value={`×${l.mv_breakdown.body_mult}`} dim />
                    <Row label="Formula: Trim" value={`×${l.mv_breakdown.trim_mult}`} dim />
                    <Row label="Formula: Color" value={`×${l.mv_breakdown.color_mult}`} dim />
                    <Row label="Formula: Mileage" value={`×${l.mv_breakdown.mileage_mult}`} dim />
                    <Row label="Formula: Title Status" value={`×${l.mv_breakdown.title_mult}`} dim note={l.mv_breakdown.title_status?.replace(/_/g, ' ')} />
                    {l.mv_breakdown?.formula_value && (
                      <Row label="Formula Result" value={fmt(l.mv_breakdown.formula_value)} dim />
                    )}
                    {l.mv_breakdown?.blend_method !== 'formula_only' && (
                      <>
                        <Separator className="bg-border/20 my-1" />
                        <Row label="Blended Market Value" value={fmt(l.market_value)} highlight />
                      </>
                    )}
                  </div>
                </details>
              )}
              {l.profit_worst !== null && l.profit_worst < 0 && (
                <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-sm">
                  <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
                  <span className="text-sm text-red-400">Worst case scenario results in a loss of {fmt(Math.abs(l.profit_worst))}</span>
                </div>
              )}
              {!hasPrice && (
                <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-sm">
                  <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                  <span className="text-sm text-amber-400">Price not yet available — profit calculation incomplete</span>
                </div>
              )}
            </div>
            <Button variant="outline" className="w-full border-border/50" asChild>
              <a href={l.url} target="_blank" rel="noopener noreferrer" data-testid="view-original-btn"><ExternalLink className="h-4 w-4 mr-2" />View Original Listing</a>
            </Button>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

/* ═══ Small shared components ═══ */

function InfoCell({ icon: Icon, label, value }) {
  return (
    <div className="bg-background/50 border border-border/30 rounded-sm p-2.5">
      <div className="flex items-center gap-1 mb-0.5">{Icon && <Icon className="h-3 w-3 text-muted-foreground" />}<span className="text-[10px] text-muted-foreground tracking-wider uppercase">{label}</span></div>
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
      <span className={`font-bold ${highlight === true ? 'text-emerald-500' : highlight === false ? 'text-red-500' : ''}`}>{value}</span>
    </div>
  );
}

function SectionTitle({ icon: Icon, title }) {
  return (
    <h2 className="text-xl md:text-2xl font-bold tracking-tight uppercase flex items-center gap-2" style={{ fontFamily: 'Barlow Condensed' }}>
      <Icon className="h-5 w-5 text-primary" />{title}
    </h2>
  );
}

function FeatureCard({ icon: Icon, title, desc }) {
  return (
    <div className="bg-card border border-border/50 rounded-sm p-5 space-y-2">
      <Icon className="h-6 w-6 text-primary" />
      <h4 className="text-sm font-bold uppercase tracking-tight" style={{ fontFamily: 'Barlow Condensed' }}>{title}</h4>
      <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

function WebsiteCard({ name, url, desc, badge }) {
  return (
    <div className="bg-card border border-border/50 rounded-sm p-4 flex gap-4 items-start">
      <div className={`shrink-0 mt-1 w-10 h-10 rounded-sm flex items-center justify-center ${sourceColor(badge)}`}>
        <Globe className="h-5 w-5" />
      </div>
      <div className="space-y-1">
        <h4 className="text-sm font-bold" style={{ fontFamily: 'Barlow Condensed' }}>{name}</h4>
        <a href={url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline break-all">{url}</a>
        <p className="text-xs text-muted-foreground">{desc}</p>
      </div>
    </div>
  );
}

function ScoreExplainer({ score, label, color, desc }) {
  return (
    <div className={`border rounded-sm p-5 space-y-2 ${color}`}>
      <div className="flex items-center gap-2">
        <span className="text-2xl font-black font-data">{score}</span>
        <span className="text-sm font-bold uppercase">{label}</span>
      </div>
      <p className="text-xs opacity-80">{desc}</p>
    </div>
  );
}

function StepItem({ number, title, desc }) {
  return (
    <div className="flex gap-3">
      <span className="shrink-0 flex items-center justify-center w-6 h-6 bg-primary/20 text-primary text-xs font-bold rounded-sm">{number}</span>
      <div>
        <h4 className="text-sm font-bold">{title}</h4>
        <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
      </div>
    </div>
  );
}

function HowToStep({ num, text }) {
  return (
    <div className="flex gap-3 items-start">
      <span className="shrink-0 flex items-center justify-center w-5 h-5 bg-primary/15 text-primary text-[10px] font-bold rounded-full">{num}</span>
      <p className="text-sm text-muted-foreground">{text}</p>
    </div>
  );
}

export default App;
