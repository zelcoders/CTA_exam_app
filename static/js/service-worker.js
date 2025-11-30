self.addEventListener("install", event => {
    event.waitUntil(
        caches.open("mcq-cache").then(cache => {
            return cache.addAll([
                "/",
                "/static/css/styles-cta.css",
                "/static/offline.js",
                "/templates/exams-obj.html"
            ]);
        })
    );
});

self.addEventListener("fetch", event => {
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
