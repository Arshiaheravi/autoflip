import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/AuthContext';
import { toast } from 'sonner';
import { Zap, Mail, Lock, Eye, EyeOff, ArrowRight, AlertCircle } from 'lucide-react';

export default function LoginPage({ onSuccess, switchToSignup }) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);
    try {
      await login(email.trim(), password);
      toast.success('Welcome back!');
      onSuccess?.();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Invalid email or password.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#09090b] flex items-center justify-center px-4" data-testid="login-page">
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
          <div className="mb-6">
            <h2 className="text-lg font-bold mb-1">Sign in to your account</h2>
            <p className="text-sm text-muted-foreground">Access your deal intelligence dashboard</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error banner */}
            {error && (
              <div className="flex items-start gap-2 px-3 py-2.5 bg-red-500/10 border border-red-500/20 rounded-sm text-sm text-red-400">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

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
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9 pr-9 bg-background border-border/50"
                  autoComplete="current-password"
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
            </div>

            {/* Submit */}
            <Button
              type="submit"
              className="w-full"
              disabled={loading}
              data-testid="login-submit"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Signing in...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  Sign In <ArrowRight className="h-4 w-4" />
                </span>
              )}
            </Button>
          </form>

          {/* Switch to signup */}
          <p className="text-center text-sm text-muted-foreground mt-5">
            Don't have an account?{' '}
            <button
              onClick={switchToSignup}
              className="text-primary hover:underline font-medium transition-colors"
              data-testid="switch-to-signup"
            >
              Create one free
            </button>
          </p>
        </div>

        {/* Social proof */}
        <p className="text-center text-xs text-muted-foreground mt-4">
          Ontario's #1 car flip intelligence platform
        </p>
      </div>
    </div>
  );
}
