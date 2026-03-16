import { useState, useEffect } from 'react';
import { scrapeApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useLanguage } from '@/lib/LanguageContext';
import {
  RefreshCw, Zap, Timer, LayoutDashboard, Info, Settings,
} from 'lucide-react';

export default function NavBar({ page, setPage }) {
  const [scrapeStatus, setScrapeStatus] = useState(null);
  const [countdown, setCountdown] = useState(null);
  const [scraping, setScraping] = useState(false);
  const { lang, setLang, t } = useLanguage();

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
      toast.info(t('nav.scanStarted'));
    } catch {
      toast.error(t('nav.scanFailed'));
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

  const navItems = [
    { id: 'dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard },
    { id: 'about', labelKey: 'nav.about', icon: Info },
    { id: 'settings', labelKey: 'nav.settings', icon: Settings },
  ];

  return (
    <header className="sticky top-0 z-40 bg-[#09090b]/90 backdrop-blur-xl border-b border-border/30" data-testid="navbar">
      <div className="max-w-[1600px] mx-auto px-4 md:px-8">
        <div className="h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => setPage('dashboard')}>
              <div className="flex items-center justify-center w-8 h-8 bg-primary/20 rounded-sm">
                <Zap className="h-5 w-5 text-primary" />
              </div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-black tracking-tighter uppercase leading-none" style={{ fontFamily: 'Barlow Condensed' }} data-testid="app-title">
                  AutoFlip
                </h1>
                <span className="text-[9px] text-muted-foreground tracking-[0.2em] uppercase">{t('nav.intelligence')}</span>
              </div>
            </div>
            <nav className="flex items-center gap-1" data-testid="nav-tabs">
              {navItems.map(({ id, labelKey, icon: Icon }) => (
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
                  <span className="hidden md:inline">{t(labelKey)}</span>
                </button>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-4 text-[11px] mr-2">
              <div className="flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${scraping ? 'bg-amber-400' : 'bg-emerald-400'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${scraping ? 'bg-amber-400' : 'bg-emerald-400'}`}></span>
                </span>
                <span className={scraping ? 'text-amber-400' : 'text-emerald-400'}>
                  {scraping ? t('nav.scanning') : t('nav.live')}
                </span>
              </div>
              {!scraping && countdown !== null && countdown > 0 && (
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Timer className="h-3 w-3" />
                  <span className="font-data">{formatCountdown(countdown)}</span>
                </div>
              )}
              <div className="text-muted-foreground">{t('nav.every')} {intervalMin}m</div>
            </div>

            {/* Language toggle */}
            <button
              onClick={() => setLang(lang === 'en' ? 'fa' : 'en')}
              className="flex items-center gap-0.5 px-2 py-1 rounded-sm border border-border/50 text-[11px] font-bold transition-all hover:bg-secondary/50"
              title="Toggle language / تغییر زبان"
              data-testid="lang-toggle"
            >
              <span className={lang === 'en' ? 'text-primary' : 'text-muted-foreground'}>EN</span>
              <span className="text-border mx-0.5">|</span>
              <span className={lang === 'fa' ? 'text-primary' : 'text-muted-foreground'}>فا</span>
            </button>

            <Button
              size="sm"
              variant={scraping ? "outline" : "default"}
              onClick={handleScrape}
              disabled={scraping}
              className="text-xs"
              data-testid="scrape-btn"
            >
              <RefreshCw className={`h-3 w-3 mr-1 ${scraping ? 'animate-spin' : ''}`} />
              {scraping ? t('nav.scanning_btn') : t('nav.scanNow')}
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
