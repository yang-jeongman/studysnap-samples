// 여의도순복음교회 모바일 주보 — Service Worker
// 캐시 전략:
//   - HTML / 동적 콘텐츠: Network-first (최신 우선, 오프라인 폴백)
//   - 정적 자원 (이미지/아이콘/manifest): Cache-first
const CACHE = 'jubo-v2';
const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './cover.jpg',
  './choir.jpg',
  './icon-192.png',
  './icon-512.png',
  './assets/icons/church_logo.jpg',
  './assets/icons/youtube.jpg',
  './assets/icons/instagram.jpg',
  './assets/icons/kakao.jpg',
];

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE).then(function(c) {
      // 일부 자원이 404 여도 install 실패하지 않도록 개별 fetch
      return Promise.all(STATIC_ASSETS.map(function(url) {
        return c.add(url).catch(function(err) {
          console.warn('[SW] 캐시 실패:', url, err.message);
        });
      }));
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(ks) {
      return Promise.all(ks.filter(function(k) { return k !== CACHE; }).map(function(k) {
        return caches.delete(k);
      }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function(e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);

  // /api/ 경로 (성경 본문 / 찬송가) — Network-first 후 폴백 없음 (실시간 데이터)
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(fetch(req).catch(function() {
      return new Response(JSON.stringify({error: 'offline'}), {
        headers: {'Content-Type': 'application/json'}, status: 503
      });
    }));
    return;
  }

  // HTML — Network-first, 실패 시 캐시 → 캐시도 없으면 index.html
  if (req.mode === 'navigate' || (req.headers.get('accept') || '').indexOf('text/html') >= 0) {
    e.respondWith(
      fetch(req).then(function(resp) {
        var copy = resp.clone();
        caches.open(CACHE).then(function(c) { c.put(req, copy); });
        return resp;
      }).catch(function() {
        return caches.match(req).then(function(r) { return r || caches.match('./index.html'); });
      })
    );
    return;
  }

  // 그 외 (이미지/CSS/JS) — Cache-first
  e.respondWith(
    caches.match(req).then(function(r) {
      return r || fetch(req).then(function(resp) {
        if (resp && resp.status === 200 && resp.type === 'basic') {
          var copy = resp.clone();
          caches.open(CACHE).then(function(c) { c.put(req, copy); });
        }
        return resp;
      });
    })
  );
});
