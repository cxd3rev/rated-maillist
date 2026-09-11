const CACHE = "rated-app-v14";
const SHELL = [
    "./",
    "./index.html",
    "./css/style.css",
    "./js/albums.js",
    "./js/artistPhotos.js",
    "./js/globalRatings.js",
    "./js/script.js",
    "./manifest.webmanifest",
    "./assets/logo.png",
    "./assets/logo-l.png"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE).then(cache => cache.addAll(SHELL))
    );
    self.skipWaiting();
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(key => key !== CACHE)
                    .map(key => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", event => {
    if (event.request.method !== "GET") {
        return;
    }

    const url = new URL(event.request.url);

    if (url.origin !== self.location.origin) {
        return;
    }

    event.respondWith(
        caches.match(event.request).then(cached => {
            const network = fetch(event.request)
                .then(response => {
                    if (!response || !response.ok) {
                        return response;
                    }
                    const copy = response.clone();
                    caches.open(CACHE).then(cache => cache.put(event.request, copy));
                    return response;
                })
                .catch(() => cached);

            return network.then(response => response || cached);
        })
    );
});
