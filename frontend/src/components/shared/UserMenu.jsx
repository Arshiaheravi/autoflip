/**
 * UserMenu — shows login/signup buttons when logged out,
 * user avatar + dropdown when logged in.
 */
import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/AuthContext';
import { User, LogOut, ChevronDown, Crown, Zap } from 'lucide-react';

export default function UserMenu({ onLogin, onSignup, onPricing }) {
  const { user, isAuthenticated, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  if (!isAuthenticated) {
    return (
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={onLogin}
          className="text-xs text-muted-foreground hover:text-foreground"
          data-testid="login-btn"
        >
          Sign In
        </Button>
        <Button
          size="sm"
          onClick={onPricing}
          className="text-xs"
          data-testid="signup-btn"
        >
          <Zap className="h-3 w-3 mr-1" />
          Get Pro
        </Button>
      </div>
    );
  }

  const initial = (user?.name || user?.email || '?')[0].toUpperCase();
  const isPro = user?.plan === 'pro';

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2 py-1 rounded-sm hover:bg-secondary/50 transition-all"
        data-testid="user-menu-btn"
      >
        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
          isPro ? 'bg-primary/30 text-primary' : 'bg-secondary text-muted-foreground'
        }`}>
          {initial}
        </div>
        {isPro && <Crown className="h-3 w-3 text-amber-400" />}
        <ChevronDown className={`h-3 w-3 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-card border border-border/50 rounded-sm shadow-xl z-50">
          {/* User info */}
          <div className="px-3 py-2.5 border-b border-border/30">
            <p className="text-xs font-semibold truncate">{user?.name || 'User'}</p>
            <p className="text-[10px] text-muted-foreground truncate">{user?.email}</p>
            <span className={`inline-flex items-center gap-1 mt-1 text-[9px] px-1.5 py-0.5 rounded-sm ${
              isPro ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground'
            }`}>
              {isPro ? <Crown className="h-2.5 w-2.5" /> : <User className="h-2.5 w-2.5" />}
              {isPro ? 'Pro' : 'Free'} plan
            </span>
          </div>

          {/* Upgrade CTA for free users */}
          {!isPro && (
            <div className="px-3 py-2 border-b border-border/30">
              <button
                onClick={() => { setOpen(false); onPricing?.(); }}
                className="w-full text-left text-xs text-primary hover:text-primary/80 flex items-center gap-1.5 transition-colors"
              >
                <Crown className="h-3.5 w-3.5" />
                Upgrade to Pro →
              </button>
            </div>
          )}

          {/* Logout */}
          <div className="p-1">
            <button
              onClick={() => { setOpen(false); logout(); }}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-secondary/50 rounded-sm transition-all"
              data-testid="logout-btn"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
