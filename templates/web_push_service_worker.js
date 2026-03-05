/**
 * Service Worker dla Web Push — szablon reużywalny
 * Kopiuj do: client/public/sw.js
 * 
 * Obsługuje:
 * - Push notifications z akcjami (kliknięcie → otwiera URL)
 * - Notification click → focus lub otwórz okno
 * - Background sync (opcjonalne)
 */

self.addEventListener("push", (event) => {
  if (!event.data) return;

  let data;
  try {
    data = event.data.json();
  } catch {
    data = { title: "Manus Brain", body: event.data.text(), url: "/" };
  }

  const options = {
    body: data.body || "Nowe powiadomienie",
    icon: data.icon || "/favicon.ico",
    badge: data.badge || "/favicon.ico",
    tag: data.tag || "manus-notification",
    data: { url: data.url || "/" },
    requireInteraction: data.requireInteraction || false,
    actions: data.actions || [],
    vibrate: [200, 100, 200],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || "Manus Brain", options)
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      // Jeśli okno już otwarte — focus
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && "focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      // Otwórz nowe okno
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => {
  event.waitUntil(clients.claim());
});
