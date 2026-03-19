import { sourceColor } from '@/lib/utils-app';
import { Separator } from '@/components/ui/separator';
import { useLanguage } from '@/lib/LanguageContext';
import {
  Zap, Globe, Calculator, Target, Eye, Wrench,
  BarChart3, AlertTriangle, Crosshair,
} from 'lucide-react';

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

export default function AboutPage() {
  const { t } = useLanguage();

  return (
    <main className="max-w-4xl mx-auto px-4 md:px-8 py-10 space-y-12 animate-fade-in" data-testid="about-page">
      <section className="text-center space-y-4">
        <div className="flex items-center justify-center w-16 h-16 mx-auto bg-primary/20 rounded-sm mb-6">
          <Zap className="h-10 w-10 text-primary" />
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase" style={{ fontFamily: 'Barlow Condensed' }}>
          {t('about.title')}
        </h1>
        <p className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          {t('about.subtitle')}
        </p>
      </section>

      <Separator className="bg-border/30" />

      <section className="space-y-6">
        <SectionTitle icon={Globe} title={t('about.whatItDoes')} />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FeatureCard icon={Globe} title={t('about.scansWebsites')} desc={t('about.scansDesc')} />
          <FeatureCard icon={Calculator} title={t('about.calculatesProfit')} desc={t('about.calcDesc')} />
          <FeatureCard icon={Target} title={t('about.scoresDeals')} desc={t('about.scoresDesc')} />
        </div>
      </section>

      <section className="space-y-6">
        <SectionTitle icon={Eye} title={t('about.websites')} />
        <div className="space-y-3">
          <WebsiteCard name="Cathcart Auto — Rebuilders" url="https://cathcartauto.com/vehicles/rebuilders/" desc={t('about.cathcartRebuildersDesc')} badge="cathcart_rebuilders" />
          <WebsiteCard name="Cathcart Auto — Used Cars" url="https://cathcartauto.com/vehicles/used-cars/" desc={t('about.cathcartUsedDesc')} badge="cathcart_used" />
          <WebsiteCard name="Pic N Save — Rebuildable Cars" url="https://picnsave.ca/rebuildable-cars/" desc={t('about.picnsaveDesc')} badge="picnsave" />
        </div>
      </section>

      <section className="space-y-6">
        <SectionTitle icon={Calculator} title={t('about.howCalc')} />
        <div className="bg-card border border-border/50 rounded-sm p-6 space-y-4">
          <StepItem number="1" title={t('about.step1Title')} desc={t('about.step1Desc')} />
          <StepItem number="2" title={t('about.step2Title')} desc={t('about.step2Desc')} />
          <StepItem number="3" title={t('about.step3Title')} desc={t('about.step3Desc')} />
          <StepItem number="4" title={t('about.step4Title')} desc={t('about.step4Desc')} />
        </div>
      </section>

      <section className="space-y-6">
        <SectionTitle icon={Wrench} title={t('about.repairCosts')} />
        <div className="bg-card border border-border/50 rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/30 text-[10px] text-muted-foreground uppercase tracking-wider">
                <th className="text-left px-4 py-2.5">{t('about.damageType')}</th>
                <th className="text-right px-4 py-2.5">{t('about.lowEst')}</th>
                <th className="text-right px-4 py-2.5">{t('about.highEst')}</th>
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
        <p className="text-xs text-muted-foreground">{t('about.repairNote')}</p>
      </section>

      <section className="space-y-6">
        <SectionTitle icon={Crosshair} title={t('about.scoring')} />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ScoreExplainer score="8-10" label="BUY" color="bg-emerald-500/10 border-emerald-500/30 text-emerald-400" desc={t('about.buyDesc')} />
          <ScoreExplainer score="5-7" label="WATCH" color="bg-amber-500/10 border-amber-500/30 text-amber-400" desc={t('about.watchDesc')} />
          <ScoreExplainer score="1-4" label="SKIP" color="bg-red-500/10 border-red-500/30 text-red-400" desc={t('about.skipDesc')} />
        </div>
      </section>

      <section className="space-y-6">
        <SectionTitle icon={BarChart3} title={t('about.howToUse')} />
        <div className="bg-card border border-border/50 rounded-sm p-6 space-y-3">
          <HowToStep num="1" text={t('about.howStep1')} />
          <HowToStep num="2" text={t('about.howStep2')} />
          <HowToStep num="3" text={t('about.howStep3')} />
          <HowToStep num="4" text={t('about.howStep4')} />
          <HowToStep num="5" text={t('about.howStep5')} />
          <HowToStep num="6" text={t('about.howStep6')} />
        </div>
      </section>

      <section className="space-y-6">
        <SectionTitle icon={AlertTriangle} title={t('about.notes')} />
        <div className="bg-card border border-amber-500/20 rounded-sm p-6 space-y-2 text-sm text-muted-foreground">
          <p dangerouslySetInnerHTML={{ __html: t('about.note1') }} />
          <p>{t('about.note2')}</p>
          <p dangerouslySetInnerHTML={{ __html: t('about.note3') }} />
          <p dangerouslySetInnerHTML={{ __html: t('about.note4') }} />
        </div>
      </section>
    </main>
  );
}
