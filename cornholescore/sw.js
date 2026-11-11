// Egyszerű offline gyorsítótár: az app internet nélkül is indul.
var CACHE = 'cornhole-v10';
var FILES = ['./', './index.html', './manifest.json', './icon.svg', './icon-192.png', './icon-512.png'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(FILES); }));

});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    })
  );
  self.clients.claim();
});

// Csak az app saját, előre eltárolt fájljait szolgálja ki a gyorsítótárból.
// Minden más kérést a böngésző a szokásos módon intéz, a service worker nem kér le semmit.
self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  var url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  var base = new URL('./', self.location.href).pathname;
  var rel = './' + url.pathname.slice(base.length);
  if (url.pathname.indexOf(base) !== 0 || FILES.indexOf(rel === './' ? './' : rel) < 0) return;
  e.respondWith(
    caches.open(CACHE).then(function (c) {
      return c.match(e.request, { ignoreSearch: true }).then(function (hit) {
        // Ha a gyorsítótárból hiányzik, a saját fájlt újra eltárolja, majd azt adja vissza.
        return hit || c.add(e.request).then(function () { return c.match(e.request, { ignoreSearch: true }); });
      });
    })
  );
});

self.addEventListener('message', function (event) {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});
