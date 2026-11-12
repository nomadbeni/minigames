// Offline gyorsítótár a startlaphoz és minden játékhoz: egyszer kell megnyitni, utána internet nélkül is indul.
// Csak az oldal saját, előre felsorolt fájljait tárolja. Más helyre nem küld és onnan nem kér semmit.
// A FILES és a CACHE sort a tools/build_site.py tölti ki közzétételkor (a tárolóban üres).
var CACHE = 'jatektar-dev';
var FILES = [];

self.addEventListener('install', function (e) {
  // cache: 'reload' – a friss változatot tárolja, ne a böngésző korábbi példányát
  e.waitUntil(caches.open(CACHE).then(function (c) {
    return c.addAll(FILES.map(function (f) { return new Request(f, { cache: 'reload' }); }));
  }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k.indexOf('jatektar-') === 0 && k !== CACHE; })
        .map(function (k) { return caches.delete(k); }));
    })
  );
  self.clients.claim();
});

// Csak a felsorolt saját fájlokat szolgálja ki a gyorsítótárból. Minden más kérést a böngésző
// a szokásos módon intéz (a saját gyorsítótárral rendelkező Cornhole pontozót is).
self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  var url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  var base = new URL('./', self.location.href).pathname;
  if (url.pathname.indexOf(base) !== 0) return;
  var rel = url.pathname.slice(base.length);
  if (rel === '' || rel.slice(-1) === '/') rel += 'index.html';
  if (FILES.indexOf(rel) < 0) return;
  var key = new URL(rel, self.location.href).href;
  e.respondWith(
    caches.open(CACHE).then(function (c) {
      return c.match(key).then(function (hit) {
        // Ha a gyorsítótárból hiányzik, a saját fájlt újra eltárolja, majd azt adja vissza.
        return hit || c.add(key).then(function () { return c.match(key); });
      });
    })
  );
});

// Új változatra csak akkor vált, ha a startlapon a felhasználó a Frissítés gombra koppint.
self.addEventListener('message', function (e) {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});
