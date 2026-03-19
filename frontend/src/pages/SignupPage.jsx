import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/AuthContext';
import { toast } from 'sonner';
import {
  Zap, Mail, Lock, Eye, EyeOff, ArrowRight, AlertCircle,
  User, CheckCircle2,
} from 'lucide-react';

const PERKS = [
  'New deals every 10 minutes — before anyone else',
  'AI damage detection on every vehicle',
  'Profit analysis with Ontario fees included',
  'Deal scoring so you know exactly what to buy',
];

export default function SignupPage({ onSuccess, switchToLogin, switchToPricing }) {
  const { register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Email and password are required.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    try {
      await register(email.trim(), password, name.trim());
      toast.success('Account created! Welcome to AutoFlip 🚗');
      onSuccess?.();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not create account. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const passwordStrength = (pw) => {
    if (!pw) return null;
    if (pw.length < 6) return { label: 'Too short', color: 'bg-red-500', width: '25%' };
    if (pw.length < 8) return { label: 'Weak', color: 'bg-amber-500', width: '50%' };
    if (/[A-Z]/.test(pw) && /\d/.test(pw)) return { label: 'Strong', color: 'bg-emerald-500', width: '100%' };
    return { label: 'Good', color: 'bg-blue-500', width: '75%' };
  };

  const strength = passwordStrength(password);

  return (
    <div className="min-h-screen bg-[#09090b] flex items-center justify-center px-4 py-8" data-testid="signup-page">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-10 h-10 bg-primary/20 rounded-sm">
              <Zap className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-base font-black tracking-tighter uppercase leading-none" style={{ fontFamily: 'Barlow Condensed' }}>
                AutoFlip
              </h1>
              <span className="text-[9px] text-muted-foreground tracking-[0.2em] uppercase">Intelligence</span>
            </div>
          </div>
        </div>

        {/* Card */}
        <div className="bg-card border border-border/50 rounded-sm p-6">
          <div className="mb-5">
            <h2 className="text-lg font-bold mb-1">Start finding profitable flips</h2>
            <p className="text-sm text-muted-foreground">Free account — upgrade anytime for unlimited alerts</p>
          </div>

          {/* Value props */}
          <div className="mb-5 space-y-1.5">
            {PERKS.map((perk) => (
              <div key={perk} className="flex items-start gap-2 text-xs text-muted-foreground">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0 mt-0.5" />
                <span>{perk}</span>
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error banner */}
            {error && (
              <div className="flex items-start gap-2 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded-sm text-sm text-red-400">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Name */}
            <div>
              <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">
                Your name <span className="normal-case">(optional)</span>
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="John Smith"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="pl-9 bg-background border-border/50"
                  autoComplete="name"
                  data-testid="name-input"
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9 bg-background border-border/50"
                  autoComplete="email"
                  data-testid="email-input"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Min. 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9 pr-9 bg-background border-border/50"
                  autoComplete="new-password"
                  data-testid="password-input"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {/* Strength meter */}
              {strength && (
                <div className="mt-1.5">
                  <div className="h-1 bg-secondary rounded-full overflow-hidden">
                    <div
                      className={`h-full ${strength.color} transition-all duration-300`}
                      style={{ width: strength.width }}
                    />
                  </div>
                  <p className={`text-[10px] mt-0.5 ${
                    strength.color === 'bg-red-500' ? 'text-red-400' :
                    strength.color === 'bg-amber-500' ? 'text-amber-400' :
                    strength.color === 'bg-blue-500' ? 'text-blue-400' : 'text-emerald-400'
                  }`}>{strength.label}</p>
                </div>
              )}
            </div>

            {/* Submit */}
            <Button
              type="submit"
              className="w-full"
              disabled={loading}
              data-testid="signup-submit"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Creating account...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  Create Free Account <ArrowRight className="h-4 w-4" />
                </span>
              )}
            </Button>

            <p className="text-[10px] text-muted-foreground text-center">
              By creating an account you agree to our terms. No credit card required.
            </p>
          </form>

          {/* Switch to login */}
          <p className="text-center text-sm text-muted-foreground mt-4">
            Already have an account?{' '}
            <button
              onClick={switchToLogin}
              className="text-primary hover:underline font-medium transition-colors"
              data-testid="switch-to-login"
            >
              Sign in
            </button>
          </p>
        </div>

        {/* Pricing note */}
        <p className="text-center text-xs text-muted-foreground mt-4">
          Free to browse •{' '}
          <button
            onClick={switchToPricing}
            className="text-primary hover:underline"
          >
            Upgrade for deal alerts
          </button>{' '}
          from $4.99/mo
        </p>
      </div>
    </div>
  );
}
