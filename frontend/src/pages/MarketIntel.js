import { useState, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { marketApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Cell } from 'recharts';
import {
  TrendingUp, TrendingDown, AlertTriangle, Flame, RefreshCw,
  BarChart3, Thermometer, ArrowUp, ArrowDown, Minus,
} from 'lucide-react';

export default function MarketIntel() {
  const { marketIntel, setMarketIntel } = useAppStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const res = await marketApi.getIntelligence();
      setMarketIntel(res.data);
    } catch (e) {
      console.error('Failed to fetch market intel', e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="market-loading">
        <RefreshCw className="h-8 w-8 text-primary animate-spin" />
      </div>
    );
  }

  if (!marketIntel) return null;

  const heatmapData = marketIntel.demand_heatmap || [];
  const seasonal = marketIntel.seasonal_trends || [];
  const oversupply = marketIntel.oversupply_alerts || [];

  return (
    <div className="space-y-8 animate-fade-in" data-testid="market-intel-page">
      {/* Demand Heatmap */}
      <section>
        <h3 className="text-xl font-bold tracking-tight uppercase mb-4 flex items-center gap-2" style={{ fontFamily: 'Barlow Condensed' }}>
          <Thermometer className="h-5 w-5 text-primary" />
          Demand Heatmap
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="demand-heatmap">
          {heatmapData.map((item, i) => (
            <div
              key={i}
              className={`p-4 rounded-sm border transition-colors ${
                item.demand === 'high' ? 'border-emerald-500/30 bg-emerald-500/5' :
                item.demand === 'medium' ? 'border-amber-500/30 bg-amber-500/5' :
                'border-red-500/30 bg-red-500/5'
              }`}
              data-testid={`heatmap-item-${item.make}`}
            >
              <div className="flex items-center justify-between">
                <h4 className="text-base font-bold" style={{ fontFamily: 'Barlow Condensed' }}>{item.make}</h4>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-sm ${
                  item.demand === 'high' ? 'score-buy' : item.demand === 'medium' ? 'score-watch' : 'score-skip'
                }`}>
                  {item.demand.toUpperCase()}
                </span>
              </div>
              <div className="flex items-center gap-4 mt-2 text-xs">
                <span className="text-muted-foreground">{item.count} listing{item.count !== 1 ? 's' : ''}</span>
                <span className="font-mono-data">Avg Score: <span className="text-primary font-bold">{item.avg_score}</span></span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Seasonal Trends */}
      <section>
        <h3 className="text-xl font-bold tracking-tight uppercase mb-4 flex items-center gap-2" style={{ fontFamily: 'Barlow Condensed' }}>
          <BarChart3 className="h-5 w-5 text-primary" />
          Seasonal Price Multipliers
        </h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="seasonal-trends">
          {seasonal.map((trend, i) => (
            <div key={i} className="bg-card border border-border/50 rounded-sm p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-bold uppercase tracking-wider" style={{ fontFamily: 'Barlow Condensed' }}>
                  {trend.vehicle_type}
                </h4>
                <span className="text-xs text-muted-foreground">Peak: {trend.peak}</span>
              </div>
              <ResponsiveContainer width="100%" height={150}>
                <LineChart data={trend.monthly} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="month" tick={{ fontSize: 9, fill: '#a1a1aa' }} />
                  <YAxis domain={[0.95, 1.2]} tick={{ fontSize: 9, fill: '#a1a1aa' }} tickFormatter={(v) => `${(v * 100 - 100).toFixed(0)}%`} />
                  <Tooltip
                    contentStyle={{ background: '#121212', border: '1px solid #27272a', borderRadius: 2 }}
                    formatter={(v) => [`${((v - 1) * 100).toFixed(1)}% premium`, 'Price']}
                  />
                  <Line type="monotone" dataKey="multiplier" stroke="#2563eb" strokeWidth={2} dot={{ r: 3, fill: '#2563eb' }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      </section>

      {/* Oversupply Alerts */}
      {oversupply.length > 0 && (
        <section>
          <h3 className="text-xl font-bold tracking-tight uppercase mb-4 flex items-center gap-2" style={{ fontFamily: 'Barlow Condensed' }}>
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Oversupply Alerts
          </h3>
          <div className="bg-card border border-amber-500/20 rounded-sm p-4" data-testid="oversupply-alerts">
            <p className="text-xs text-muted-foreground mb-3">
              Makes/models with high listing counts - may indicate slow sellers
            </p>
            <div className="flex flex-wrap gap-2">
              {oversupply.map((item, i) => (
                <span key={i} className="text-xs font-semibold px-3 py-1.5 rounded-sm bg-amber-500/10 text-amber-500 border border-amber-500/20">
                  {item.make_model}: {item.count} listings
                </span>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Quick Stats */}
      <section className="bg-card border border-border/50 rounded-sm p-6">
        <h3 className="text-xl font-bold tracking-tight uppercase mb-4" style={{ fontFamily: 'Barlow Condensed' }}>
          Market Summary
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-3xl font-bold font-mono-data text-primary">{marketIntel.total_active}</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wider mt-1">Active Listings</p>
          </div>
          <div>
            <p className="text-3xl font-bold font-mono-data text-emerald-500">{heatmapData.filter(h => h.demand === 'high').length}</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wider mt-1">High Demand Makes</p>
          </div>
          <div>
            <p className="text-3xl font-bold font-mono-data text-amber-500">{oversupply.length}</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wider mt-1">Oversupply Alerts</p>
          </div>
          <div>
            <p className="text-3xl font-bold font-mono-data">{seasonal.length}</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wider mt-1">Vehicle Categories</p>
          </div>
        </div>
      </section>
    </div>
  );
}
