// One worker per GitHub Pages project path. Keep the app shell available offline.
const SCOPE = self.registration.scope;
const CACHE = "pocket-pwa-" + new URL(SCOPE).pathname.replace(/\W/g, "-") + "v1";
const ASSETS = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png"];
const PATHS = new Set(ASSETS.map((name) => new URL(name, SCOPE).pathname));

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS.map((name) => new URL(name, SCOPE)))).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith("pocket-pwa-") && key !== CACHE && key.includes(new URL(SCOPE).pathname.replace(/\W/g, "-"))).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin || !PATHS.has(url.pathname)) return;
  // Network first: new deployments appear without waiting for a service-worker version bump.
  event.respondWith(fetch(event.request).then((response) => {
    if (response.ok) {
      const copy = response.clone();
      event.waitUntil(caches.open(CACHE).then((cache) => cache.put(event.request, copy)));
    }
    return response;
  }).catch(async () => (await caches.match(event.request, { ignoreSearch: true })) || (event.request.mode === "navigate" ? caches.match(new URL("./", SCOPE)) : undefined) || Response.error()));
});
