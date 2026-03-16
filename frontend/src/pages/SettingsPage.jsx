import { useState, useEffect } from 'react';
import { settingsApi, scrapeApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useLanguage } from '@/lib/LanguageContext';
import { RefreshCw, Timer, Clock, Shield, CheckCircle2 } from 'lucide-react';

export default function SettingsPage() {
  const { t } = useLanguage();
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
      toast.success(t('settings.saved'));
    } catch {
      toast.error(t('settings.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-20"><RefreshCw className="h-8 w-8 text-primary animate-spin" /></div>;
  }

  const intervalOptions = [
    { value: '300', labelKey: '5min' },
    { value: '600', labelKey: '10min' },
    { value: '900', labelKey: '15min' },
    { value: '1800', labelKey: '30min' },
  ];

  return (
    <main className="max-w-3xl mx-auto px-4 md:px-8 py-8 space-y-8 animate-fade-in" data-testid="settings-page">
      <h2 className="text-2xl font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>{t('settings.title')}</h2>

      <section className="bg-card border border-border/50 rounded-sm p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Timer className="h-4 w-4 text-primary" />
          <h3 className="text-base font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>{t('settings.scanFreq')}</h3>
        </div>
        <p className="text-sm text-muted-foreground">{t('settings.scanFreqDesc')}</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2" data-testid="interval-options">
          {intervalOptions.map(({ value, labelKey }) => (
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
              {t(labelKey)}
            </button>
          ))}
        </div>
        <Button onClick={handleSave} disabled={saving} className="mt-2" data-testid="save-settings-btn">
          {saving ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle2 className="h-4 w-4 mr-2" />}
          {t('settings.save')}
        </Button>
      </section>

      <section className="bg-card border border-border/50 rounded-sm p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-primary" />
          <h3 className="text-base font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>{t('settings.scanHistory')}</h3>
        </div>
        {scanHistory.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('settings.noScans')}</p>
        ) : (
          <div className="space-y-1.5 max-h-64 overflow-y-auto" data-testid="scan-history-list">
            {scanHistory.map((scan, i) => (
              <div key={scan.id || i} className="flex items-center justify-between px-3 py-2 bg-background/50 rounded-sm text-xs">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                  <span className="font-data">{new Date(scan.timestamp).toLocaleString()}</span>
                </div>
                <span className="text-muted-foreground">{t('settings.every')} {Math.round((scan.interval || 600) / 60)}m</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="bg-card border border-border/50 rounded-sm p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-primary" />
          <h3 className="text-base font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>{t('settings.dataSources')}</h3>
        </div>
        <div className="space-y-2 text-sm text-muted-foreground">
          <p><strong className="text-foreground">Cathcart Auto — Rebuilders:</strong> cathcartauto.com/vehicles/rebuilders/</p>
          <p><strong className="text-foreground">Cathcart Auto — Used Cars:</strong> cathcartauto.com/vehicles/used-cars/</p>
          <p><strong className="text-foreground">Pic N Save — Rebuildable Cars:</strong> picnsave.ca/rebuildable-cars/</p>
        </div>
      </section>
    </main>
  );
}
