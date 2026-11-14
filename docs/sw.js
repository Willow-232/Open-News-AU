// Minimal offline support: serve the app shell from cache, always try the network for news first.
const CACHE = "open-news-au-v1";
const SHELL = ["./", "index.html", "manifest.json", "icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  // Network first (so news is fresh), fall back to the last cached copy when offline.
  e.respondWith(
    fetch(e.request).then((res) => {
      const copy = res.clone();
      const key = url.pathname.endsWith("news.json") ? "news.json" : e.request;
      caches.open(CACHE).then((c) => c.put(key, copy));
      return res;
    }).catch(() => caches.match(url.pathname.endsWith("news.json") ? "news.json" : e.request))
  );
});
