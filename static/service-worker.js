
const CACHE_NAME = 'cv-optimizer-v1.2';
const urlsToCache = [
  '/',
  '/static/css/custom.css',
  '/static/js/main.js',
  '/static/manifest.json'
];

self.addEventListener('install', function(event) {
  console.log('SW: Installing version', CACHE_NAME);
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('SW: Cache opened successfully');
        // Nie cache'uj wszystkich plików od razu - tylko podstawowe
        return cache.addAll(['/']);
      })
      .catch(function(error) {
        console.error('SW: Cache installation failed:', error);
        // Nie blokuj instalacji jeśli cache nie działa
      })
  );
  // Wymusz aktywację nowego SW
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  console.log('SW: Activating new version');
  event.waitUntil(
    Promise.all([
      // Wyczyść stare cache
      caches.keys().then(function(cacheNames) {
        return Promise.all(
          cacheNames.map(function(cacheName) {
            if (cacheName !== CACHE_NAME) {
              console.log('SW: Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      // Przejmij kontrolę nad wszystkimi klientami
      self.clients.claim()
    ])
  );
});

self.addEventListener('fetch', function(event) {
  // Ignoruj zapytania spoza HTTP/HTTPS
  if (!event.request.url.startsWith('http')) {
    return;
  }

  // Ignoruj zapytania do API (zawsze pobieraj ze sieci)
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('/optimize-cv') ||
      event.request.url.includes('/upload-cv')) {
    return;
  }

  // Strategia Network First dla głównych plików
  event.respondWith(
    fetch(event.request)
      .then(function(response) {
        // Jeśli sieć działa, zapisz w cache i zwróć odpowiedź
        if (response && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME)
            .then(function(cache) {
              cache.put(event.request, responseClone);
            })
            .catch(function(error) {
              console.warn('SW: Cache put failed:', error);
            });
        }
        return response;
      })
      .catch(function(error) {
        console.log('SW: Network failed, trying cache:', error);
        // Jeśli sieć nie działa, spróbuj z cache
        return caches.match(event.request)
          .then(function(response) {
            if (response) {
              return response;
            }
            // Jeśli nie ma w cache, zwróć podstawową odpowiedź
            return new Response('Aplikacja nie jest dostępna offline', {
              status: 503,
              statusText: 'Service Unavailable',
              headers: { 'Content-Type': 'text/plain; charset=utf-8' }
            });
          });
      })
  );
});

// Obsługa wiadomości od głównej aplikacji
self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
