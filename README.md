# Swan–Ganz · PiCCO · FloTrac simulator — ICU O.Dakka

Haemodynamic monitoring teaching app, live at https://swanganz.netlify.app (auto-deployed from `main`).

## Structure
- `public/index.html` — the app: Swan–Ganz module, PiCCO/FloTrac module (shadow DOM), tab switcher.
- `public/engine.js` — shared patient engine. One patient for all three monitors: scenarios, drugs, fluid, ventilation, rhythm, oxygen delivery, baroreflex.
- `public/vendor/three/` — three.js r160 bundled locally (works on filtered hospital networks and offline).
- `public/sw.js` — service worker; bump `CACHE` on every release.
- `netlify.toml` — publish `public/`, no build step.

Educational model only. Not affiliated with Getinge or Edwards Lifesciences.
