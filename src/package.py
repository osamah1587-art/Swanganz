"""Build the Netlify folder: proper <head>, local three.js (no CDN dependency), service worker."""
import json, shutil, os, sys
SITE, OUT, VER = sys.argv[1], sys.argv[2], sys.argv[3]
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
shutil.copytree(os.path.join(SITE,'icons'), os.path.join(OUT,'icons'))
for f in ['favicon.ico','manifest.webmanifest']: shutil.copy(os.path.join(SITE,f), OUT)
T='node_modules/three'
for src,dst in [('build/three.module.js','vendor/three/three.module.js'),('examples/jsm/controls/OrbitControls.js','vendor/three/addons/controls/OrbitControls.js'),('examples/jsm/environments/RoomEnvironment.js','vendor/three/addons/environments/RoomEnvironment.js')]:
    os.makedirs(os.path.dirname(os.path.join(OUT,dst)),exist_ok=True); shutil.copy(os.path.join(T,src),os.path.join(OUT,dst))
src=open(os.path.join(SITE,'index.html'),encoding='utf-8').read()
cdn='{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}'
assert src.count(cdn)==1
src=src.replace(cdn,'{"imports":{"three":"./vendor/three/three.module.js","three/addons/":"./vendor/three/addons/"}}')
start=src.index('<title>'); end=src.index('display=swap">',start)+len('display=swap">')
head=src[start:end].replace('<meta name="claude:viewport-fit-sides" content="cover">\n',''); body=src[:start]+src[end:]
html=('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
 +head+'\n<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}img{max-width:100%}[hidden]{display:none!important}</style>\n</head>\n<body>\n'+body.strip()+'\n</body>\n</html>\n')
open(os.path.join(OUT,'index.html'),'w',encoding='utf-8').write(html)
core=['./','index.html','manifest.webmanifest','favicon.ico','icons/icon-192.png','icons/icon-512.png','icons/logo-160.png','icons/apple-touch-icon.png',
      'vendor/three/three.module.js','vendor/three/addons/controls/OrbitControls.js','vendor/three/addons/environments/RoomEnvironment.js']
open(os.path.join(OUT,'sw.js'),'w').write(f"""// {VER}: network-first for pages, cache-first for static files; works offline after first visit
const CACHE='swanganz-{VER}';
const CORE={json.dumps(core)};
self.addEventListener('install',e=>{{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()));}});
self.addEventListener('activate',e=>{{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));}});
self.addEventListener('fetch',e=>{{
  const r=e.request; if(r.method!=='GET')return;
  if(r.mode==='navigate'){{e.respondWith(fetch(r).then(res=>{{const cp=res.clone();caches.open(CACHE).then(c=>c.put('index.html',cp));return res;}}).catch(()=>caches.match('index.html')));return;}}
  e.respondWith(caches.match(r).then(hit=>hit||fetch(r).then(res=>{{if(res.ok){{const cp=res.clone();caches.open(CACHE).then(c=>c.put(r,cp));}}return res;}})));
}});
""")
open(os.path.join(OUT,'README.txt'),'w',encoding='utf-8').write(f"""Swan–Ganz Simulator {VER} · ICU O.Dakka
Three simulators in one app: Swan–Ganz · PiCCO · FloTrac (icons in the header, or index.html#picco / #flotrac).
three.js is bundled locally (vendor/), so the 3D view works on filtered hospital networks and offline after the first visit.
DEPLOY: drag this folder or the ZIP onto the swanganz project on Netlify (Deploys tab).
Educational model only; not affiliated with Getinge or Edwards Lifesciences.
""")
print('packaged',OUT)
