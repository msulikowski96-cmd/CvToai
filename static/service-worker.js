const CACHE_NAME = 'cv-optimizer-v1';
const urlsToCache = [
  '/',
  '/static/css/custom.css',
  '/static/js/main.js'
];

self.addEventListener('install', function(event) {
  console.log('Service Worker installing...');
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  console.log('Service Worker activating...');
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', function(event) {
  // For now, just pass through all requests
  event.respondWith(
    fetch(event.request).catch(function() {
      // Fallback in case of network error
      return new Response('Offline');
    })
  );
});