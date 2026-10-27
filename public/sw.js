// v7: network-first for pages, cache-first for static files; works offline after first visit
const CACHE='swanganz-v8';
const CORE=["./", "index.html", "engine.js", "manifest.webmanifest", "favicon.ico", "icons/icon-192.png", "icons/icon-512.png", "icons/logo-160.png", "icons/apple-touch-icon.png", "vendor/three/three.module.js", "vendor/three/addons/controls/OrbitControls.js", "vendor/three/addons/environments/RoomEnvironment.js"];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const r=e.request; if(r.method!=='GET')return;
  if(r.mode==='navigate'){e.respondWith(fetch(r).then(res=>{const cp=res.clone();caches.open(CACHE).then(c=>c.put('index.html',cp));return res;}).catch(()=>caches.match('index.html')));return;}
  e.respondWith(caches.match(r).then(hit=>hit||fetch(r).then(res=>{if(res.ok){const cp=res.clone();caches.open(CACHE).then(c=>c.put(r,cp));}return res;})));
});
