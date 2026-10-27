"""Merge PiCCO & FloTrac Lab into the Swan-Ganz Simulator as a second module with an icon switcher."""
import re, sys

SWAN = sys.argv[1]
LAB = sys.argv[2]
OUT = sys.argv[3]

swan_lines = open(SWAN, encoding="utf-8").read().split("\n")
# drop the publish skeleton (line 1) and closing tags (last line)
assert swan_lines[0].startswith("<!doctype html>")
assert swan_lines[-1].strip() == "</body></html>"
swan = "\n".join(swan_lines[1:-1])
lab = open(LAB, encoding="utf-8").read()


def sub1(src, old, new):
    n = src.count(old)
    if n != 1:
        raise SystemExit(f"expected 1 match, found {n}: {old[:70]!r}")
    return src.replace(old, new)


# ---------------- lab -> shadow-DOM module ----------------
lab_css = re.search(r"<style>(.*?)</style>", lab, re.S).group(1)
lab_body = lab[lab.index('<div class="wrap">'):lab.index("<script>")]
lab_js = lab[lab.index("<script>") + len("<script>"):lab.rindex("</script>")]

lab_css = sub1(lab_css, "/* Layout: bedside-monitor bench.", "/* PiCCO & FloTrac module (shadow DOM). Layout: bedside-monitor bench.")
lab_css = re.sub(r":root\{\s*color-scheme: dark;", ":host{display:block;color-scheme:dark;", lab_css, count=1)
# harmonise palette with the Swan-Ganz app
for k, v in {"--bg:#09111a": "--bg:#060d16", "--panel:#0e1925": "--panel:#0b1724", "--panel2:#122031": "--panel2:#0f2134",
             "--line:#1c2d40": "--line:#1c3550", "--grid:#152638": "--grid:#13263a", "--fg:#e3eaf2": "--fg:#e6eef7",
             "--muted:#8495a9": "--muted:#8ea6bf", "--dim:#5b6c80": "--dim:#5f7790"}.items():
    lab_css = sub1(lab_css, k, v)
lab_css = sub1(lab_css, "html,body{background:var(--bg);color:var(--fg)}\n", ":host{background:var(--bg);color:var(--fg);font-family:var(--f-ui);font-size:14px;line-height:1.45}\n[hidden]{display:none!important}\n")
lab_css = re.sub(r"body\{font-family:var\(--f-ui\);.*?padding-block:18px 40px\}\n", "", lab_css, count=1, flags=re.S)
lab_css = sub1(lab_css, ".wrap{max-width:1380px;margin:0 auto;", ".wrap{")

# masthead: drop the lab's own brand/h1 (the app header carries it), keep tools + scenarios + case
lab_body = re.sub(r'<div>\s*<p class="brand">.*?</h1>\s*</div>\s*', '<h2 class="modTitle">Scenario</h2>\n      ', lab_body, count=1, flags=re.S)
lab_css += "\n.modTitle{font-family:var(--f-mono);font-size:12px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);align-self:center}\n.mast-row{align-items:center}\n"

# JS: scope DOM lookups to the shadow root, pause when the module is hidden
lab_js = sub1(lab_js, "(()=>{\nconst $=id=>document.getElementById(id);",
              "window.initPicco=function(host){\nconst R=host.attachShadow({mode:'open'});\nR.innerHTML='<style>'+document.getElementById('pfCss').textContent+'</style>'+document.getElementById('pfTpl').innerHTML;\nconst $=id=>R.getElementById(id);")
lab_js = sub1(lab_js, "const CSS=getComputedStyle(document.documentElement);", "const CSS=getComputedStyle(host);")
lab_js = lab_js.replace("document.querySelectorAll(", "R.querySelectorAll(")
assert "document." not in lab_js.replace("document.getElementById('pfCss')", "").replace("document.getElementById('pfTpl')", ""), "unscoped document access left"
lab_js = sub1(lab_js, "function tick(now){\n  const dt=Math.min(.05,(now-last)/1000); last=now;",
              "function tick(now){\n  if(window.APPVIEW==='swan'){last=now;requestAnimationFrame(tick);return;}\n  const dt=Math.min(.05,(now-last)/1000); last=now;")
lab_js = sub1(lab_js, "load('sepsis');\nrequestAnimationFrame(tick);\n})();",
              "load('sepsis');\nrequestAnimationFrame(tick);\nreturn {shown(m){last=performance.now();setMode(m);renderTiles();drawTD();drawTrend();renderTruth();renderInterp();}};\n};")

# ---------------- Swan-Ganz shell changes ----------------
swan = sub1(swan, "IBM+Plex+Mono:wght@500&display=swap", "IBM+Plex+Mono:wght@400;500&display=swap")
swan = sub1(swan, '<meta name="description" content="Pulmonary artery catheter simulator: 3D insertion, live bedside waveforms, shock haemodynamics, thermodilution and troubleshooting. ICU O.Dakka.">',
            '<meta name="description" content="Haemodynamic monitoring simulator: Swan–Ganz catheter (3D insertion, live waveforms, shock profiles) and PiCCO/FloTrac (pulse contour, transpulmonary thermodilution). ICU O.Dakka.">')

SWITCH_CSS = """
/* module switcher */
.switch{display:inline-flex;gap:4px;padding:4px;border:1px solid var(--line2);border-radius:12px;background:#08131f}
.switch button{display:inline-flex;align-items:center;gap:8px;background:transparent;border:1px solid transparent;border-radius:9px;padding:6px 12px 6px 8px;color:var(--muted);font:600 15px/1 var(--f-display);letter-spacing:.03em}
.switch button svg{width:30px;height:30px;flex:none}
.switch button:hover{color:var(--text)}
.switch button[aria-pressed="true"]{background:var(--panel2);border-color:var(--line2);color:var(--text)}
.switch button[data-app="swan"][aria-pressed="true"]{box-shadow:inset 0 -2px 0 var(--cath)}
.switch button[data-app="picco"][aria-pressed="true"]{box-shadow:inset 0 -2px 0 #36cfc2}
.switch button[data-app="flotrac"][aria-pressed="true"]{box-shadow:inset 0 -2px 0 #f1b64a}
.modView{max-width:1720px;margin:0 auto}
@media (max-width:560px){.switch{width:100%}.switch button{flex:1;flex-direction:column;justify-content:center;gap:3px;padding:6px 4px;font-size:13px}.switch button svg{width:26px;height:26px}}
"""
swan = sub1(swan, "@media (prefers-reduced-motion:reduce){*{transition:none!important}}\n</style>",
            "@media (prefers-reduced-motion:reduce){*{transition:none!important}}\n" + SWITCH_CSS + "</style>")

ICON_SWAN = ('<svg viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke-linecap="round">'
             '<path d="M4 5c4 0 6 3 7 8s2 10 7 10c3 0 4-3 6-6" stroke="#ffc83d" stroke-width="2.2"/>'
             '<circle cx="25.5" cy="15.5" r="3.6" fill="rgba(233,246,255,.25)" stroke="#e9f6ff" stroke-width="1.6"/>'
             '<path d="M6.5 6.2v2.2M9.2 8.6l-1.6 1.4" stroke="#16120a" stroke-width="1.4"/></svg>')
ICON_PICCO = ('<svg viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke-linecap="round" stroke-linejoin="round">'
              '<path d="M3 25h26" stroke="#2a4d70" stroke-width="1.5"/>'
              '<path d="M4 25c3 0 4-14 7-14s5 7 9 10 6 4 9 4" stroke="#36cfc2" stroke-width="2.2"/>'
              '<circle cx="11" cy="11" r="1.6" fill="#36cfc2" stroke="none"/></svg>')
ICON_FLO = ('<svg viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M6.5 24l2.5-13 3 6v7z" fill="rgba(241,182,74,.45)" stroke="none"/>'
            '<path d="M21 24l2.5-13 3 6v7z" fill="rgba(241,182,74,.45)" stroke="none"/>'
            '<path d="M3 24h3.5l2.5-13 3 6h2l2-2 2.5 9h2.5l2.5-13 3 6H29" stroke="#ff5f5f" stroke-width="2"/></svg>')

swan = sub1(swan, """      <h1>Swan–Ganz <span>Simulator</span></h1>
      <p>PA catheter insertion · live waveforms · shock haemodynamics — ICU O.Dakka</p>
    </div>
  </div>
  <div class="topActions">""", f"""      <h1 id="appTitle">Swan–Ganz <span>Simulator</span></h1>
      <p id="appSub">PA catheter insertion · live waveforms · shock haemodynamics — ICU O.Dakka</p>
    </div>
  </div>
  <nav class="switch" aria-label="Choose simulator">
    <button type="button" data-app="swan" aria-pressed="true">{ICON_SWAN}<span>Swan–Ganz</span></button>
    <button type="button" data-app="picco" aria-pressed="false">{ICON_PICCO}<span>PiCCO</span></button>
    <button type="button" data-app="flotrac" aria-pressed="false">{ICON_FLO}<span>FloTrac</span></button>
  </nav>
  <div class="topActions" id="swanActions">""")

swan = sub1(swan, '<main class="app">', '<main class="app" id="viewSwan">')
# install button moves to the shared header so it works from every module
swan = sub1(swan, '    <button class="btn" id="installBtn" hidden>Install app</button>\n', '')
swan = sub1(swan, '  <div class="topActions" id="swanActions">', '  <button class="btn gold" id="installBtn" hidden>Install app</button>\n  <div class="topActions" id="swanActions">')
swan = sub1(swan, '<span>Educational model. Stylised anatomy; waveforms and drug responses are illustrative, not validated predictions.</span>',
  '<span>Educational model. Stylised anatomy; waveforms and drug responses are illustrative, not validated predictions. PiCCO and FloTrac are trademarks of Getinge and Edwards Lifesciences; this app is not affiliated with or endorsed by them.</span>')
swan = sub1(swan, """</main>
<footer class="foot">""", f"""</main>
<section class="modView" id="viewPicco" aria-label="PiCCO and FloTrac simulator" hidden><div id="pfHost"></div></section>
<template id="pfTpl">
{lab_body}</template>
<script type="text/plain" id="pfCss">{lab_css}</script>
<footer class="foot">""")


# ---------------- Swan-Ganz clinical additions ----------------
# PEEP (zone 3 teaching), LBBB -> complete heart block, PA rupture, chest X-ray check
swan = sub1(swan, "  vent:'spont', af:false, damp:'opt', level:0,", "  vent:'spont', af:false, damp:'opt', level:0, peep:5, lbbb:false, chb:false, ruptured:false,")
swan = sub1(swan, "iv:{fluid:0, ne:false, dob:false, diur:false, ino:false, peri:false, lysis:false},", "iv:{fluid:0, ne:false, dob:false, diur:false, ino:false, peri:false, lysis:false, pace:false},")
swan = swan.replace("S.iv = {fluid:0,ne:false,dob:false,diur:false,ino:false,peri:false,lysis:false};", "S.iv = {fluid:0,ne:false,dob:false,diur:false,ino:false,peri:false,lysis:false,pace:false}; S.chb = false; S.ruptured = false;")
swan = sub1(swan, """  p.hr = clamp(p.hr,40,170);
  return p;""", """  if (S.chb && !S.iv.pace){ p.hr = 36; p.co *= .55; }
  else if (S.chb && S.iv.pace){ p.hr = 80; p.co *= .9; }
  if (S.ruptured){ p.sao2 *= .84; p.co *= .78; p.hr += 18; p.hb -= 1.5; }
  // PEEP on mechanical ventilation: less venous return, raised measured (not transmural) pressures
  p.zone3 = true;
  if (S.vent==='mech'){
    const dp = S.peep - 5;
    p.co *= 1 - .015*dp*clamp(p.fr,0,1);
    const off = .74*.4*dp; p.ra += off; p.pawp += off;
    if (.74*S.peep > p.pawp - off){ p.zone3 = false; p.pawp = Math.max(p.pawp, .74*S.peep*.85); }
  }
  p.hr = clamp(p.hr,30,170);
  return p;""")
# LBBB ECG + catheter-induced complete heart block (escape rhythm)
swan = sub1(swan, """  let type = S.af ? 'af' : 'sinus', rr = base, sv = 1;
  if (prev && prev.type==='pvc'){ rr = base*1.45; sv = 1.12; }""", """  let type = S.af ? 'af' : 'sinus', rr = base, sv = 1;
  if (S.lbbb && !S.chb && !S.iv.pace && zone()==='rv' && Math.random() < .03){ S.chb = true; setTimeout(() => window.dispatchEvent(new Event('chb')), 0); }
  if (S.chb && !S.iv.pace){ type = 'esc'; }
  else if (prev && prev.type==='pvc'){ rr = base*1.45; sv = 1.12; }""")
swan = sub1(swan, """function ecgBeat(b,τ){
  if (b.type==='pvc')""", """function ecgBeat(b,τ){
  if (b.type==='esc') return G(τ,b.qr+.03,.045,-.9) + G(τ,b.qr+.11,.05,.5) + G(τ,b.te,.07,.5);
  if (S.lbbb && b.type!=='pvc') return (b.type==='sinus'?G(τ,b.pc,.024,.13):0) + G(τ,b.qr,.03,.85) + G(τ,b.qr+.05,.03,.75) + G(τ,b.te-.06,.06,-.35);
  if (b.type==='pvc')""")
swan = sub1(swan, """<option value="af">Atrial fibrillation</option></select></label>""", """<option value="af">Atrial fibrillation</option><option value="lbbb">Sinus with LBBB</option></select></label>""")
swan = sub1(swan, """<option value="-10">10 cm too low</option></select></label>""", """<option value="-10">10 cm too low</option></select></label>
          <label for="setPeep">PEEP (mechanical ventilation)<select id="setPeep"><option value="5">5 cmH₂O</option><option value="10">10 cmH₂O</option><option value="15">15 cmH₂O</option><option value="20">20 cmH₂O</option></select></label>""")
swan = sub1(swan, """$('setRhythm').onchange = e => { S.af = e.target.value==='af'; $('rhythmTxt').textContent = S.af ? 'AF' : 'sinus'; log(S.af ? 'AF: a waves disappear from RA and wedge traces; irregular RR changes beat-to-beat stroke volume.' : 'Sinus rhythm restored.'); };""",
"""$('setRhythm').onchange = e => { const v = e.target.value; S.af = v==='af'; S.lbbb = v==='lbbb'; $('rhythmTxt').textContent = S.af ? 'AF' : S.lbbb ? 'LBBB' : 'sinus';
  log(S.af ? 'AF: a waves disappear from RA and wedge traces; irregular RR changes beat-to-beat stroke volume.' : S.lbbb ? 'Pre-existing LBBB: relative contraindication. The catheter can cause RBBB in the RV and so complete heart block. Have transcutaneous pacing ready and cross the RV quickly.' : 'Sinus rhythm restored.', S.lbbb ? 'w' : ''); };
$('setPeep').onchange = e => { S.peep = +e.target.value; derive(); render(true);
  log(S.vent!=='mech' ? 'PEEP applies to mechanical ventilation: switch ventilation to mechanical.' : S.peep >= 10 ? `PEEP ${S.peep}: measured RAP/PAWP rise without a rise in transmural filling; venous return falls. If PEEP (×0.74) exceeds PAWP the tip may be outside West zone 3.` : 'PEEP 5 cmH₂O.', S.peep>=10 ? 'w' : ''); };
window.addEventListener('chb', () => { derive(); buildIV(); render(true); alertMsg('Complete heart block: catheter-induced RBBB on top of LBBB. Start transcutaneous pacing (Interventions), withdraw to the RA, get help.', 'crit', 9000); log('Complete heart block during RV passage (LBBB + catheter RBBB). Escape rhythm ~36/min.', 'c'); });""")
swan = sub1(swan, """['ino','Inhaled NO','tog'],['peri','Pericardiocentesis','tog'],['lysis','Thrombolysis','tog']""", """['ino','Inhaled NO','tog'],['peri','Pericardiocentesis','tog'],['lysis','Thrombolysis','tog'],['pace','Transcutaneous pacing','tog']""")
swan = sub1(swan, """      if ((k==='peri' && S.scen!=='tamp') || (k==='lysis' && S.scen!=='pe')){""", """      if (k==='pace' && !S.chb){ if (S.iv[k]) log('Pacing pads on, standby: no heart block at present.', ''); }
      else if ((k==='peri' && S.scen!=='tamp') || (k==='lysis' && S.scen!=='pe')){""")
swan = sub1(swan, "$('setVent').onchange = e => { S.vent = e.target.value;", "$('setVent').onchange = e => { S.vent = e.target.value; derive();")
# PA rupture after sustained over-wedge
swan = sub1(swan, """  if (z==='wedge'){
    S.wedgeT += dt;""", """  if (z==='over' && S.overStart && simT - S.overStart > 6 && !S.ruptured){
    S.ruptured = true; derive(); render(true);
    alertMsg('PA rupture: massive haemoptysis. Leave the catheter in, re-inflate the balloon to tamponade, bleeding side down, isolate the lung (DLT / bronchial blocker), call thoracic surgery / IR.', 'crit', 12000);
    log('PA RUPTURE after sustained over-wedge: haemoptysis, desaturation, hypotension.', 'c');
  }
  if (z==='wedge'){
    S.wedgeT += dt;""")
# chest X-ray tip check
swan = sub1(swan, """          <button class="btn" id="tdBtn">Thermodilution CO</button>""", """          <button class="btn" id="tdBtn">Thermodilution CO</button>
          <button class="btn" id="cxrBtn">Chest X-ray</button>""")
swan = sub1(swan, """/* ---------- scenarios, interventions, settings ---------- */""", """$('cxrBtn').onclick = () => {
  const z = zone(), t = S.tip, w = S.wedgeDepth; let msg, cls = 'g';
  if (S.slack > 3){ msg = `Loop of catheter in the ${t < TV ? 'RA' : 'RV'} (${S.slack.toFixed(0)} cm slack). Withdraw, inflate and re-float.`; cls = 'w'; }
  else if (z==='svc' || z==='ra'){ msg = `Tip in the ${ZONES[z].name}: not yet in position.`; cls = 'w'; }
  else if (z==='rv'){ msg = 'Tip in the RV: arrhythmia risk if left here. Float on to the PA.'; cls = 'w'; }
  else if (t > w - .5){ msg = 'Tip too distal: beyond the hilum in the lung field. Withdraw 2–3 cm (risk of spontaneous wedge, infarction, rupture).'; cls = 'c'; }
  else if (t > w - 3){ msg = 'Tip in a proximal branch PA, within ~2 cm of the hilum, below the LA on the lateral film (zone 3): good position.'; }
  else { msg = 'Tip in the main PA: acceptable, but it may not wedge with a full 1.5 mL. Advance slightly if a wedge cannot be obtained.'; cls = 'w'; }
  log('CXR: ' + msg, cls); alertMsg('CXR: ' + msg, cls==='c' ? 'crit' : 'warn', 6000);
};

/* ---------- scenarios, interventions, settings ---------- */""")
# teaching: RV tip on LBBB, zone 3 interpretation
swan = sub1(swan, """['RV systolic ≈ PA systolic in the absence of pulmonic stenosis','RV at > 40 cm suggests coiling: withdraw and re-float']]""", """['RV systolic ≈ PA systolic in the absence of pulmonic stenosis','RV at > 40 cm suggests coiling: withdraw and re-float','Pre-existing LBBB: catheter-induced RBBB can cause complete heart block; have pacing ready']]""")
swan = sub1(swan, """  if (S.vent==='mech' && d.ppv > .15) add('Large arterial pulse-pressure variation on the ventilator — likely fluid responsive.', 'ok');""", """  if (S.vent==='mech' && d.ppv > .15) add('Large arterial pulse-pressure variation on the ventilator — likely fluid responsive.', 'ok');
  if (S.vent==='mech' && S.peep >= 10) add(`PEEP ${S.peep}: measured RAP and PAWP over-read transmural filling by ~${(.74*.4*(S.peep-5)).toFixed(0)} mmHg.`, 'warn');
  if (d.zone3 === false) add('PAWP may reflect alveolar pressure (non-zone 3): PEEP exceeds left atrial pressure. Check that PAWP respiratory swing is not larger than the PA diastolic swing; confirm tip below the LA on a lateral film.', 'crit');
  if (S.chb) add(S.iv.pace ? 'Complete heart block: paced at 80/min.' : 'Complete heart block with slow escape rhythm: pace now.', 'crit');
  if (S.ruptured) add('PA rupture: haemoptysis and hypoxaemia. Balloon tamponade, lung isolation, surgery / IR.', 'crit');""")
swan = sub1(swan, """$('resetAll').onclick = () => { stopAuto();""", """$('resetAll').onclick = () => { S.chb = false; S.ruptured = false; stopAuto();""")

# pause the Swan-Ganz engine and keyboard shortcuts while the PiCCO module is shown
swan = sub1(swan, """function loop(now){
  const dtReal = Math.min(.1, (now - lastReal)/1000); lastReal = now;""",
            """function loop(now){
  if (window.APPVIEW !== 'swan'){ lastReal = now; requestAnimationFrame(loop); return; }
  const dtReal = Math.min(.1, (now - lastReal)/1000); lastReal = now;""")
swan = sub1(swan, """document.addEventListener('keydown', e => {
  if (e.target.matches('input,select,textarea')) return;""",
            """document.addEventListener('keydown', e => {
  if (window.APPVIEW !== 'swan' || e.target.matches('input,select,textarea')) return;""")

SWITCH_JS = """
<!-- ======================= MODULE SWITCHER + PiCCO/FloTrac ======================= -->
<script>
'use strict';
""" + lab_js + """
(function(){
  window.APPVIEW = 'swan';
  let pf = null;
  const TITLES = {
    swan:['Swan–Ganz <span>Simulator</span>','PA catheter insertion · live waveforms · shock haemodynamics — ICU O.Dakka'],
    picco:['PiCCO <span>Simulator</span>','Calibrated pulse contour · transpulmonary thermodilution · lung water — ICU O.Dakka'],
    flotrac:['FloTrac <span>Simulator</span>','Autocalibrated pulse contour · SV, SVV, SVR — ICU O.Dakka']
  };
  function switchApp(v){
    v = (v === 'picco' || v === 'flotrac') ? v : 'swan';
    window.APPVIEW = v;
    $('viewSwan').hidden = v !== 'swan';
    $('viewPicco').hidden = v === 'swan';
    $('swanActions').hidden = v !== 'swan';
    document.querySelectorAll('.switch [data-app]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.app === v)));
    $('appTitle').innerHTML = TITLES[v][0]; $('appSub').textContent = TITLES[v][1];
    if (v !== 'swan'){ if (!pf) pf = window.initPicco($('pfHost')); pf.shown(v); }
    else requestAnimationFrame(() => { setupMonitor(); updateScales(); drawTD(); });
    if ((v !== 'swan' || location.hash) && location.hash.slice(1) !== v) history.replaceState(null, '', '#' + v);
  }
  document.querySelectorAll('.switch [data-app]').forEach(b => b.addEventListener('click', () => switchApp(b.dataset.app)));
  window.addEventListener('hashchange', () => switchApp(location.hash.slice(1)));
  switchApp(location.hash.slice(1));
})();
</script>
"""
swan = swan.rstrip() + "\n" + SWITCH_JS

open(OUT, "w", encoding="utf-8").write(swan)
print("written", OUT, len(swan))
