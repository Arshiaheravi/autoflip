import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API,
  headers: { 'Content-Type': 'application/json' },
});

export const listingsApi = {
  getAll: (params = {}) => api.get('/listings', { params }),
  getOne: (id) => api.get(`/listings/${id}`),
  getPhotos: (id) => api.get(`/listings/${id}/photos`),
  getAnalysis: (id) => api.get(`/listings/${id}/analysis`),
  create: (data) => api.post('/listings', data),
  analyze: (id) => api.post(`/listings/${id}/analyze`),
  recalculate: (id) => api.post(`/listings/${id}/recalculate`),
};

export const watchlistApi = {
  getAll: () => api.get('/watchlist'),
  add: (data) => api.post('/watchlist', data),
  update: (id, data) => api.put(`/watchlist/${id}`, data),
  remove: (id) => api.delete(`/watchlist/${id}`),
};

export const portfolioApi = {
  getAll: () => api.get('/portfolio'),
  create: (data) => api.post('/portfolio', data),
  update: (id, data) => api.put(`/portfolio/${id}`, data),
  remove: (id) => api.delete(`/portfolio/${id}`),
};

export const statsApi = {
  get: () => api.get('/stats'),
};

export const marketApi = {
  get: (make, model) => api.get(`/market/${make}/${model}`),
  getIntelligence: () => api.get('/market-intelligence'),
};

export const settingsApi = {
  get: () => api.get('/settings'),
  update: (data) => api.put('/settings', data),
  testNotify: () => api.post('/settings/test-notify'),
};

export default api;
