import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/AuthContext';
import {
  Zap, CheckCircle2, ArrowRight, Star, Shield, Clock,
  Bell, Brain, TrendingUp, Users, X,
} from 'lucide-react';

const FEATURES_FREE = [
  'Browse all auction listings',
  'Basic profit estimates',
  'Deal scoring (BUY / WATCH / SKIP)',
  'Ontario fee calculator',
];

const FEATURES_PRO = [
  'Everything in Free',
  'Real-time deal alerts (BUY deals within 10 min)',
  'AI damage detection on every vehicle',
  'AutoTrader market comps (live data)',
  'Price drop notifications',
  'Export listings to CSV',
  'Priority email support',
];

const FAQ = [
  {
    q: 'How quickly do I receive deal alerts?',
    a: 'AutoFlip scans every 10 minutes. When a new BUY deal (score 8+) is found, you get an email within minutes — before it hits any other platform.',
  },
  {
    q: 'What auctions does AutoFlip monitor?',
    a: "Currently Cathcart Auto (Rebuilders + Used) and Pic N Save in Ontario. We're adding IAA Canada and Copart Canada next.",
  },
  {
    q: 'Do I need a dealer license?',
    a: "No. AutoFlip only shows vehicles that don't require a dealer license to purchase — perfect for private flippers in Ontario.",
  },
  {
    q: 'Can I cancel anytime?',
    a: 'Yes, absolutely. No contracts, no cancellation fees. Cancel from your account settings at any time.',
  },
  {
    q: 'How accurate are the profit estimates?',
    a: 'Market values are blended from live AutoTrader comps (60%) and our formula (40%). Repair estimates use Ontario body shop rates. Always verify before purchasing.',
  },
];

function PlanCard({ title, price, period, priceNote, features, cta, highlighted, badge, onSelect, disabled }) {
  return (
    <div
      className={`relative flex flex-col rounded-sm border p-6 ${
        highlighted
          ? 'border-primary/60 bg-primary/5 shadow-lg shadow-primary/10'
          : 'border-border/50 bg-card'
      }`}
    >
      {badge && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="flex items-center gap-1 px-3 py-0.5 bg-primary text-primary-foreground text-[11px] font-bold rounded-full">
            <Star className="h-3 w-3" />
            {badge}
          </span>
        </div>
      )}

      <div className="mb-5">
        <h3 className="text-base font-bold mb-1">{title}</h3>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-black font-data">{price}</span>
          {period && <span className="text-sm text-muted-foreground">/{period}</span>}
        </div>
        {priceNote && <p className="text-xs text-muted-foreground mt-1">{priceNote}</p>}
      </div>

      <ul className="space-y-2.5 mb-6 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      <Button
        onClick={onSelect}
        variant={highlighted ? 'default' : 'outline'}
        disabled={disabled}
        className="w-full"
        data-testid={`cta-${title.toLowerCase().replace(/\s+/g, '-')}`}
      >
        {cta} {highlighted && <ArrowRight className="ml-1 h-4 w-4" />}
      </Button>
    </div>
  );
}

export default function PricingPage({ onSignup, onLogin, onClose }) {
  const { user, isAuthenticated } = useAuth();
  const [billingPeriod, setBillingPeriod] = useState('yearly');

  const monthlyPrice = '$4.99';
  const yearlyPrice = '$39.99';
  const yearlyPerMonth = '$3.33';

  return (
    <div className="min-h-screen bg-[#09090b] overflow-y-auto" data-testid="pricing-page">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-[#09090b]/90 backdrop-blur-xl border-b border-border/30">
        <div className="max-w-5xl mx-auto px-4 md:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5 cursor-pointer" onClick={onClose}>
            <div className="flex items-center justify-center w-8 h-8 bg-primary/20 rounded-sm">
              <Zap className="h-5 w-5 text-primary" />
            </div>
            <h1 className="text-sm font-black tracking-tighter uppercase" style={{ fontFamily: 'Barlow Condensed' }}>
              AutoFlip
            </h1>
          </div>
          <div className="flex items-center gap-2">
            {!isAuthenticated && (
              <Button variant="ghost" size="sm" onClick={onLogin} className="text-xs">
                Sign In
              </Button>
            )}
            {onClose && (
              <Button variant="ghost" size="sm" onClick={onClose} className="text-xs">
                <X className="h-4 w-4 mr-1" /> Close
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 md:px-8 py-12">

        {/* Hero */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/20 rounded-full text-xs text-primary mb-4">
            <Bell className="h-3 w-3" />
            New BUY deals found every 10 minutes
          </div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-4" style={{ fontFamily: 'Barlow Condensed' }}>
            Find profitable car flips<br />
            <span className="text-primary">before anyone else</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-xl mx-auto">
            AutoFlip monitors Ontario auction sites 24/7, calculates your real profit after fees, and alerts you the moment a BUY deal appears.
          </p>
        </div>

        {/* Social proof bar */}
        <div className="flex flex-wrap justify-center gap-8 mb-10 text-center">
          {[
            { icon: Clock, stat: '10 min', label: 'Scan interval' },
            { icon: TrendingUp, stat: '$2,400+', label: 'Avg profit on BUY deals' },
            { icon: Brain, stat: 'AI', label: 'Damage detection' },
            { icon: Users, stat: 'Ontario', label: 'Exclusive market data' },
          ].map(({ icon: Icon, stat, label }) => (
            <div key={label} className="flex flex-col items-center gap-1">
              <Icon className="h-4 w-4 text-primary mb-0.5" />
              <span className="text-xl font-black font-data">{stat}</span>
              <span className="text-xs text-muted-foreground">{label}</span>
            </div>
          ))}
        </div>

        {/* Billing toggle */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center gap-1 p-1 bg-card border border-border/50 rounded-sm">
            <button
              onClick={() => setBillingPeriod('monthly')}
              className={`px-4 py-1.5 text-sm rounded-sm transition-all ${
                billingPeriod === 'monthly' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingPeriod('yearly')}
              className={`px-4 py-1.5 text-sm rounded-sm transition-all flex items-center gap-1.5 ${
                billingPeriod === 'yearly' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Yearly
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                billingPeriod === 'yearly' ? 'bg-white/20' : 'bg-emerald-500/20 text-emerald-400'
              }`}>
                2 months free
              </span>
            </button>
          </div>
        </div>

        {/* Plan cards */}
        <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto mb-14">
          <PlanCard
            title="Free"
            price="$0"
            priceNote="No credit card required"
            features={FEATURES_FREE}
            cta={isAuthenticated ? 'Current Plan' : 'Get Started Free'}
            disabled={isAuthenticated && user?.plan === 'free'}
            onSelect={isAuthenticated ? undefined : onSignup}
          />
          <PlanCard
            title="Pro"
            price={billingPeriod === 'yearly' ? yearlyPrice : monthlyPrice}
            period={billingPeriod === 'yearly' ? 'year' : 'month'}
            priceNote={
              billingPeriod === 'yearly'
                ? `${yearlyPerMonth}/month — 2 months free vs monthly`
                : 'Less than one coffee a month'
            }
            features={FEATURES_PRO}
            cta={
              isAuthenticated
                ? user?.plan === 'pro' ? '✓ Current Plan' : 'Upgrade to Pro'
                : 'Start Pro Free Trial'
            }
            highlighted
            badge="Most Popular"
            disabled={isAuthenticated && user?.plan === 'pro'}
            onSelect={isAuthenticated ? () => {} : onSignup}
          />
        </div>

        {/* How it works */}
        <div className="mb-14">
          <h2 className="text-2xl font-black text-center mb-8" style={{ fontFamily: 'Barlow Condensed' }}>
            How it works
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                step: '01',
                title: 'We scan every 10 minutes',
                desc: 'AutoFlip monitors Cathcart Auto and Pic N Save around the clock — catching new listings the moment they go live.',
                icon: Clock,
              },
              {
                step: '02',
                title: 'AI analyses every vehicle',
                desc: 'Our AI reads the listing photos to detect damage, then calculates market value, repair costs, and Ontario fees automatically.',
                icon: Brain,
              },
              {
                step: '03',
                title: 'You get the profitable ones',
                desc: 'Deals are scored 1–10. BUY deals (8+) hit your inbox within minutes. You click the link and go see the car.',
                icon: TrendingUp,
              },
            ].map(({ step, title, desc, icon: Icon }) => (
              <div key={step} className="bg-card border border-border/50 rounded-sm p-5">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-3xl font-black text-primary/30 font-data leading-none">{step}</span>
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="font-bold mb-2">{title}</h3>
                <p className="text-sm text-muted-foreground">{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Trust / risk reduction */}
        <div className="flex flex-wrap justify-center gap-6 mb-14 text-sm text-muted-foreground">
          {[
            { icon: Shield, text: 'Cancel anytime — no contracts' },
            { icon: CheckCircle2, text: 'Ontario-specific data only' },
            { icon: Zap, text: 'Works while you sleep' },
          ].map(({ icon: Icon, text }) => (
            <div key={text} className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-emerald-500" />
              <span>{text}</span>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <div className="max-w-2xl mx-auto mb-14">
          <h2 className="text-2xl font-black text-center mb-6" style={{ fontFamily: 'Barlow Condensed' }}>
            Frequently asked questions
          </h2>
          <div className="space-y-3">
            {FAQ.map(({ q, a }) => (
              <div key={q} className="bg-card border border-border/50 rounded-sm p-4">
                <h4 className="font-semibold text-sm mb-1.5">{q}</h4>
                <p className="text-sm text-muted-foreground">{a}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Final CTA */}
        <div className="text-center bg-primary/5 border border-primary/20 rounded-sm p-8">
          <h2 className="text-2xl font-black mb-2" style={{ fontFamily: 'Barlow Condensed' }}>
            Stop missing profitable deals
          </h2>
          <p className="text-muted-foreground text-sm mb-6 max-w-md mx-auto">
            Ontario car flippers who use AutoFlip find BUY deals 10 minutes before anyone else sees them listed.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-3">
            <Button size="lg" onClick={onSignup} className="text-base px-8">
              Start for free <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            {!isAuthenticated && (
              <Button size="lg" variant="outline" onClick={onLogin} className="text-base px-8">
                Sign in
              </Button>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-3">No credit card required • Cancel anytime</p>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground mt-8">
          © {new Date().getFullYear()} AutoFlip Intelligence. Ontario, Canada.
        </p>
      </div>
    </div>
  );
}
