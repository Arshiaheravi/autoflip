import { useEffect, useRef } from 'react';
import '@/App.css';
import { useAppStore } from '@/lib/store';
import AppLayout from '@/components/AppLayout';
import LiveFeed from '@/pages/LiveFeed';
import Watchlist from '@/pages/Watchlist';
import Portfolio from '@/pages/Portfolio';
import MarketIntel from '@/pages/MarketIntel';
import SettingsPage from '@/pages/Settings';
import { Toaster } from '@/components/ui/sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const { activePage, setWsConnected, addListing } = useAppStore();
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);

  useEffect(() => {
    const connectWs = () => {
      try {
        const wsUrl = BACKEND_URL.replace(/^http/, 'ws') + '/ws/listings';
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsConnected(true);
          // Heartbeat
          const interval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) ws.send('ping');
          }, 30000);
          ws._heartbeat = interval;
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'new_listing') {
              addListing(msg.data);
            }
          } catch (e) {}
        };

        ws.onclose = () => {
          setWsConnected(false);
          if (ws._heartbeat) clearInterval(ws._heartbeat);
          reconnectRef.current = setTimeout(connectWs, 5000);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch (e) {
        reconnectRef.current = setTimeout(connectWs, 5000);
      }
    };

    connectWs();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [setWsConnected, addListing]);

  const renderPage = () => {
    switch (activePage) {
      case 'feed': return <LiveFeed />;
      case 'watchlist': return <Watchlist />;
      case 'portfolio': return <Portfolio />;
      case 'market': return <MarketIntel />;
      case 'settings': return <SettingsPage />;
      default: return <LiveFeed />;
    }
  };

  return (
    <div className="App">
      <AppLayout>
        {renderPage()}
      </AppLayout>
      <Toaster position="bottom-right" theme="dark" />
    </div>
  );
}

export default App;
