
const CACHE_NAME = "cv-optimizer-v1.0.0";
const STATIC_CACHE = "cv-optimizer-static-v1.0.0";
const RUNTIME_CACHE = "cv-optimizer-runtime-v1.0.0";

// Updated assets to cache on install
const STATIC_ASSETS = [
    "/",
    "/manifest.json",
    "/static/css/custom.css",
    "/static/js/main.js",
    "/icons/icon-512.png",
    "/static/icon-192.png",
    "/static/icon-32.png",
    "/static/icon-16.png",
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css",
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
];

// API endpoints that should not be cached
const NO_CACHE_PATHS = ["/upload-cv", "/optimize-cv", "/health", "/api/"];

self.addEventListener("install", (event) => {
    console.log("[SW] Install event");

    event.waitUntil(
        caches
            .open(STATIC_CACHE)
            .then((cache) => {
                console.log("[SW] Pre-caching static assets");
                return cache.addAll(
                    STATIC_ASSETS.map(
                        (url) =>
                            new Request(url, {
                                mode: "cors",
                                credentials: "omit",
                            }),
                    ),
                );
            })
            .catch((error) => {
                console.error("[SW] Error pre-caching static assets:", error);
            }),
    );

    // Force the waiting service worker to become the active service worker
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    console.log("[SW] Activate event");

    event.waitUntil(
        caches
            .keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((cacheName) => {
                            // Delete old caches
                            return (
                                cacheName !== STATIC_CACHE &&
                                cacheName !== RUNTIME_CACHE &&
                                cacheName.startsWith("cv-optimizer-")
                            );
                        })
                        .map((cacheName) => {
                            console.log("[SW] Deleting old cache:", cacheName);
                            return caches.delete(cacheName);
                        }),
                );
            })
            .then(() => {
                // Take control of all clients immediately
                return self.clients.claim();
            }),
    );
});

self.addEventListener("fetch", (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== "GET") {
        return;
    }

    // Skip API endpoints that shouldn't be cached
    if (NO_CACHE_PATHS.some((path) => url.pathname.startsWith(path))) {
        return;
    }

    // Handle different types of requests
    if (url.origin === location.origin) {
        // Same-origin requests
        event.respondWith(handleSameOriginRequest(request));
    } else {
        // Cross-origin requests (CDN, external assets)
        event.respondWith(handleCrossOriginRequest(request));
    }
});

/**
 * Handle same-origin requests with cache-first strategy for static assets
 * and network-first for dynamic content
 */
async function handleSameOriginRequest(request) {
    const url = new URL(request.url);

    // Static assets (CSS, JS, images) - cache first
    if (
        url.pathname.startsWith("/static/") ||
        url.pathname.startsWith("/icons/") ||
        url.pathname.endsWith(".css") ||
        url.pathname.endsWith(".js") ||
        url.pathname.endsWith(".png") ||
        url.pathname.endsWith(".jpg") ||
        url.pathname.endsWith(".svg")
    ) {
        return cacheFirst(request, STATIC_CACHE);
    }

    // HTML pages - network first with cache fallback
    if (
        url.pathname === "/" ||
        url.pathname.includes("/result/") ||
        request.headers.get("Accept")?.includes("text/html")
    ) {
        return networkFirst(request, RUNTIME_CACHE);
    }

    // Default to network first
    return networkFirst(request, RUNTIME_CACHE);
}

/**
 * Handle cross-origin requests (CDNs)
 */
async function handleCrossOriginRequest(request) {
    // CDN assets - cache first
    return cacheFirst(request, STATIC_CACHE);
}

/**
 * Cache-first strategy
 */
async function cacheFirst(request, cacheName) {
    try {
        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);

        if (cachedResponse) {
            console.log("[SW] Cache hit:", request.url);

            // Update cache in background if not a static asset
            if (!request.url.includes("/static/") && !request.url.includes("/icons/")) {
                fetch(request)
                    .then((response) => {
                        if (response.status === 200) {
                            cache.put(request, response.clone());
                        }
                    })
                    .catch(() => {
                        // Ignore network errors in background updates
                    });
            }

            return cachedResponse;
        }

        console.log("[SW] Cache miss, fetching:", request.url);
        const response = await fetch(request);

        if (response.status === 200) {
            cache.put(request, response.clone());
        }

        return response;
    } catch (error) {
        console.error("[SW] Cache-first error:", error);

        // Try to return cached version as fallback
        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);

        if (cachedResponse) {
            return cachedResponse;
        }

        // Return offline page for navigation requests
        if (request.mode === "navigate") {
            return (
                caches.match("/") ||
                new Response(createOfflinePage(), {
                    headers: { "Content-Type": "text/html" },
                })
            );
        }

        throw error;
    }
}

/**
 * Network-first strategy
 */
async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);

        if (response.status === 200) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }

        return response;
    } catch (error) {
        console.log("[SW] Network error, trying cache:", error);

        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);

        if (cachedResponse) {
            return cachedResponse;
        }

        // Return offline page for navigation requests
        if (request.mode === "navigate") {
            return new Response(createOfflinePage(), {
                headers: { "Content-Type": "text/html" },
            });
        }

        throw error;
    }
}

/**
 * Create offline page HTML
 */
function createOfflinePage() {
    return `
    <!DOCTYPE html>
    <html lang="pl" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Offline - CV Optimizer Pro</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                margin: 0;
                padding: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
            }
            .offline-container {
                max-width: 500px;
                padding: 2rem;
            }
            .offline-icon {
                font-size: 4rem;
                margin-bottom: 1rem;
            }
            .offline-title {
                font-size: 2rem;
                font-weight: bold;
                margin-bottom: 1rem;
            }
            .offline-message {
                font-size: 1.1rem;
                opacity: 0.9;
                line-height: 1.6;
                margin-bottom: 2rem;
            }
            .offline-button {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 0.5rem;
                text-decoration: none;
                display: inline-block;
                backdrop-filter: blur(10px);
                transition: all 0.3s ease;
            }
            .offline-button:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <div class="offline-container">
            <div class="offline-icon">📱</div>
            <h1 class="offline-title">Tryb Offline</h1>
            <p class="offline-message">
                Nie masz połączenia z internetem. CV Optimizer Pro wymaga połączenia sieciowego do optymalizacji CV.
            </p>
            <a href="/" class="offline-button" onclick="window.location.reload()">
                Spróbuj ponownie
            </a>
        </div>
        
        <script>
            // Auto-reload when connection is restored
            window.addEventListener('online', () => {
                window.location.reload();
            });
        </script>
    </body>
    </html>
    `;
}

// Handle background sync
self.addEventListener("sync", (event) => {
    if (event.tag === "cv-sync") {
        console.log("[SW] Background sync triggered");
        event.waitUntil(handleBackgroundSync());
    }
});

/**
 * Handle background sync for pending CV optimizations
 */
async function handleBackgroundSync() {
    // Implementation would sync pending operations
    // For now, just log the event
    console.log("[SW] Background sync completed");
}

// Handle push notifications (future feature)
self.addEventListener("push", (event) => {
    if (event.data) {
        const data = event.data.json();
        console.log("[SW] Push notification received:", data);

        event.waitUntil(
            self.registration.showNotification(data.title, {
                body: data.message,
                icon: "/icons/icon-512.png",
                badge: "/static/icon-192.png",
                tag: "cv-optimizer-notification",
                renotify: true,
                requireInteraction: false,
                actions: [
                    {
                        action: "open",
                        title: "Otwórz aplikację",
                    },
                    {
                        action: "dismiss",
                        title: "Odrzuć",
                    },
                ],
            }),
        );
    }
});

// Handle notification clicks
self.addEventListener("notificationclick", (event) => {
    console.log("[SW] Notification clicked:", event.notification.tag);

    event.notification.close();

    if (event.action === "open") {
        event.waitUntil(
            clients.matchAll().then((clientList) => {
                // Try to focus existing tab
                for (const client of clientList) {
                    if (client.url === "/" && "focus" in client) {
                        return client.focus();
                    }
                }

                // Open new tab if no existing tab found
                if (clients.openWindow) {
                    return clients.openWindow("/");
                }
            }),
        );
    }
});

// Handle service worker updates
self.addEventListener("message", (event) => {
    if (event.data && event.data.type === "SKIP_WAITING") {
        console.log("[SW] Skipping waiting");
        self.skipWaiting();
    }
});

// Clean up old caches periodically
self.addEventListener("message", (event) => {
    if (event.data && event.data.type === "CLEANUP_CACHES") {
        event.waitUntil(cleanupCaches());
    }
});

/**
 * Clean up old cache entries
 */
async function cleanupCaches() {
    const cacheNames = await caches.keys();
    const cachesToDelete = cacheNames.filter(
        (name) =>
            name.startsWith("cv-optimizer-") &&
            name !== STATIC_CACHE &&
            name !== RUNTIME_CACHE,
    );

    await Promise.all(cachesToDelete.map((name) => caches.delete(name)));

    console.log("[SW] Cleanup completed");
}
