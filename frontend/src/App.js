import { useState } from 'react';
import '@/App.css';
import { Toaster } from '@/components/ui/sonner';
import NavBar from '@/components/shared/NavBar';
import Dashboard from '@/pages/Dashboard';
import AboutPage from '@/pages/AboutPage';
import SettingsPage from '@/pages/SettingsPage';
import LoginPage from '@/pages/LoginPage';
import SignupPage from '@/pages/SignupPage';
import PricingPage from '@/pages/PricingPage';
import { LanguageProvider, useLanguage } from '@/lib/LanguageContext';
import { AuthProvider, useAuth } from '@/lib/AuthContext';

function AppInner() {
  const [page, setPage] = useState('dashboard');
  const [authModal, setAuthModal] = useState(null); // 'login' | 'signup' | 'pricing' | null
  const { lang } = useLanguage();
  const { loading } = useAuth();

  // Show full-screen overlay pages
  const showPricing = authModal === 'pricing';
  const showLogin = authModal === 'login';
  const showSignup = authModal === 'signup';

  const handleAuthSuccess = () => {
    setAuthModal(null);
  };

  // Loading screen while we validate the stored JWT
  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <span className="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    );
  }

  // Full-screen overlay pages (auth / pricing)
  if (showPricing) {
    return (
      <>
        <PricingPage
          onSignup={() => setAuthModal('signup')}
          onLogin={() => setAuthModal('login')}
          onClose={() => setAuthModal(null)}
        />
        <Toaster position="bottom-right" theme="dark" />
      </>
    );
  }

  if (showLogin) {
    return (
      <div dir={lang === 'fa' ? 'rtl' : 'ltr'}>
        <LoginPage
          onSuccess={handleAuthSuccess}
          switchToSignup={() => setAuthModal('signup')}
        />
        <Toaster position="bottom-right" theme="dark" />
      </div>
    );
  }

  if (showSignup) {
    return (
      <div dir={lang === 'fa' ? 'rtl' : 'ltr'}>
        <SignupPage
          onSuccess={handleAuthSuccess}
          switchToLogin={() => setAuthModal('login')}
          switchToPricing={() => setAuthModal('pricing')}
        />
        <Toaster position="bottom-right" theme="dark" />
      </div>
    );
  }

  // Main app
  return (
    <div className="App min-h-screen grid-bg" dir={lang === 'fa' ? 'rtl' : 'ltr'}>
      <NavBar
        page={page}
        setPage={setPage}
        onLogin={() => setAuthModal('login')}
        onSignup={() => setAuthModal('signup')}
        onPricing={() => setAuthModal('pricing')}
      />
      {page === 'dashboard' && <Dashboard />}
      {page === 'about' && <AboutPage />}
      {page === 'settings' && <SettingsPage />}
      <Toaster position="bottom-right" theme="dark" />
    </div>
  );
}

function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <AppInner />
      </AuthProvider>
    </LanguageProvider>
  );
}

export default App;
