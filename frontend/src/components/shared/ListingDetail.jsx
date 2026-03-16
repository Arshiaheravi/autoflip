import { fmt, fmtNum, sourceLabel, scoreBadge } from '@/lib/utils-app';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useLanguage } from '@/lib/LanguageContext';
import {
  DollarSign, Gauge, Wrench, Car, Clock, ExternalLink,
  AlertTriangle, ChevronRight, Eye,
} from 'lucide-react';

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
      <span className={`font-bold ${highlight === true ? 'text-emerald-500' : highlight === false ? 'text-red-500' : ''}`}>{value}</span>
    </div>
  );
}

export default function ListingDetail({ listing, onClose }) {
  const { t } = useLanguage();
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
              <InfoCell icon={DollarSign} label={t('detail.price')} value={hasPrice ? fmt(l.price) : l.price_raw || t('detail.tbd')} />
              <InfoCell icon={Gauge} label={t('detail.mileage')} value={l.mileage ? `${fmtNum(l.mileage)} km` : t('detail.unknown')} />
              <InfoCell icon={Wrench} label={t('detail.damage')} value={l.damage || t('detail.noneListed')} />
              <InfoCell icon={Car} label={t('detail.brand')} value={l.brand || t('detail.unknown')} />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <InfoCell label={t('detail.source')} value={sourceLabel(l.source)} />
              <InfoCell label={t('detail.colour')} value={l.colour || t('detail.unknown')} />
              <InfoCell label={t('detail.status')} value={l.status?.replace('_', ' ').toUpperCase() || t('detail.unknown')} />
              <InfoCell icon={Clock} label={t('detail.dateFound')} value={l.first_seen ? new Date(l.first_seen).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' }) : t('detail.unknown')} />
            </div>
            {l.description && (
              <div className="bg-background/50 border border-border/30 rounded-sm p-3">
                <p className="text-xs text-muted-foreground">{l.description}</p>
              </div>
            )}
            <Separator className="bg-border/30" />
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold tracking-tight uppercase" style={{ fontFamily: 'Barlow Condensed' }}>{t('detail.profitAnalysis')}</h3>
                {l.deal_label && <span className={`text-base font-bold px-3 py-1 rounded-sm border ${scoreBadge(l.deal_label)}`}>{l.deal_score}/10 — {l.deal_label}</span>}
              </div>
              {l.ai_damage_detected && (
                <div className="flex items-center gap-2 p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-sm">
                  <Eye className="h-4 w-4 text-blue-400 shrink-0" />
                  <span className="text-xs text-blue-300">{t('detail.aiDetected')} <strong>{l.damage}</strong> {l.ai_damage_details && `— ${l.ai_damage_details}`}</span>
                </div>
              )}
              <div className="bg-background/50 border border-border/30 rounded-sm p-4 space-y-2 font-data text-sm">
                <Row label={t('detail.marketValue')} value={l.market_value ? fmt(l.market_value) : t('detail.na')} note={l.mv_breakdown?.title_status === 'salvage_title' ? t('detail.salvageNote') : l.mv_breakdown?.title_status === 'rebuilt_title' ? t('detail.rebuiltNote') : ''} />
                <Row label={t('detail.purchasePrice')} value={hasPrice ? fmt(l.price) : t('detail.tbd')} />
                <Row label={t('detail.repairLow')} value={fmt(l.repair_low)} dim />
                <Row label={t('detail.repairHigh')} value={fmt(l.repair_high)} dim />
                {l.repair_breakdown?.salvage_to_rebuilt_cost > 0 && (
                  <Row label={`  ${t('detail.salvageProcess')}`} value={fmt(l.repair_breakdown.salvage_to_rebuilt_cost)} dim note={t('detail.salvageProcessNote')} />
                )}
                <Row label={t('detail.ontarioFees')} value={l.fees ? fmt(l.fees) : t('detail.na')} dim note={t('detail.ontarioFeesNote')} />
                <Separator className="bg-border/30" />
                <Row label={t('detail.bestProfit')} value={l.profit_best !== null ? fmt(l.profit_best) : t('detail.na')} highlight={l.profit_best > 0} />
                <Row label={t('detail.worstProfit')} value={l.profit_worst !== null ? fmt(l.profit_worst) : t('detail.na')} highlight={l.profit_worst > 0} />
                <Row label={t('detail.roiBest')} value={l.roi_best !== null ? `${l.roi_best}%` : t('detail.na')} />
                <Row label={t('detail.roiWorst')} value={l.roi_worst !== null ? `${l.roi_worst}%` : t('detail.na')} />
              </div>
              {l.mv_breakdown && (
                <details className="group">
                  <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5">
                    <ChevronRight className="h-3 w-3 group-open:rotate-90 transition-transform" />
                    {t('detail.viewBreakdown')}
                  </summary>
                  <div className="mt-2 bg-background/50 border border-border/30 rounded-sm p-3 space-y-1.5 font-data text-[11px]">
                    {l.mv_breakdown?.autotrader_median && (
                      <>
                        <Row label={t('detail.atComps')} value={`${l.mv_breakdown.autotrader_count} ${t('detail.listingsFound')}`} dim note={l.mv_breakdown.blend_method?.replace(/_/g, ' ')} />
                        <Row label={`  ${t('detail.atMedian')}`} value={fmt(l.mv_breakdown.autotrader_median)} dim />
                        <Row label={`  ${t('detail.atRange')}`} value={`${fmt(l.mv_breakdown.autotrader_low)} – ${fmt(l.mv_breakdown.autotrader_high)}`} dim />
                        <Row label={`  ${t('detail.atAdjusted')}`} value={fmt(l.mv_breakdown.autotrader_adjusted)} dim />
                        <Separator className="bg-border/20 my-1" />
                      </>
                    )}
                    <Row label={t('detail.formulaMsrp')} value={fmt(l.mv_breakdown.msrp)} dim note={l.mv_breakdown.msrp_source === 'model_match' ? t('detail.modelMatched') : t('detail.estimated')} />
                    <Row label={t('detail.formulaDeprec')} value={`×${l.mv_breakdown.depreciation}`} dim note={`${l.mv_breakdown.age} ${t('detail.yrOld')}`} />
                    <Row label={t('detail.formulaBrand')} value={`×${l.mv_breakdown.brand_mult}`} dim note={l.mv_breakdown.brand} />
                    <Row label={t('detail.formulaBody')} value={`×${l.mv_breakdown.body_mult}`} dim />
                    <Row label={t('detail.formulaTrim')} value={`×${l.mv_breakdown.trim_mult}`} dim />
                    <Row label={t('detail.formulaColor')} value={`×${l.mv_breakdown.color_mult}`} dim />
                    <Row label={t('detail.formulaMileage')} value={`×${l.mv_breakdown.mileage_mult}`} dim />
                    <Row label={t('detail.formulaTitle')} value={`×${l.mv_breakdown.title_mult}`} dim note={l.mv_breakdown.title_status?.replace(/_/g, ' ')} />
                    {l.mv_breakdown?.formula_value && (
                      <Row label={t('detail.formulaResult')} value={fmt(l.mv_breakdown.formula_value)} dim />
                    )}
                    {l.mv_breakdown?.blend_method !== 'formula_only' && (
                      <>
                        <Separator className="bg-border/20 my-1" />
                        <Row label={t('detail.blendedValue')} value={fmt(l.market_value)} highlight />
                      </>
                    )}
                  </div>
                </details>
              )}
              {l.profit_worst !== null && l.profit_worst < 0 && (
                <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-sm">
                  <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
                  <span className="text-sm text-red-400">{t('detail.worstLoss')} {fmt(Math.abs(l.profit_worst))}</span>
                </div>
              )}
              {!hasPrice && (
                <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-sm">
                  <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                  <span className="text-sm text-amber-400">{t('detail.noPrice')}</span>
                </div>
              )}
            </div>
            <Button variant="outline" className="w-full border-border/50" asChild>
              <a href={l.url} target="_blank" rel="noopener noreferrer" data-testid="view-original-btn">
                <ExternalLink className="h-4 w-4 mr-2" />{t('detail.viewOriginal')}
              </a>
            </Button>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
