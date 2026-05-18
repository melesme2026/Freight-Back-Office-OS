const CACHE_NAME = "adwa-freight-os-shell-v2";
const SHELL_ASSETS = ["/offline.html", "/logo.svg", "/brand/adwa-mark-light.svg", "/icons/driver-icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

function isSensitiveRequest(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith("/api/") || url.pathname.includes("/documents") || request.headers.has("authorization") || request.method !== "GET";
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (isSensitiveRequest(request)) return;

  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match("/offline.html")));
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (!response || response.status !== 200 || response.type !== "basic") return response;
        const responseToCache = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, responseToCache));
        return response;
      });
    })
  );
});
