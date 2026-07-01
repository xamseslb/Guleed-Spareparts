/* Service worker – makes the app shell available offline.
   Strategy: stale-while-revalidate for the shell – serve the cached page
   instantly (no white screen while the server wakes up), then refresh the
   cache in the background so the next load is up to date. API data is cached
   separately by api.js in localStorage; we deliberately don't cache /api/. */

const CACHE = 'guleed-v10';
const SHELL = [
  './login.html',
  './index.html',
  './parts.html',
  './orders.html',
  './customers.html',
  './loans.html',
  './users.html',
  './activity.html',
  './sales.html',
  './css/style.css',
  './js/api.js',
  './js/app.js',
  './js/combobox.js',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png',
  './icons/favicon.png',
  './img/logo.png',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;              // writes are handled by api.js's offline queue
  const url = new URL(req.url);
  if (url.pathname.startsWith('/api/')) return;  // data is cached by api.js, not here

  // Stale-while-revalidate: serve the cached shell instantly (so there's no
  // white screen even when the server is asleep/waking up), then refresh the
  // cache in the background for next time.
  e.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => cached || caches.match('./login.html'));
      return cached || network;
    })
  );
});
