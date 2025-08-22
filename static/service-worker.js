const CACHE_NAME = 'cv-optimizer-v1';
const urlsToCache = [
  '/',
  '/static/css/custom.css',
  '/static/js/main.js'
];

self.addEventListener('install', function(event) {
  console.log('SW: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('SW: Cache opened');
        return cache.addAll(urlsToCache);
      })
      .catch(function(error) {
        console.error('SW: Cache installation failed:', error);
      })
  );
});

self.addEventListener('fetch', function(event) {
  // Ignoruj zapytania chrome-extension i inne nieobsługiwane protokoły
  if (!event.request.url.startsWith('http')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        if (response) {
          return response;
        }
        return fetch(event.request).catch(function(error) {
          console.log('SW: Fetch failed:', error);
          // Zwróć podstawową odpowiedź w przypadku błędu
          return new Response('Offline content not available', {
            status: 200,
            statusText: 'OK'
          });
        });
      })
      .catch(function(error) {
        console.error('SW: Response error:', error);
        return new Response('Service unavailable', {
          status: 503,
          statusText: 'Service Unavailable'
        });
      })
  );
});