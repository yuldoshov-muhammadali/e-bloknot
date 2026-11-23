/*
  sw.js — Service Worker.
  Vazifasi: faqat STATIK fayllarni (CSS, JS, ikonka) keshlash, shunda ilova
  tez ochiladi va telefonga o'rnatish mumkin bo'ladi.

  MUHIM: sahifalar va API (ma'lumot) KESHLANMAYDI — ma'lumot doim yangi
  bo'lishi kerak. Internet yo'q bo'lsa oddiy oflayn sahifa ko'rsatiladi.
*/

var CACHE = "ebloknot-static-v1";

// Oldindan keshlanadigan statik fayllar.
var STATIC_ASSETS = [
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/manifest.json",
  "/static/offline.html",
];

// O'rnatish — statik fayllarni keshga solamiz.
self.addEventListener("install", function (e) {
  e.waitUntil(
    caches
      .open(CACHE)
      .then(function (c) {
        return c.addAll(STATIC_ASSETS);
      })
      .then(function () {
        return self.skipWaiting();
      })
  );
});

// Faollashtirish — eski keshlarni tozalaymiz.
self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches
      .keys()
      .then(function (keys) {
        return Promise.all(
          keys
            .filter(function (k) {
              return k !== CACHE;
            })
            .map(function (k) {
              return caches.delete(k);
            })
        );
      })
      .then(function () {
        return self.clients.claim();
      })
  );
});

// So'rovlarni ushlaymiz.
self.addEventListener("fetch", function (e) {
  var req = e.request;

  // Faqat GET so'rovlar bilan ishlaymiz (POST/API — keshlanmaydi).
  if (req.method !== "GET") return;

  var url = new URL(req.url);
  // Faqat o'z saytimiz.
  if (url.origin !== self.location.origin) return;

  // 1) Statik fayllar — avval keshdan, bo'lmasa tarmoqdan (va keshga solamiz).
  if (url.pathname.indexOf("/static/") === 0) {
    e.respondWith(
      caches.match(req).then(function (cached) {
        return (
          cached ||
          fetch(req).then(function (resp) {
            var copy = resp.clone();
            caches.open(CACHE).then(function (c) {
              c.put(req, copy);
            });
            return resp;
          })
        );
      })
    );
    return;
  }

  // 2) Sahifalar (navigatsiya) — tarmoqdan. Internet yo'q bo'lsa oflayn sahifa.
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req).catch(function () {
        return caches.match("/static/offline.html");
      })
    );
    return;
  }

  // 3) Boshqa so'rovlar (masalan /fragment, /api) — faqat tarmoqdan, keshlanmaydi.
  e.respondWith(fetch(req));
});
