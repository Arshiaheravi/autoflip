import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API, headers: { 'Content-Type': 'application/json' } });

export const listingsApi = {
  getAll: (params = {}) => api.get('/listings', { params }),
  getOne: (id) => api.get(`/listings/${id}`),
  getPriceHistory: (id) => api.get(`/listings/${id}/price-history`),
};

export const statsApi = {
  get: () => api.get('/stats'),
};

export const scrapeApi = {
  trigger: () => api.post('/scrape'),
  status: () => api.get('/scrape-status'),
  history: () => api.get('/scan-history'),
};

export const settingsApi = {
  get: () => api.get('/settings'),
  update: (data) => api.put('/settings', data),
};

export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
};

export default api;
