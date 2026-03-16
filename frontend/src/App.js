import { useState } from 'react';
import '@/App.css';
import { Toaster } from '@/components/ui/sonner';
import NavBar from '@/components/shared/NavBar';
import Dashboard from '@/pages/Dashboard';
import AboutPage from '@/pages/AboutPage';
import SettingsPage from '@/pages/SettingsPage';
import { LanguageProvider, useLanguage } from '@/lib/LanguageContext';

function AppInner() {
  const [page, setPage] = useState('dashboard');
  const { lang } = useLanguage();

  return (
    <div className="App min-h-screen grid-bg" dir={lang === 'fa' ? 'rtl' : 'ltr'}>
      <NavBar page={page} setPage={setPage} />
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
      <AppInner />
    </LanguageProvider>
  );
}

export default App;
