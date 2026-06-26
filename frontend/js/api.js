/**
 * api.js – All kommunikasjon med Guleed Spareparts API.
 */

// Use the same origin the page was served from (e.g. http://127.0.0.1:8000),
// falling back to localhost when the HTML is opened directly as a file://.
const API_BASE = window.location.origin.startsWith('http')
  ? window.location.origin
  : 'http://localhost:8000';

// The downloadable desktop app runs against a server on this same PC, which is
// always reachable regardless of internet/wifi. So the offline queue + banner
// (meant for the cloud website) don't apply here.
const IS_LOCAL = ['localhost', '127.0.0.1'].includes(window.location.hostname);

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

// fetch() throws a TypeError when the network is unreachable (offline).
function isNetworkError(err) {
  return err instanceof TypeError;
}

async function doFetch(method, path, body, isFormData) {
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

// GET requests are cached so the app can still show data offline.
async function request(method, path, body = null, isFormData = false) {
  if (method === 'GET') {
    try {
      const data = await doFetch(method, path, body, isFormData);
      try { localStorage.setItem('cache:' + path, JSON.stringify(data)); } catch (e) {}
      return data;
    } catch (err) {
      if (isNetworkError(err)) {
        const cached = localStorage.getItem('cache:' + path);
        if (cached !== null) return JSON.parse(cached);
      }
      throw err;
    }
  }
  return doFetch(method, path, body, isFormData);
}

// ─── Offline write queue (orders & credit sales) ─────────────────────
const QUEUE_KEY = 'gs_sync_queue';
const getQueue = () => { try { return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]'); } catch (e) { return []; } };
const setQueue = (q) => localStorage.setItem(QUEUE_KEY, JSON.stringify(q));

// Try the request; if the network is down, store it and replay later.
async function requestQueued(method, path, body, label) {
  if (IS_LOCAL) return doFetch(method, path, body, false);  // local server is always there
  try {
    return await doFetch(method, path, body, false);
  } catch (err) {
    if (isNetworkError(err)) {
      const q = getQueue();
      q.push({ method, path, body, label, ts: new Date().getTime() });
      setQueue(q);
      updateBanner();
      return { _queued: true };
    }
    throw err;  // a real validation/HTTP error – surface it
  }
}

async function flushQueue() {
  if (!navigator.onLine) { updateBanner(); return; }
  const q = getQueue();
  if (!q.length) { updateBanner(); return; }
  const kept = [];
  let synced = 0, stopped = false;
  for (const entry of q) {
    if (stopped) { kept.push(entry); continue; }
    try {
      const result = await doFetch(entry.method, entry.path, entry.body, false);
      // undefined means the session expired (doFetch is redirecting to login) –
      // keep the item so it syncs after re-login instead of being lost.
      if (result === undefined) { stopped = true; kept.push(entry); continue; }
      synced++;
    } catch (err) {
      if (isNetworkError(err)) { stopped = true; kept.push(entry); }      // still offline
      else { offlineToast(`A queued ${entry.label || 'change'} could not sync: ${err.message}`, 'error'); }
    }
  }
  setQueue(kept);
  updateBanner();
  if (synced > 0) {
    offlineToast(`Synced ${synced} offline change${synced === 1 ? '' : 's'}`, 'success');
    window.dispatchEvent(new CustomEvent('gs-synced'));
  }
}

// ─── Status banner + lightweight toast ───────────────────────────────
function updateBanner() {
  if (IS_LOCAL) return;            // the desktop app is always "online" locally
  if (!document.body) return;
  let el = document.getElementById('gs-offline-banner');
  if (!el) {
    el = document.createElement('div');
    el.id = 'gs-offline-banner';
    el.className = 'offline-banner';
    document.body.appendChild(el);
  }
  const pending = getQueue().length;
  const offline = !navigator.onLine;
  if (!offline && pending === 0) { el.style.display = 'none'; return; }
  el.style.display = 'flex';
  el.classList.toggle('syncing', !offline && pending > 0);
  el.textContent = offline
    ? (pending ? `Offline · ${pending} change${pending === 1 ? '' : 's'} waiting to sync`
               : 'Offline · changes are saved on this device')
    : `Syncing ${pending} change${pending === 1 ? '' : 's'}…`;
}

function offlineToast(msg, type = 'info') {
  const c = document.getElementById('toast-container');
  if (!c) return;
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), 4000);
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
    return requestQueued('POST', '/api/orders/', data, 'order');
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
    return requestQueued('POST', '/api/loans/', data, 'credit sale');
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

  // ─── User management (admin only) ────────────────────────────────
  async getUsers(includeInactive = false) {
    return request('GET', `/api/auth/users?include_inactive=${includeInactive ? 'true' : 'false'}`);
  },

  async createUser(data) {
    return request('POST', '/api/auth/register', data);
  },

  async updateUser(id, data) {
    return request('PUT', `/api/auth/users/${id}`, data);
  },

  // How many offline changes are waiting to sync (for the UI)
  pendingSyncCount() {
    return getQueue().length;
  },
};

// ─── Offline wiring: service worker + auto-sync + status ─────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
}
window.addEventListener('online', () => { updateBanner(); flushQueue(); });
window.addEventListener('offline', updateBanner);
window.addEventListener('load', () => { updateBanner(); flushQueue(); });
