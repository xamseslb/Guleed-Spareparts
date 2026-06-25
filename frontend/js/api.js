/**
 * api.js – All kommunikasjon med Guleed Spareparts API.
 */

// Use the same origin the page was served from (e.g. http://127.0.0.1:8000),
// falling back to localhost when the HTML is opened directly as a file://.
const API_BASE = window.location.origin.startsWith('http')
  ? window.location.origin
  : 'http://localhost:8000';

function getToken() {
  return localStorage.getItem('gs_token');
}

function getHeaders(extra = {}) {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function request(method, path, body = null, isFormData = false) {
  const headers = isFormData
    ? { 'Authorization': `Bearer ${getToken()}` }
    : getHeaders();

  const options = { method, headers };
  if (body && !isFormData) options.body = JSON.stringify(body);
  if (body && isFormData) options.body = body;

  const res = await fetch(`${API_BASE}${path}`, options);

  if (res.status === 401) {
    localStorage.removeItem('gs_token');
    localStorage.removeItem('gs_user');
    window.location.href = 'login.html';
    return;
  }

  if (res.status === 204) return null;

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Error: ${res.status}`);
  return data;
}

// ─── Auth ──────────────────────────────────────────────────────────
export const api = {
  async login(username, password) {
    const form = new URLSearchParams({ username, password });
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Innlogging feilet');
    return data;
  },

  // ─── Parts ──────────────────────────────────────────────────────
  async getParts({ q, category, car_make, car_model, low_stock_only } = {}) {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (category) params.set('category', category);
    if (car_make) params.set('car_make', car_make);
    if (car_model) params.set('car_model', car_model);
    if (low_stock_only) params.set('low_stock_only', 'true');
    return request('GET', `/api/parts/?${params}`);
  },

  async getPart(id) {
    return request('GET', `/api/parts/${id}`);
  },

  async createPart(data) {
    return request('POST', '/api/parts/', data);
  },

  async updatePart(id, data) {
    return request('PUT', `/api/parts/${id}`, data);
  },

  async deletePart(id) {
    return request('DELETE', `/api/parts/${id}`);
  },

  async uploadImage(partId, file) {
    const formData = new FormData();
    formData.append('file', file);
    return request('POST', `/api/parts/${partId}/images`, formData, true);
  },

  async deleteImage(partId, imageIndex) {
    return request('DELETE', `/api/parts/${partId}/images/${imageIndex}`);
  },

  // ─── Orders ─────────────────────────────────────────────────────
  async getOrder(id) {
    return request('GET', `/api/orders/${id}`);
  },

  async getOrders(filters = {}) {
    const params = new URLSearchParams(filters);
    return request('GET', `/api/orders/?${params}`);
  },

  async createOrder(data) {
    return request('POST', '/api/orders/', data);
  },

  async updateOrder(id, data) {
    return request('PUT', `/api/orders/${id}`, data);
  },

  async deleteOrder(id) {
    return request('DELETE', `/api/orders/${id}`);
  },

  // ─── Customers ──────────────────────────────────────────────────
  async getCustomers() {
    return request('GET', '/api/customers/');
  },

  async getCustomer(id) {
    return request('GET', `/api/customers/${id}`);
  },

  async createCustomer(data) {
    return request('POST', '/api/customers/', data);
  },

  async updateCustomer(id, data) {
    return request('PUT', `/api/customers/${id}`, data);
  },

  async deleteCustomer(id) {
    return request('DELETE', `/api/customers/${id}`);
  },

  // ─── Analytics ──────────────────────────────────────────────────
  async getSummary() {
    return request('GET', '/api/analytics/summary');
  },

  async getLowStock() {
    return request('GET', '/api/analytics/low-stock');
  },

  async getCategoryStats() {
    return request('GET', '/api/analytics/categories');
  },

  async getOrderTrend(days = 30) {
    return request('GET', `/api/analytics/order-trend?days=${days}`);
  },

  // ─── Loans ──────────────────────────────────────────────────────
  async getLoans(filters = {}) {
    const params = new URLSearchParams(filters);
    return request('GET', `/api/loans/?${params}`);
  },

  async getLoan(id) {
    return request('GET', `/api/loans/${id}`);
  },

  async createLoan(data) {
    return request('POST', '/api/loans/', data);
  },

  async updateLoan(id, data) {
    return request('PUT', `/api/loans/${id}`, data);
  },

  // Mark a loan as returned – updates stock automatically on the backend
  async returnLoan(id) {
    return request('POST', `/api/loans/${id}/return`);
  },

  async deleteLoan(id) {
    return request('DELETE', `/api/loans/${id}`);
  },

  // ─── Employees (used in loan registration dropdown) ──────────────
  // Fetches all users from the auth/me endpoint list
  async getEmployees() {
    return request('GET', '/api/auth/users');
  },
};
