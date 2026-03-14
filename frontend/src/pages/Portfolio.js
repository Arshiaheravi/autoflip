import { useState, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { portfolioApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils-app';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import {
  Plus, DollarSign, TrendingUp, TrendingDown, Target, Calendar,
  Wrench, RefreshCw, Trash2, FileDown, Edit,
} from 'lucide-react';

export default function Portfolio() {
  const { portfolio, setPortfolio } = useAppStore();
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingId, setEditingId] = useState(null);

  useEffect(() => { fetchPortfolio(); }, []);

  const fetchPortfolio = async () => {
    try {
      const res = await portfolioApi.getAll();
      setPortfolio(res.data);
    } catch (e) {
      console.error('Failed to fetch portfolio', e);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await portfolioApi.remove(id);
      setPortfolio(portfolio.filter(p => p.id !== id));
      toast.success('Deleted');
    } catch (e) {
      toast.error('Failed to delete');
    }
  };

  const handleExportCSV = () => {
    const headers = ['Vehicle', 'Buy Date', 'Buy Price', 'Repair Cost', 'Sale Date', 'Sale Price', 'Profit', 'ROI %'];
    const rows = portfolio.map(p => {
      const repairCost = (p.repair_items || []).reduce((s, r) => s + (r.cost || 0), 0);
      const totalCost = p.buy_price + repairCost;
      const profit = p.sale_price ? p.sale_price - totalCost : null;
      const roi = p.sale_price && totalCost > 0 ? ((profit / totalCost) * 100).toFixed(1) : '';
      return [p.vehicle_description, p.buy_date, p.buy_price, repairCost, p.sale_date || '', p.sale_price || '', profit || '', roi];
    });
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'autoflip-portfolio.csv'; a.click();
    URL.revokeObjectURL(url);
    toast.success('CSV exported');
  };

  // Stats
  const completed = portfolio.filter(p => p.sale_price);
  const active = portfolio.filter(p => !p.sale_price);
  const totalInvested = portfolio.reduce((s, p) => s + p.buy_price, 0);
  const totalRepair = portfolio.reduce((s, p) => s + (p.repair_items || []).reduce((ss, r) => ss + (r.cost || 0), 0), 0);
  const totalSold = completed.reduce((s, p) => s + p.sale_price, 0);
  const totalProfit = totalSold - completed.reduce((s, p) => s + p.buy_price + (p.repair_items || []).reduce((ss, r) => ss + (r.cost || 0), 0), 0);
  const avgRoi = completed.length > 0
    ? completed.reduce((s, p) => {
        const cost = p.buy_price + (p.repair_items || []).reduce((ss, r) => ss + (r.cost || 0), 0);
        return s + (cost > 0 ? ((p.sale_price - cost) / cost) * 100 : 0);
      }, 0) / completed.length
    : 0;

  // Chart data
  const chartData = completed.map(p => {
    const cost = p.buy_price + (p.repair_items || []).reduce((s, r) => s + (r.cost || 0), 0);
    const profit = p.sale_price - cost;
    return {
      name: p.vehicle_description.split(' ').slice(0, 3).join(' '),
      profit,
      positive: profit >= 0,
    };
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="portfolio-loading">
        <RefreshCw className="h-8 w-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="portfolio-page">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <SummaryCard icon={DollarSign} label="Total Invested" value={formatCurrency(totalInvested)} />
        <SummaryCard icon={Wrench} label="Total Repairs" value={formatCurrency(totalRepair)} />
        <SummaryCard icon={TrendingUp} label="Total Profit" value={formatCurrency(totalProfit)} accent={totalProfit >= 0 ? 'text-emerald-500' : 'text-red-500'} />
        <SummaryCard icon={Target} label="Avg ROI" value={`${avgRoi.toFixed(1)}%`} accent={avgRoi >= 0 ? 'text-emerald-500' : 'text-red-500'} />
        <SummaryCard icon={Calendar} label="Active Deals" value={active.length} />
      </div>

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="bg-card border border-border/50 rounded-sm p-4">
          <h3 className="text-base font-bold tracking-tight uppercase mb-4" style={{ fontFamily: 'Barlow Condensed' }}>
            Profit by Vehicle
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#a1a1aa' }} />
              <YAxis tick={{ fontSize: 10, fill: '#a1a1aa' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{ background: '#121212', border: '1px solid #27272a', borderRadius: 2 }}
                labelStyle={{ color: '#fafafa' }}
                formatter={(v) => [formatCurrency(v), 'Profit']}
              />
              <Bar dataKey="profit" radius={[2, 2, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.positive ? '#10b981' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Button onClick={() => setShowAddDialog(true)} data-testid="add-portfolio-btn">
          <Plus className="h-4 w-4 mr-2" />
          Log Purchase
        </Button>
        <Button variant="outline" onClick={handleExportCSV} className="border-border/50" data-testid="export-csv-btn">
          <FileDown className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Portfolio List */}
      <div className="space-y-3">
        {portfolio.map((item) => {
          const repairCost = (item.repair_items || []).reduce((s, r) => s + (r.cost || 0), 0);
          const totalCost = item.buy_price + repairCost;
          const profit = item.sale_price ? item.sale_price - totalCost : null;
          const roi = item.sale_price && totalCost > 0 ? ((profit / totalCost) * 100).toFixed(1) : null;
          const isActive = !item.sale_price;

          return (
            <div key={item.id} className="bg-card border border-border/50 rounded-sm p-4" data-testid={`portfolio-item-${item.id}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold tracking-tight" style={{ fontFamily: 'Barlow Condensed' }}>
                      {item.vehicle_description}
                    </h3>
                    {isActive ? (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-sm bg-amber-500/15 text-amber-500">ACTIVE</span>
                    ) : (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-sm bg-emerald-500/15 text-emerald-500">SOLD</span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                    <span>Bought: {item.buy_date}</span>
                    <span>Buy: {formatCurrency(item.buy_price)}</span>
                    <span>Repairs: {formatCurrency(repairCost)}</span>
                    {item.sale_date && <span>Sold: {item.sale_date}</span>}
                    {item.sale_price && <span>Sale: {formatCurrency(item.sale_price)}</span>}
                  </div>
                  {/* Repair Items */}
                  {item.repair_items?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {item.repair_items.map((r, i) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 bg-secondary rounded-sm">
                          {r.description}: {formatCurrency(r.cost)}
                        </span>
                      ))}
                    </div>
                  )}
                  {item.notes && (
                    <p className="mt-2 text-xs text-muted-foreground italic">{item.notes}</p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  {profit !== null ? (
                    <div>
                      <span className={`text-xl font-bold font-mono-data ${profit >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                        {formatCurrency(profit)}
                      </span>
                      <p className={`text-xs font-mono-data ${roi >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                        {roi}% ROI
                      </p>
                    </div>
                  ) : (
                    <span className="text-sm text-muted-foreground">In progress</span>
                  )}
                  <div className="flex gap-1 mt-2">
                    <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => handleDelete(item.id)} data-testid={`delete-portfolio-btn-${item.id}`}>
                      <Trash2 className="h-3 w-3 text-red-500" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Dialog */}
      {showAddDialog && (
        <AddPortfolioDialog
          onClose={() => setShowAddDialog(false)}
          onSaved={() => { setShowAddDialog(false); fetchPortfolio(); }}
        />
      )}
    </div>
  );
}

function SummaryCard({ icon: Icon, label, value, accent }) {
  return (
    <div className="bg-card border border-border/50 p-4 rounded-sm">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className="h-3 w-3 text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground tracking-wider uppercase">{label}</span>
      </div>
      <p className={`text-xl font-bold font-mono-data ${accent || ''}`}>{value}</p>
    </div>
  );
}

function AddPortfolioDialog({ onClose, onSaved }) {
  const [form, setForm] = useState({
    vehicle_description: '', buy_date: '', buy_price: '',
    sale_date: '', sale_price: '', notes: '',
  });
  const [repairItems, setRepairItems] = useState([]);
  const [newRepair, setNewRepair] = useState({ description: '', cost: '' });

  const handleSubmit = async () => {
    if (!form.vehicle_description || !form.buy_date || !form.buy_price) {
      toast.error('Fill required fields');
      return;
    }
    try {
      await portfolioApi.create({
        ...form,
        buy_price: parseFloat(form.buy_price),
        sale_price: form.sale_price ? parseFloat(form.sale_price) : null,
        sale_date: form.sale_date || null,
        repair_items: repairItems,
      });
      toast.success('Purchase logged');
      onSaved();
    } catch (e) {
      toast.error('Failed to save');
    }
  };

  const addRepairItem = () => {
    if (newRepair.description && newRepair.cost) {
      setRepairItems([...repairItems, { ...newRepair, cost: parseFloat(newRepair.cost), date: new Date().toISOString().split('T')[0] }]);
      setNewRepair({ description: '', cost: '' });
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md bg-card border-border/50" data-testid="add-portfolio-dialog">
        <DialogHeader>
          <DialogTitle className="uppercase tracking-tight" style={{ fontFamily: 'Barlow Condensed' }}>
            Log Purchase
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Input placeholder="Vehicle (e.g. 2019 Honda Civic)" value={form.vehicle_description} onChange={(e) => setForm({ ...form, vehicle_description: e.target.value })} className="bg-background border-border/50" data-testid="portfolio-vehicle-input" />
          <div className="grid grid-cols-2 gap-3">
            <Input type="date" value={form.buy_date} onChange={(e) => setForm({ ...form, buy_date: e.target.value })} className="bg-background border-border/50" data-testid="portfolio-buy-date-input" />
            <Input type="number" placeholder="Buy Price" value={form.buy_price} onChange={(e) => setForm({ ...form, buy_price: e.target.value })} className="bg-background border-border/50" data-testid="portfolio-buy-price-input" />
          </div>
          <Separator className="bg-border/30" />
          <p className="text-xs text-muted-foreground uppercase tracking-wider">Repair Items</p>
          {repairItems.map((r, i) => (
            <div key={i} className="text-xs px-2 py-1 bg-secondary rounded-sm flex justify-between">
              <span>{r.description}</span>
              <span className="font-mono-data">{formatCurrency(r.cost)}</span>
            </div>
          ))}
          <div className="flex gap-2">
            <Input placeholder="Repair description" value={newRepair.description} onChange={(e) => setNewRepair({ ...newRepair, description: e.target.value })} className="bg-background border-border/50 text-sm" data-testid="repair-desc-input" />
            <Input type="number" placeholder="Cost" value={newRepair.cost} onChange={(e) => setNewRepair({ ...newRepair, cost: e.target.value })} className="bg-background border-border/50 text-sm w-24" data-testid="repair-cost-input" />
            <Button size="sm" variant="outline" onClick={addRepairItem} data-testid="add-repair-btn">+</Button>
          </div>
          <Separator className="bg-border/30" />
          <p className="text-xs text-muted-foreground uppercase tracking-wider">Sale (optional)</p>
          <div className="grid grid-cols-2 gap-3">
            <Input type="date" value={form.sale_date} onChange={(e) => setForm({ ...form, sale_date: e.target.value })} className="bg-background border-border/50" data-testid="portfolio-sale-date-input" />
            <Input type="number" placeholder="Sale Price" value={form.sale_price} onChange={(e) => setForm({ ...form, sale_price: e.target.value })} className="bg-background border-border/50" data-testid="portfolio-sale-price-input" />
          </div>
          <Input placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="bg-background border-border/50" data-testid="portfolio-notes-input" />
          <Button className="w-full" onClick={handleSubmit} data-testid="submit-portfolio-btn">
            Log Purchase
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
