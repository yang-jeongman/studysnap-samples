// Service Worker for Election Pamphlet PWA
const CACHE_NAME = 'election-pamphlet-v1';

// Install event
self.addEventListener('install', event => {
  console.log('[SW] Install');
  self.skipWaiting();
});

// Activate event
self.addEventListener('activate', event => {
  console.log('[SW] Activate');
  event.waitUntil(
    caches.keys().then(names =>
      Promise.all(
        names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', event => {
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

// Push event
self.addEventListener('push', event => {
  console.log('[SW] Push received');
  let data = { title: '선거공보물 알림', body: '새로운 소식이 있습니다.', icon: '' };

  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: data.icon || '/studysnap-samples/election/minjoo/pwa/jeong_w-192.png',
    badge: data.badge || '/studysnap-samples/election/minjoo/pwa/jeong_w-192.png',
    vibrate: [200, 100, 200],
    data: {
      url: data.url || self.registration.scope
    },
    actions: data.actions || [
      { action: 'open', title: '확인하기' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification click event
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification clicked');
  event.notification.close();

  const url = event.notification.data && event.notification.data.url
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
