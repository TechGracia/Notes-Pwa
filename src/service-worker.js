import { build, files, version } from '$service-worker';

const CACHE = `cache-${version}`;

const ASSETS = [...build, ...files, '/'];

self.addEventListener('install', (event) => {
	event.waitUntil(
		caches.open(CACHE).then((cache) => {
			return cache.addAll(ASSETS);
		})
	);

	self.skipWaiting();
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		caches.keys().then((cacheNames) => {
			return Promise.all(
				cacheNames
					.filter((cacheName) => cacheName !== CACHE)
					.map((cacheName) => caches.delete(cacheName))
			);
		})
	);

	self.clients.claim();
});

self.addEventListener('fetch', (event) => {
	if (event.request.method !== 'GET') return;

	event.respondWith(
		caches.match(event.request).then((cachedResponse) => {
			return cachedResponse || fetch(event.request);
		})
	);
});
