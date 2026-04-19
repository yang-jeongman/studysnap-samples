// Service Worker for Election Pamphlet PWA
// - Caches pages (network-first)
// - Handles Web Push events
// - Shows notifications with image attachment and action buttons

const CACHE_NAME = 'election-pamphlet-v2';

self.addEventListener('install', event => {
  console.log('[SW] Install');
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  console.log('[SW] Activate');
  event.waitUntil(
    caches.keys().then(names =>
      Promise.all(names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  // Only cache GET requests
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request)
      .then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

// === Push event (from admin backend via webpush) ===
self.addEventListener('push', event => {
  console.log('[SW] Push received');
  let data = {
    title: '선거공보물 알림',
    body: '새로운 소식이 있습니다.',
  };

  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body || '',
    icon: data.icon || '/studysnap-samples/election/minjoo/pwa/jeong_w-192.png',
    badge: data.badge || data.icon || '/studysnap-samples/election/minjoo/pwa/jeong_w-192.png',
    image: data.image || undefined,   // big image attachment
    vibrate: [200, 100, 200],
    requireInteraction: !!data.image,
    data: {
      url: data.url || self.registration.scope,
      action_label: data.action_label
    },
    actions: data.actions || [
      { action: 'open', title: data.action_label || '확인하기' }
    ],
    tag: data.tag || 'election-message-' + Date.now()
  };

  event.waitUntil(
    self.registration.showNotification(data.title || '선거공보물 알림', options)
  );
});

self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification clicked', event.action);
  event.notification.close();

  const url = (event.notification.data && event.notification.data.url)
    ? event.notification.data.url
    : '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(windowClients => {
        for (const client of windowClients) {
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }
        return clients.openWindow(url);
      })
  );
});

// Handle pushsubscriptionchange (Chrome re-subscribes)
self.addEventListener('pushsubscriptionchange', event => {
  console.log('[SW] Subscription changed, re-subscribe needed');
});
