import { create } from 'zustand';

export const useAppStore = create((set, get) => ({
  listings: [],
  watchlist: [],
  portfolio: [],
  stats: null,
  settings: null,
  marketIntel: null,
  activePage: 'feed',
  selectedListing: null,
  filters: {
    source: '',
    min_price: '',
    max_price: '',
    min_score: '',
    damage_type: '',
    make: '',
    sort_by: 'deal_score',
    sort_order: 'desc',
  },
  wsConnected: false,

  setListings: (listings) => set({ listings }),
  setWatchlist: (watchlist) => set({ watchlist }),
  setPortfolio: (portfolio) => set({ portfolio }),
  setStats: (stats) => set({ stats }),
  setSettings: (settings) => set({ settings }),
  setMarketIntel: (marketIntel) => set({ marketIntel }),
  setActivePage: (activePage) => set({ activePage }),
  setSelectedListing: (selectedListing) => set({ selectedListing }),
  setFilters: (filters) => set((state) => ({ filters: { ...state.filters, ...filters } })),
  setWsConnected: (wsConnected) => set({ wsConnected }),

  addListing: (listing) => set((state) => ({
    listings: [listing, ...state.listings],
  })),
}));
