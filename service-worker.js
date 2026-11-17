/* MONO STUDIO v0.5: always request fresh HTML and feed, no offline content-data cache. */
const CACHE='mono-ui-v05';
self.addEventListener('install',e=>{self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil((async()=>{for(const k of await caches.keys())if(k.startsWith('mono-ui-')&&k!==CACHE)await caches.delete(k);await self.clients.claim();})());});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method!=='GET'||u.origin!==self.location.origin)return; if(e.request.mode==='navigate'||u.pathname.endsWith('/data/latest_news.json')){e.respondWith(fetch(e.request,{cache:'no-store'}));return;}e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});
