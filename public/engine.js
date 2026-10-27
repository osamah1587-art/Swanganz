/* ============================================================
   Shared patient engine: one patient, three monitors.
   Swan–Ganz, PiCCO and FloTrac all read this state, so a drug,
   a bolus or a scenario change in one tab is the same patient
   in the others, and their cardiac outputs can be compared.
   ============================================================ */
window.PT = (() => {
  'use strict';
  const BSA = 1.9, PBW = 70;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  // c = LV contractility, cR = RV contractility, vol = stressed volume (drives GEDVI),
  // pvr in dyn·s·cm⁻⁵, ppc = pericardial pressure (mmHg), mr = mitral regurgitation severity 0–1
  const BASE = {
    vol: 720, c: 1, cR: 1, svri: 1900, pvr: 80, hr: 78, evlwi: 6,
    hb: 12, sao2: .98, vo2i: 130, ei: 0, lac0: 1, ppc: 0, mr: 0,
    kPA: 1, kA: 1, rr: 14, swing: 4, pulsus: .05,
    rhythm: 'sinus', vent: 'cmv', tv: 8, peep: 5, chest: 'closed', line: 'ok',
    norad: 0, dobu: 0, ino: false, lysis: false, pace: false, chb: false, ruptured: false, plr: false, eeo: false
  };

  const SCEN = {
    normal: { name: 'Normal (post-op)', short: 'Baseline reference', p: {},
      v: '62-year-old man after elective colectomy. Sedated, volume-controlled ventilation at 8 mL/kg, sinus rhythm. Haemodynamically stable.',
      t: 'Read the thermodilution series and check the spread between boluses. Switch the line to overdamped and watch PCCI fall until you recalibrate.',
      ft: 'Read CI, SV and SVV. Switch the line to overdamped and watch SV fall, then run a fast-flush test.',
      key: ['All pressures normal: CI 2.5–4.0, PAWP 6–12, RAP 2–6', 'GEDVI, EVLWI and ScvO₂ normal', 'SVV low on 8 mL/kg: not fluid responsive'] },
    hypo: { name: 'Haemorrhage', short: 'Low preload, high SVR',
      p: { vol: 400, c: 1.05, cR: 1.05, svri: 2050, hr: 112, evlwi: 5, hb: 8, lac0: 1.6, rr: 24, swing: 6, pulsus: .08, kA: 1.2 },
      v: '45-year-old man, 2 h after trauma laparotomy for splenic injury. Drain output rising. Sedated and ventilated at 8 mL/kg.',
      t: 'Note the high SVV and low GEDVI. Give 500 mL twice and follow CI, SVV and the Starling position.',
      ft: 'SVV is high on controlled ventilation at 8 mL/kg. Give 500 mL twice and watch SVV fall as CI rises.',
      key: ['Low RAP and low PAWP; low GEDVI', 'Low CI with compensatory high SVR', 'High SVV/PPV on controlled ventilation', 'Low ScvO₂; volume (blood) raises CI briskly'] },
    septic: { name: 'Septic shock + ARDS', short: 'Vasoplegia, high output',
      p: { vol: 590, c: .85, cR: .9, svri: 950, pvr: 160, hr: 118, evlwi: 17, tv: 6, peep: 12, hb: 10, sao2: .94, vo2i: 150, ei: .35, lac0: 3.2, rr: 26, swing: 7, kA: 1.1, pulsus: .06 },
      v: '58-year-old woman with faecal peritonitis and ARDS. Lung-protective ventilation at 6 mL/kg. Warm peripheries, MAP in the 50s.',
      t: 'SVV is falsely low at 6 mL/kg: run a PLR. EVLWI and PVPI show permeability oedema. Start norepinephrine, then check whether PiCCO asks for recalibration.',
      ft: 'Low SVR: FloTrac under-reads CO here (reveal true physiology). SVV is unreliable at 6 mL/kg, so run a PLR. Then start norepinephrine.',
      key: ['Low SVR with high CI: vasoplegia', 'High ScvO₂/SvO₂ with raised lactate: extraction defect', 'EVLWI high with PVPI > 3: permeability oedema', 'Norepinephrine first; prove responsiveness (PLR) before fluid'] },
    lv: { name: 'LV cardiogenic', short: 'Pump failure, high PAWP',
      p: { vol: 980, c: .3, cR: .85, svri: 2400, pvr: 150, hr: 100, evlwi: 13, peep: 8, hb: 12, sao2: .93, vo2i: 120, mr: .1, kPA: 1.5, kA: .9, rr: 26, swing: 8, pulsus: .06 },
      v: '71-year-old man with anterior STEMI after PCI. Cool peripheries, rising lactate, crackles to the mid-zones.',
      t: 'GEDVI is high and GEF low: fluid will not help. Add dobutamine, then remove 500 mL and watch EVLWI.',
      ft: 'Low CI with low SVV and high SVR: fluid will not help. Add dobutamine and watch CI and SVR.',
      key: ['PAWP > 18 with CI < 2.2 ("cold and wet")', 'High SVR, low SvO₂/ScvO₂', 'High GEDVI, low GEF/CFI; EVLWI high with PVPI < 3', 'Dobutamine raises CO and lowers PAWP; fluid does not help'] },
    rv: { name: 'RV failure', short: 'RV infarct pattern',
      p: { vol: 820, c: .9, cR: .35, svri: 2000, pvr: 140, hr: 100, evlwi: 6, hb: 13, sao2: .96, rr: 20, swing: 5, pulsus: .08 },
      v: 'Inferior STEMI with RV involvement, hypotensive after nitrates. Clear lung fields, raised JVP.',
      t: 'CI is low with high CVP and normal EVLWI. Fluid raises CVP more than CI. Compare RAP/PAWP on the Swan–Ganz tab.',
      ft: 'Low CI with high CVP: do not keep giving fluid. FloTrac cannot tell RV from LV failure: check the Swan–Ganz tab.',
      key: ['RAP > PAWP: RA/PAWP > 0.86', 'PAPi < 0.9 (low PA pulse pressure for the RAP)', 'Low PA pressures: the RV cannot generate pressure', 'Fluid raises RAP without raising CO'] },
    pe: { name: 'Massive PE', short: 'Acute RV pressure overload',
      p: { vol: 780, c: 1, cR: .5, svri: 2000, pvr: 650, hr: 124, evlwi: 7, sao2: .88, kPA: 2.1, rr: 28, swing: 9, pulsus: .15, lac0: 1.5 },
      v: '67-year-old woman, day 5 after hip surgery, sudden collapse, SpO₂ 88% on oxygen.',
      t: 'Low CI with high CVP and normal EVLWI: fluid will not help. PiCCO cannot measure PA pressure: the Swan–Ganz tab shows the PVR.',
      ft: 'Low CI, low SVV, high CVP: obstructive pattern. Thrombolysis is in the Swan–Ganz tab interventions.',
      key: ['High RAP, normal or low PAWP', 'PADP − PAWP gradient (DPG) > 7', 'PVR markedly raised; mPAP rarely > 40 acutely', 'Thrombolysis is the definitive fix; fluid worsens it'] },
    tamp: { name: 'Tamponade', short: 'Diastolic equalisation',
      p: { vol: 520, ppc: 18, svri: 2000, hr: 128, evlwi: 6, sao2: .97, rr: 26, swing: 8, pulsus: .42 },
      v: '55-year-old man, 6 h after cardiac surgery: rising CVP, falling drain output, pulsus paradoxus.',
      t: 'Low CI, low GEDVI (compressed chambers), high CVP. Fluid buys little; pericardiocentesis (Swan–Ganz tab) is definitive.',
      ft: 'Low CI with high CVP. A high SVV here is pulsus paradoxus, not fluid responsiveness. Drain the pericardium.',
      key: ['RAP ≈ RVEDP ≈ PADP ≈ PAWP (within ~5 mmHg)', 'Blunted y descent on the RA trace', 'Pulsus paradoxus on the arterial line', 'Pericardiocentesis is definitive'] },
    mr: { name: 'Acute severe MR', short: 'Giant v waves',
      p: { vol: 900, c: .6, cR: .9, svri: 2400, pvr: 180, hr: 115, evlwi: 12, mr: 1, sao2: .91, kPA: 1.6, kA: .9, rr: 26, swing: 8, pulsus: .06 },
      v: '64-year-old woman with posterior MI, new pansystolic murmur and flash pulmonary oedema.',
      t: 'Low forward CI, high EVLWI with PVPI < 3, reduced GEF. Giant v waves are only visible on the Swan–Ganz wedge trace.',
      ft: 'Low CI with high SVR: afterload reduction and inotropy help, vasopressors worsen MR.',
      key: ['Giant v waves on the wedge trace', 'Mean PAWP over-reads LVEDP; read at the a wave', 'v waves can make the wedge look like PA', 'Afterload reduction / inotropy helps; vasopressors worsen MR'] },
    pah: { name: 'Precapillary PH', short: 'Chronic PAH, RV strain',
      p: { vol: 760, c: 1, cR: .75, svri: 1900, pvr: 960, hr: 104, evlwi: 6, sao2: .92, kPA: 3.2, rr: 22, swing: 6, pulsus: .06 },
      v: '45-year-old woman with known pulmonary arterial hypertension, now septic and hypotensive.',
      t: 'Low CI with high CVP and normal EVLWI. PiCCO cannot see the RV afterload: compare with the PA pressures on the Swan–Ganz tab.',
      ft: 'Low CI with high CVP. Avoid large boluses into a failing RV; inhaled NO on the Swan–Ganz tab lowers PVR.',
      key: ['mPAP > 20 with PAWP ≤ 15 and PVR > 2 WU', 'Very high PASP: a hypertrophied RV generates pressure', 'High TPG and DPG', 'Pulmonary vasodilators lower PVR'] },
    overload: { name: 'Fluid overload', short: 'High GEDVI and lung water',
      p: { vol: 1050, c: .9, cR: .9, svri: 1400, pvr: 180, hr: 88, evlwi: 16, peep: 10, hb: 9, sao2: .91, lac0: 1.2, rr: 20, swing: 6 },
      v: '66-year-old woman on day 4 of septic shock, +9 L balance, worsening oxygenation on the ventilator.',
      t: 'EVLWI is high with PVPI below 3 (hydrostatic). Compare with the septic ARDS case, where PVPI is above 3.',
      ft: 'FloTrac cannot see lung water: CI and SVV look acceptable while EVLWI is 16. Reveal true physiology to see what you are missing.',
      key: ['High GEDVI and EVLWI with PVPI < 3', 'Adequate CI: de-resuscitate when stable', 'FloTrac alone cannot see the lung water'] },
    traps: { name: 'Validity traps', short: 'AF, spontaneous efforts',
      p: { vol: 560, c: .9, cR: .9, svri: 1500, pvr: 150, hr: 120, evlwi: 12, rhythm: 'af', vent: 'spont', tv: 6, peep: 10, hb: 11, sao2: .93, vo2i: 140, lac0: 1.5, rr: 28, swing: 7 },
      v: '52-year-old man with pneumonia-ARDS, new atrial fibrillation, light sedation with triggered breaths.',
      t: 'SVV and PPV are meaningless here. Use a PLR with real-time pulse contour CI to decide on fluid.',
      ft: 'AF and spontaneous breaths make SVV meaningless. Run a PLR and read the change in FloTrac CI.',
      key: ['AF and spontaneous efforts: SVV/PPV invalid', 'PLR shows fluid responsiveness despite uninterpretable SVV', 'Raised EVLWI with PVPI around 3'] }
  };

  const s = {}, eff = {};
  let key = 'normal', version = 0, lac = 1, map0 = null;
  const meas = {};

  // forward stroke volume index for a given filling (GEDVI), limited by the weaker ventricle
  function sviAt(G, e = eff) {
    const fill = 1 - Math.exp(-Math.max(0, G - 250) / 280);
    const sL = 58 * e.c * fill;
    const aR = 1 / (1 + Math.max(0, e.pvr / 80 - 2) * .09 / Math.max(.2, e.cR));
    const sR = 58 * e.cR * fill * aR;
    let v = Math.min(sL, sR);
    if (e.ppc > 6) v *= clamp(1 - (e.ppc - 6) / 20, .3, 1);
    v *= 1 - .45 * e.mr;
    if (s.chb) v *= s.pace ? 1 : 1.25;
    if (s.ruptured) v *= .8;
    return v;
  }
  const sviNormal = G => 58 * (1 - Math.exp(-Math.max(0, G - 250) / 280));

  function derived(e = eff) {
    const SVI = sviAt(e.G, e), CI = SVI * e.hr / 1000, CO = CI * BSA;
    const cmv = s.vent === 'cmv', off = cmv ? .74 * .4 * (s.peep - 5) : 0;
    let RAP = 1 + Math.max(0, e.G - 450) / 60 + 14 * Math.max(0, 1 - e.cR) + .008 * Math.max(0, e.pvr - 150);
    let PAWP = 4 + Math.max(0, e.G - 500) / 40 + 14 * Math.max(0, 1 - e.c) * Math.max(0, e.G - 600) / 400 + 8 * e.mr;
    const tamp = e.ppc > 8;
    if (e.ppc > 0) { RAP = Math.max(RAP, e.ppc); PAWP = Math.max(PAWP, e.ppc); }
    const MAP = CI * e.svri / 80 + RAP;
    let PAWPm = PAWP + off, zone3 = true;
    if (cmv && .74 * s.peep > PAWP) { zone3 = false; PAWPm = Math.max(PAWPm, .74 * s.peep * .85); }
    const mPAP = PAWP + e.pvr * CO / 80 + off;
    return { SVI, CI, CO, HR: e.hr, MAP, CVP: clamp(RAP + off, 0, 30), RAP: RAP + off, RAPt: RAP, PAWP: PAWPm, PAWPt: PAWP, mPAP, zone3, tamp, SVR: e.svri / BSA };
  }

  function targets() {
    const baro = (eff.G != null && map0 != null) ? clamp(.35 * (map0 - derived(eff).MAP), -12, 25) : 0;   // baroreflex
    let hr = s.hr + 1.4 * s.dobu + baro + (s.ruptured ? 18 : 0);
    if (s.chb) hr = s.pace ? 80 : 36;
    let pvr = s.pvr * (1 + .1 * s.norad) * (s.ino ? (s.pvr > 300 ? .7 : .92) : 1);
    if (s.lysis) pvr = Math.min(pvr, 280);
    const cmv = s.vent === 'cmv';
    return {
      G: s.vol + 160 * Math.min(s.norad, .6) + (s.plr ? 110 : 0) + (s.eeo && cmv ? 30 : 0) - (cmv ? 4 * (s.peep - 5) : 0),
      c: s.c * (1 + .045 * s.dobu) * (1 + .15 * Math.min(s.norad, .5)),
      cR: (s.lysis ? Math.max(s.cR, .85) : s.cR) * (1 + .045 * s.dobu) * (1 + .1 * Math.min(s.norad, .5)),
      hr: clamp(hr, 30, 170),
      svri: s.svri * (1 + 1.6 * s.norad) * (1 - .012 * s.dobu),
      pvr, evlwi: s.evlwi, ppc: s.ppc, mr: s.mr
    };
  }

  function oxy() {
    const d = derived(eff), hb = s.hb - (s.ruptured ? 1.5 : 0), sao2 = s.sao2 * (s.ruptured ? .84 : 1);
    const do2i = d.CI * 1.34 * hb * sao2 * 10, er = clamp(s.vo2i / do2i * (1 - s.ei), .1, .75), svo2 = sao2 * (1 - er) * 100;
    const shock = d.MAP < 65 || d.CI < 2.5;
    return { do2i, er, svo2, hb, sao2, scv: clamp(svo2 + (shock ? 6 : -2), 20, 95), lacT: s.lac0 + Math.max(0, 330 - do2i) / 40 + Math.max(0, 65 - d.MAP) / 8 };
  }
  // femoral-radial MAP gradient in vasoplegia and high-dose norepinephrine
  const radGrad = () => clamp((1500 - s.svri) / 800, 0, 1) * (3 + 14 * Math.min(s.norad, .6));
  // arterial pulse-pressure variation (fraction) from the Starling slope and tidal volume
  function dynPPV() {
    if (s.vent !== 'cmv' || s.eeo) return .03;
    const dG = 9 * s.tv * (s.chest === 'open' ? .3 : 1), m = sviAt(eff.G);
    return m > 0 ? clamp((sviAt(eff.G + dG / 2) - sviAt(eff.G - dG / 2)) / m, 0, .6) : 0;
  }

  function load(k) {
    key = SCEN[k] ? k : 'normal';
    for (const x in s) delete s[x];
    Object.assign(s, BASE, SCEN[key].p);
    for (const x in eff) delete eff[x];
    map0 = null; Object.assign(eff, targets());
    map0 = derived(eff).MAP; lac = oxy().lacT;
    for (const x in meas) delete meas[x];
    version++;
  }
  function advance(dt) {
    const a = 1 - Math.exp(-dt / 4), tg = targets();
    for (const k in tg) eff[k] += (tg[k] - eff[k]) * a;
    lac += (oxy().lacT - lac) * (1 - Math.exp(-dt / 45));
  }
  function fluid(ml) {
    s.vol = clamp(s.vol + .11 * ml, 300, 1400);
    const pv = s.evlwi * PBW / (.25 * eff.G * BSA);
    s.evlwi += (pv > 3 ? 1.2 : eff.G > 850 ? .8 : .1) * ml / 500;
  }
  function removeFluid(ml) {
    s.vol = clamp(s.vol - .11 * ml, 300, 1400);
    if (s.evlwi > 7) s.evlwi = Math.max(6, s.evlwi - .6 * ml / 500);
  }
  function resetInterventions() {
    const p = { ...BASE, ...SCEN[key].p };
    for (const k of ['vol', 'evlwi', 'ppc', 'norad', 'dobu', 'ino', 'lysis', 'pace', 'plr', 'eeo']) s[k] = p[k];
  }

  load('normal');
  return {
    s, eff, SCEN, KEYS: Object.keys(SCEN), BSA, PBW, meas,
    load, advance, targets, derived, oxy, radGrad, dynPPV, sviAt, sviNormal, fluid, removeFluid, resetInterventions,
    get key() { return key; }, get version() { return version; }, get lac() { return lac; },
    quiz: false
  };
})();
