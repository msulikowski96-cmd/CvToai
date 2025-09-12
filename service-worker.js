// Service Worker for CV Optimizer Pro PWA
const CACHE_NAME = "cv-optimizer-pro-v1.0.0";
const urlsToCache = [
    "/",
    "/static/css/custom.css",
    "/static/js/main.js",
    "/static/manifest.json",
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css",
];

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.addAll(urlsToCache);
        }),
    );
});

self.addEventListener("fetch", function (event) {
    // Skip API requests and HEAD requests
    if (event.request.url.includes("/api") || event.request.method === "HEAD") {
        return;
    }

    event.respondWith(
        caches.match(event.request).then(function (response) {
            // Cache hit - return response
            if (response) {
                return response;
            }
            return fetch(event.request);
        }),
    );
});