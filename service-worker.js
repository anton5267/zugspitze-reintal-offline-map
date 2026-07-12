const CACHE_NAME = "zugspitze-pwa-20260712-clean";
const ASSETS = [
  "./",
  "index.html",
  "index.html?app=1",
  "print.html",
  "manifest.webmanifest",
  "service-worker.js",
  "icon-192.png",
  "icon-512.png",
  "apple-startup-1179x2556.png",
  "apple-startup-1290x2796.png",
  "zugspitze_reintal_corrected_route.gpx",
  "zugspitze_reintal_corrected_map.kml",
  "zugspitze_organic_maps_import.kmz",
  "zugspitze_organic_maps_import.kml",
  "ORGANIC_MAPS_IMPORT.txt",
  "zugspitze_descent_options.gpx",
  "zugspitze_descent_options.kml",
  "zugspitze_reintal_editable_points.json",
  "OFFLINE_README.txt",
  "zugspitze_offline_pack.zip"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith("zugspitze-pwa-") && key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put("index.html", copy));
          return response;
        })
        .catch(() => caches.match("index.html"))
    );
    return;
  }

  event.respondWith(
    caches.match(request)
      .then((cached) => cached || fetch(request).then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      }))
  );
});
