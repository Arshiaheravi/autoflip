import { fmt, fmtNum, sourceLabel, sourceColor, scoreBadge } from '@/lib/utils-app';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Car, ExternalLink, X } from 'lucide-react';

/**
 * Returns the index of the best (winner) value in an array.
 * direction: 'max' = highest wins, 'min' = lowest wins.
 * Returns -1 if all values are null/undefined.
 */
function winnerIndex(values, direction = 'max') {
  const valid = values.map((v, i) => ({ v, i })).filter(({ v }) => v !== null && v !== undefined);
  if (valid.length < 2) return -1;
  return valid.reduce((best, cur) =>
    direction === 'max' ? (cur.v > best.v ? cur : best) : (cur.v < best.v ? cur : best)
  ).i;
}

function CompareCell({ value, isWinner, dim, className = '' }) {
  return (
    <div className={`text-sm font-data text-right py-2 px-3 ${isWinner ? 'text-emerald-400 font-bold' : dim ? 'text-muted-foreground' : 'text-foreground'} ${className}`}>
      {value ?? <span className="text-muted-foreground/40">—</span>}
    </div>
  );
}

function CompareRow({ label, values, direction, formatter, dim }) {
  const raw = values.map(v => v);
  const winner = winnerIndex(raw, direction);
  return (
    <div className="grid border-b border-border/20 last:border-0" style={{ gridTemplateColumns: `140px repeat(${values.length}, 1fr)` }}>
      <div className={`text-[10px] uppercase tracking-wider py-2 px-3 flex items-center ${dim ? 'text-muted-foreground/60' : 'text-muted-foreground'}`}>
        {label}
      </div>
      {values.map((v, i) => (
        <CompareCell
          key={i}
          value={formatter ? formatter(v) : v}
          isWinner={winner === i && v !== null && v !== undefined}
          dim={dim}
        />
      ))}
    </div>
  );
}

export default function CompareModal({ listings, onClose }) {
  if (!listings || listings.length < 2) return null;
  const n = listings.length;

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent
        className="bg-card border-border/50 p-0 overflow-hidden"
        style={{ maxWidth: n === 3 ? '900px' : '680px', width: '95vw', maxHeight: '90vh' }}
        data-testid="compare-modal"
      >
        <ScrollArea className="max-h-[90vh]">
          <div className="p-5 space-y-4">
            <DialogHeader>
              <div className="flex items-center justify-between">
                <DialogTitle className="text-lg font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>
                  Compare {n} Listings
                </DialogTitle>
                <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors" data-testid="compare-close">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </DialogHeader>

            {/* Photo + title header row */}
            <div className="grid gap-3" style={{ gridTemplateColumns: `140px repeat(${n}, 1fr)` }}>
              <div /> {/* label spacer */}
              {listings.map((l, i) => (
                <div key={i} className="flex flex-col gap-2">
                  <div className="w-full aspect-video bg-secondary rounded-sm overflow-hidden">
                    {l.photo
                      ? <img src={l.photo} alt="" className="w-full h-full object-cover" loading="lazy" />
                      : <div className="flex items-center justify-center h-full"><Car className="h-6 w-6 text-muted-foreground/30" /></div>
                    }
                  </div>
                  <div>
                    <p className="text-xs font-bold leading-tight" style={{ fontFamily: 'Barlow Condensed' }}>{l.title}</p>
                    <span className={`inline-block mt-1 text-[9px] px-1.5 py-0.5 rounded-sm ${sourceColor(l.source)}`}>
                      {sourceLabel(l.source).split(' ')[0]}
                    </span>
                  </div>
                  {l.deal_label && (
                    <span className={`inline-flex items-center justify-center text-xs font-bold px-2 py-0.5 rounded-sm border ${scoreBadge(l.deal_label)}`}>
                      {l.deal_score}/10 {l.deal_label}
                    </span>
                  )}
                </div>
              ))}
            </div>

            {/* Comparison rows */}
            <div className="bg-background/50 border border-border/30 rounded-sm overflow-hidden text-sm">
              <CompareRow
                label="Price"
                values={listings.map(l => (l.price && l.price > 0 ? l.price : null))}
                direction="min"
                formatter={v => v ? fmt(v) : (listings.find(x => !x.price || x.price === 0)?.price_raw?.substring(0, 10) || 'TBD')}
              />
              <CompareRow
                label="Mileage"
                values={listings.map(l => l.mileage || null)}
                direction="min"
                formatter={v => v ? `${fmtNum(v)} km` : '—'}
              />
              <CompareRow
                label="Damage"
                values={listings.map(l => l.damage || null)}
                direction={null}
                formatter={v => v || '—'}
                dim
              />
              <CompareRow
                label="Colour"
                values={listings.map(l => l.colour || null)}
                direction={null}
                formatter={v => v || '—'}
                dim
              />
              <CompareRow
                label="Title"
                values={listings.map(l => l.brand || null)}
                direction={null}
                formatter={v => v || '—'}
                dim
              />
              <CompareRow
                label="Market Value"
                values={listings.map(l => l.market_value || null)}
                direction="max"
                formatter={v => v ? fmt(v) : '—'}
              />
              <CompareRow
                label="Repair Est"
                values={listings.map(l => (l.repair_low != null ? ((l.repair_low + (l.repair_high || l.repair_low)) / 2) : null))}
                direction="min"
                formatter={(v, i) => {
                  const l = listings[i];
                  if (l.repair_low == null) return '—';
                  return `${fmt(l.repair_low)} – ${fmt(l.repair_high)}`;
                }}
                dim
              />
              <CompareRow
                label="Fees"
                values={listings.map(l => l.fees || null)}
                direction="min"
                formatter={v => v ? fmt(v) : '—'}
                dim
              />
              <CompareRow
                label="Best Profit"
                values={listings.map(l => l.profit_best ?? null)}
                direction="max"
                formatter={v => v != null ? fmt(v) : '—'}
              />
              <CompareRow
                label="Worst Profit"
                values={listings.map(l => l.profit_worst ?? null)}
                direction="max"
                formatter={v => v != null ? fmt(v) : '—'}
              />
              <CompareRow
                label="ROI Best"
                values={listings.map(l => l.roi_best ?? null)}
                direction="max"
                formatter={v => v != null ? `${v}%` : '—'}
              />
              <CompareRow
                label="ROI Worst"
                values={listings.map(l => l.roi_worst ?? null)}
                direction="max"
                formatter={v => v != null ? `${v}%` : '—'}
              />
              <CompareRow
                label="Deal Score"
                values={listings.map(l => l.deal_score ?? null)}
                direction="max"
                formatter={v => v != null ? `${v}/10` : '—'}
              />
            </div>

            {/* View original links */}
            <div className="grid gap-2" style={{ gridTemplateColumns: `140px repeat(${n}, 1fr)` }}>
              <div />
              {listings.map((l, i) => (
                <Button key={i} variant="outline" size="sm" className="border-border/50 text-xs w-full" asChild>
                  <a href={l.url} target="_blank" rel="noopener noreferrer" data-testid={`compare-link-${i}`}>
                    <ExternalLink className="h-3 w-3 mr-1" />View
                  </a>
                </Button>
              ))}
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
