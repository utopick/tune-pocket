// Shared, offline MIDI device wireframes and per-device assignments. Kept identical in all Pocket apps.
// The drawings are original line sketches of each controller's layout (not manufacturer images), made in code.
// Pads (MIDI channel 10) and knobs (CC numbers, in order) light up by themselves; LEARN pins a drawn control to
// the real one and to a Pocket function.
(function () {
  "use strict";
  // shape = which layout to draw; keys / pads / knobs = how many; base = lowest key's note number;
  // cc0 = the CC number of knob 1 when the model is known (its knobs are cc0, cc0 + 1 ...); without it knobs go by rank
  const PROFILES = {
    synido: { title: "Synido Scale Pocket", shape: "mini", keys: 25, base: 48, pads: 0, knobs: 1, source: "https://www.synido.com/products/scale-pocket-portable-mini-piano-midi-controller-learn-scales-play-music" },
    akai: { title: "Akai MPK mini Play mk3", shape: "mpk", keys: 25, base: 48, pads: 8, knobs: 8, cc0: 1, source: "https://www.akaipro.com/mpk-mini-play-mk3/" },
    korgpad: { title: "Korg nanoPAD · pads", shape: "pads", keys: 0, base: 36, pads: 12, knobs: 0, source: "https://www.korg.com/us/products/computergear/nanopad2/" },
    casio: { title: "Casio PX-S1100", shape: "piano", keys: 88, base: 21, pads: 0, knobs: 0, source: "https://www.casio.com/us/electronic-musical-instruments/product.PX-S1100BK/" },
    novation25: { title: "Novation Launchkey · 25 keys", shape: "lk", keys: 25, base: 48, pads: 16, knobs: 8, cc0: 21, source: "https://novationmusic.com/launchkey" },
    novation37: { title: "Novation Launchkey · 37 keys", shape: "lk", keys: 37, base: 48, pads: 16, knobs: 8, cc0: 21, source: "https://novationmusic.com/launchkey" },
    novation49: { title: "Novation Launchkey · 49 keys", shape: "lk", keys: 49, base: 36, pads: 16, knobs: 8, cc0: 21, source: "https://novationmusic.com/launchkey" },
    novation61: { title: "Novation Launchkey · 61 keys", shape: "lk", keys: 61, base: 36, pads: 16, knobs: 8, cc0: 21, source: "https://novationmusic.com/launchkey" },
    novation88: { title: "Novation Launchkey · 88 keys", shape: "lk", keys: 88, base: 21, pads: 16, knobs: 8, cc0: 21, source: "https://novationmusic.com/launchkey" },
    generic: { title: "MIDI keyboard · generic", shape: "mpk", keys: 25, base: 48, pads: 8, knobs: 8, source: "" },
  };
  const css = `#mdPanel{position:fixed;inset:0;z-index:96;background:#000b;display:flex;align-items:center;justify-content:center;padding:12px;color:#eaf0f5;font:12px/1.45 system-ui}
#mdPanel *{box-sizing:border-box}#mdPanel .mdCard{width:min(900px,100%);max-height:94vh;overflow:auto;background:#1a2029;border:1px solid #54606e;border-radius:14px;padding:16px}
#mdPanel header{display:flex;align-items:center;justify-content:space-between;gap:10px}#mdPanel h2{margin:0;font-size:19px}#mdPanel button,#mdPanel select{background:#303b49;color:#fff;border:1px solid #647486;border-radius:6px;padding:8px;min-height:36px;font:inherit}
#mdPanel button{cursor:pointer}#mdPanel button:focus-visible,#mdPanel select:focus-visible{outline:2px solid #69ccfa}#mdPanel .mdRow{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:12px 0}#mdPanel label{display:grid;gap:3px}#mdPanel small{color:#b4c4d1}#mdPanel a{color:#8bd5fc}
#mdPanel .mdDevice{margin:12px 0}#mdPanel .mdDevice svg{width:100%;height:auto;display:block}
#mdPanel .body{fill:#141a22;stroke:#8aa0b6;stroke-width:2}#mdPanel .sh,#mdPanel .dc{fill:none;stroke:#9fb2c6;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
#mdPanel .dc{stroke:#5f7186}#mdPanel .tk{fill:none;stroke:#47576a;stroke-width:1.3;stroke-dasharray:1.5 5}#mdPanel .hit{fill:transparent;stroke:none}
#mdPanel .nm{fill:#8196ab;font:600 11px system-ui;text-anchor:middle;pointer-events:none}#mdPanel .mdc{cursor:pointer;outline:none}#mdPanel .mdc:focus-visible .sh{stroke:#69ccfa}
#mdPanel .mdc.lit .sh{fill:#38d5fb55;stroke:#38d5fb}#mdPanel .mdc.lit{filter:drop-shadow(0 0 6px #38d5fb)}#mdPanel .mdc.chosen .sh{stroke:#ffbf52;stroke-width:3}
#mdPanel .mdKey{fill:#1b232d;stroke:#9fb2c6;stroke-width:1;cursor:pointer;outline:none}#mdPanel .mdBlack{fill:#090d12}#mdPanel .mdKey:focus-visible{stroke:#69ccfa;stroke-width:2}
#mdPanel .mdKey.lit{fill:#38d5fb;filter:drop-shadow(0 0 5px #38d5fb)}#mdPanel .mdKey.chosen{stroke:#ffbf52;stroke-width:3}
#mdPanel .mdMap{border-top:1px solid #647486;padding-top:10px}#mdPanel .mdMap select{max-width:100%;min-width:200px}#mdPanel .mdHint{min-height:1.5em;color:#ffce84}`;
  const storageKey = "pocket.midi.devices.v1." + location.pathname.split("/").filter(Boolean)[0];
  const load = () => { try { return JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch { return {}; } };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const guess = (s) => {
    if (/scale pocket|synido/i.test(s)) return "synido";
    if (/mpk|akai/i.test(s)) return "akai";
    if (/nanopad|korg/i.test(s)) return "korgpad";
    if (/casio|privia|px-s|cdp/i.test(s)) return "casio";
    if (/launchkey|novation/i.test(s)) { const n = (s.match(/\b(25|37|49|61|88)\b/) || [])[1]; return "novation" + (n || 25); }
    return "generic";
  };
  const noteName = (n) => ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"][n % 12] + (Math.floor(n / 12) - 1);
  // Pads send notes on MIDI channel 10 (36 and up); with more pads than the bank, banks wrap round.
  const padIndex = (pads, note) => (((note - 36) % pads) + pads) % pads;
  // Knobs are matched in the order of their CC numbers (mod wheel, sustain and the like are not knobs).
  const NOT_KNOB = new Set([0, 1, 32, 64, 98, 99, 100, 101]);
  const knobRank = (seen, cc, cc0) => (cc0 != null ? (cc >= cc0 ? cc - cc0 : -1) : NOT_KNOB.has(cc) || cc >= 120 ? -1 : [...seen].filter((x) => !NOT_KNOB.has(x) && x < 120).sort((a, b) => a - b).indexOf(cc));

  // ---------- the wireframes (SVG, 840 wide)
  const W = 840;
  const num = (n) => Math.round(n * 10) / 10;
  const g = (id, label, inner) => `<g class="mdc" data-control="${id}" tabindex="0" role="button" aria-label="${esc(label)}">${inner}</g>`;
  const knob = (id, x, y, r, label) => g(id, label, `<circle class="hit" cx="${x}" cy="${y}" r="${r + 8}"/><circle class="tk" cx="${x}" cy="${y}" r="${r + 5}"/><circle class="sh" cx="${x}" cy="${y}" r="${r}"/><line class="sh" x1="${x}" y1="${y}" x2="${x}" y2="${num(y - r + 4)}" transform="rotate(40 ${x} ${y})"/>`);
  const pad = (id, x, y, s, n) => g(id, "Pad " + n, `<rect class="sh" x="${x}" y="${y}" width="${s}" height="${s}" rx="6"/><rect class="dc" x="${num(x + 5)}" y="${num(y + 5)}" width="${s - 10}" height="${s - 10}" rx="3"/><text class="nm" x="${num(x + s / 2)}" y="${num(y + s / 2 + 4)}">${n}</text>`);
  const padGrid = (x, y, cols, count, s, gap) => Array.from({ length: count }, (_, i) => pad("p" + i, x + (i % cols) * (s + gap), y + Math.floor(i / cols) * (s + gap), s, i + 1)).join("");
  const knobGrid = (x, y, cols, count, dx, dy, r) => Array.from({ length: count }, (_, i) => knob("c" + i, x + (i % cols) * dx, y + Math.floor(i / cols) * dy, r, "Knob " + (i + 1))).join("");
  const wheel = (x, y, w, h) => `<rect class="dc" x="${x}" y="${y}" width="${w}" height="${h}" rx="${w / 2}"/>` + [0.2, 0.35, 0.5, 0.65, 0.8].map((f) => `<line class="dc" x1="${x + 4}" x2="${x + w - 4}" y1="${num(y + h * f)}" y2="${num(y + h * f)}"/>`).join("");
  const joystick = (x, y, r) => `<circle class="dc" cx="${x}" cy="${y}" r="${r}"/><circle class="dc" cx="${x}" cy="${y}" r="${num(r * 0.5)}"/><path class="dc" d="M${x - r} ${y}h${2 * r}M${x} ${y - r}v${2 * r}"/>`;
  const btn = (x, y, w, h) => `<rect class="dc" x="${x}" y="${y}" width="${w}" height="${h}" rx="4"/>`;
  const btnRow = (x, y, n, w, h, gap) => Array.from({ length: n }, (_, i) => btn(x + i * (w + gap), y, w, h)).join("");
  const screen = (x, y, w, h) => `<rect class="dc" x="${x}" y="${y}" width="${w}" height="${h}" rx="4"/><path class="dc" d="M${x + 8} ${y + h * 0.35}h${w * 0.5}M${x + 8} ${y + h * 0.65}h${w * 0.3}"/>`;
  const speaker = (x, y, w, h) => Array.from({ length: Math.floor(h / 10) }, (_, i) => `<line class="dc" x1="${x}" x2="${x + w}" y1="${y + i * 10}" y2="${y + i * 10}" stroke-dasharray="6 5"/>`).join("");
  function keysSvg(x, y, w, h, n, base) {
    const black = (m) => [1, 3, 6, 8, 10].includes(m % 12);
    let whites = 0;
    for (let i = 0; i < n; i++) if (!black(base + i)) whites++;
    const kw = w / Math.max(1, whites), bw = kw * 0.62;
    let wi = 0, out = "", blk = "";
    for (let i = 0; i < n; i++) {
      const m = base + i, lab = `data-control="k${m}" data-note="${m}" tabindex="0" role="button" aria-label="${noteName(m)}"`;
      if (black(m)) {
        const cx = Math.min(Math.max(x + wi * kw, x + bw / 2), x + w - bw / 2);
        blk += `<rect class="mdKey mdBlack" ${lab} x="${num(cx - bw / 2)}" y="${y}" width="${num(bw)}" height="${num(h * 0.6)}" rx="2"><title>${noteName(m)}</title></rect>`;
      } else {
        out += `<rect class="mdKey mdWhite" ${lab} x="${num(x + wi * kw)}" y="${y}" width="${num(kw)}" height="${h}" rx="3"><title>${noteName(m)}</title></rect>`;
        if (m % 12 === 0 && kw >= 11) out += `<text class="nm" x="${num(x + wi * kw + kw / 2)}" y="${y + h - 7}" style="font-size:${kw > 24 ? 11 : 8}px">${noteName(m)}</text>`;
        wi++;
      }
    }
    return out + blk;
  }
  function schematic(p, base) {
    let h = 0, inner = "";
    const keys = (y, kh, x0 = 22) => keysSvg(x0, y, W - 2 * x0, kh, p.keys, base);
    switch (p.shape) {
      case "mpk": // joystick, 4x2 pads, screen, 4x2 knobs, speaker; the keys along the bottom
        h = 290;
        inner = joystick(62, 78, 32) + padGrid(120, 22, 4, p.pads, 54, 8) + screen(392, 34, 96, 50) + btnRow(392, 102, 3, 26, 22, 8) + knobGrid(546, 48, 4, p.knobs, 60, 64, 19) + speaker(776, 30, 38, 110) + keys(170, 100);
        break;
      case "lk": // wheels, screen and buttons, a row of 8 knobs over 2x8 pads, a fader; the keys at the bottom
        h = 330;
        inner = wheel(24, 24, 26, 150) + wheel(60, 24, 26, 150) + screen(112, 30, 170, 54) + btnRow(112, 104, 3, 52, 26, 8) + btnRow(112, 142, 3, 52, 26, 8) + knobGrid(352, 44, 8, p.knobs, 50, 0, 16) + padGrid(334, 86, 8, p.pads, 42, 8) + btn(772, 30, 14, 146) + btn(764, 70, 30, 22) + keys(200, 112);
        break;
      case "mini": // a small keyboard: one knob, a display, scale buttons
        h = 230;
        inner = knob("c0", 58, 52, 20, "Knob 1") + screen(112, 28, 130, 50) + btnRow(272, 34, 6, 42, 32, 10) + keys(112, 100);
        break;
      case "piano": // 88 keys under a slim panel
        h = 210;
        inner = `<circle class="dc" cx="38" cy="38" r="10"/>` + `<rect class="dc" x="92" y="33" width="130" height="10" rx="5"/><rect class="dc" x="150" y="27" width="14" height="22" rx="4"/>` + btnRow(270, 24, 6, 40, 28, 10) + keys(80, 114, 14);
        break;
      case "pads": // pad controller: X-Y pad and 4x3 pads, no keys
        h = 340;
        inner = `<rect class="dc" x="44" y="34" width="200" height="272" rx="8"/><circle class="dc" cx="144" cy="170" r="14"/><path class="dc" d="M144 34v272M44 170h200"/>` + padGrid(292, 34, 4, p.pads, 84, 12);
        break;
    }
    return `<svg viewBox="0 0 ${W} ${h}" role="img" aria-label="${esc(p.title)} wireframe"><rect class="body" x="1" y="1" width="${W - 2}" height="${h - 2}" rx="16"/>${inner}</svg>`;
  }

  function createMidiPanel(MI, run, send) {
    const saved = load();
    let el, device = "", profile = "", selected = "", learning = false, base = 48;
    const flash = new Map(), seenCC = {};
    const persist = () => localStorage.setItem(storageKey, JSON.stringify(saved));
    const record = () => (saved[device] = saved[device] || { profile: guess(device), map: {}, controls: {} });
    const prof = () => PROFILES[profile] || PROFILES.generic;
    function sourceOptions() {
      if (!el) return;
      const sel = el.querySelector("#mdSource");
      sel.innerHTML = MI.names.map((n) => `<option value="${esc(n)}">${esc(n)}</option>`).join("");
      if (!MI.names.includes(device)) device = MI.names[0] || "";
      sel.value = device;
    }
    function open() {
      if (!MI.names.length) return;
      if (el) return;
      device = MI.names[0];
      const style = document.createElement("style"); style.textContent = css; style.id = "mdStyle"; document.head.appendChild(style);
      el = document.createElement("div"); el.id = "mdPanel";
      el.innerHTML = `<div class="mdCard" role="dialog" aria-modal="true" aria-label="MIDI device diagram"><header><h2>MIDI DEVICE · LIVE DIAGRAM</h2><button data-do="close">DONE</button></header><div class="mdRow"><label>Input port<select id="mdSource"></select></label><label>Diagram<select id="mdProfile"></select></label></div><small>A line sketch of the layout, not to scale. Pick the model that matches yours. Keys, pads (MIDI channel 10) and knobs light up as you use them; knobs are matched in the order of their CC numbers. LEARN pins a drawn control to the real one.</small><div class="mdDevice"></div><div class="mdMap"><div class="mdRow"><strong id="mdSelected">Select a key, pad or knob</strong><label>Pocket function<select id="mdAction"></select></label><button data-do="learn">LEARN FROM HARDWARE</button><button data-do="clear">CLEAR CONTROL</button></div><div class="mdHint" id="mdHint"></div><small>Choose a diagram control and a Pocket function, then press or turn its real counterpart. Assignments are saved for this input port and this Pocket app. Unassigned keys still play normally. Click a drawn key to preview it.</small><p><a id="mdSourceLink" target="_blank" rel="noopener noreferrer">Manufacturer reference ↗</a></p></div></div>`;
      document.body.appendChild(el);
      sourceOptions();
      el.querySelector("#mdSource").onchange = (e) => { device = e.target.value; learning = false; selected = ""; draw(); };
      el.querySelector("#mdProfile").onchange = (e) => { profile = e.target.value; record().profile = profile; persist(); selected = ""; draw(); };
      el.querySelector("#mdAction").onchange = () => { if (selected) setAssignment(selected, el.querySelector("#mdAction").value); };
      const pick = (control) => { select(control.dataset.control); if (control.dataset.control.startsWith("k")) preview(+control.dataset.control.slice(1)); };
      el.onclick = (e) => {
        const control = e.target.closest("[data-control]");
        if (control) return pick(control);
        const action = e.target.closest("[data-do]")?.dataset.do;
        if (action === "close") close();
        if (action === "learn" && selected) { learning = true; hint("Now press the matching hardware control on " + device + "."); }
        if (action === "clear" && selected) { clearAssignment(selected); hint("Assignment removed."); }
      };
      el.onkeydown = (e) => {
        const control = (e.key === "Enter" || e.key === " ") && e.target.closest?.("[data-control]");
        if (control) { e.preventDefault(); pick(control); }
      };
      draw();
    }
    function close() { learning = false; el?.remove(); el = null; document.getElementById("mdStyle")?.remove(); }
    function hint(text) { if (el) el.querySelector("#mdHint").textContent = text; }
    function draw() {
      if (!el) return;
      profile = record().profile || guess(device);
      const p = prof(); base = p.base;
      const sel = el.querySelector("#mdProfile");
      sel.innerHTML = Object.entries(PROFILES).map(([id, x]) => `<option value="${id}">${esc(x.title)}</option>`).join(""); sel.value = profile;
      const link = el.querySelector("#mdSourceLink"); link.hidden = !p.source; link.href = p.source;
      drawDevice(); select("");
      hint("Listening to " + device + ". Press a key, a pad or turn a knob to see it light up.");
    }
    function drawDevice() {
      if (el) el.querySelector(".mdDevice").innerHTML = schematic(prof(), base);
    }
    function select(id) {
      selected = id; if (!el) return;
      el.querySelectorAll(".chosen").forEach((x) => x.classList.remove("chosen"));
      el.querySelector(`[data-control="${id}"]`)?.classList.add("chosen");
      el.querySelector("#mdSelected").textContent = id ? (id[0] === "k" ? noteName(+id.slice(1)) : id[0] === "p" ? `Pad ${+id.slice(1) + 1}` : `Knob ${+id.slice(1) + 1}`) : "Select a key, pad or knob";
      const actions = MI.actions(), groups = [...new Set(actions.map((a) => a.group))];
      const action = el.querySelector("#mdAction");
      action.innerHTML = `<option value="">Unassigned · normal key</option>` + groups.map((gr) => `<optgroup label="${esc(gr)}">${actions.filter((a) => a.group === gr).map((a) => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join("")}</optgroup>`).join("");
      action.value = id ? (record().controls[id]?.action || "") : "";
      action.disabled = !id;
      const binding = id && record().controls[id]?.key;
      hint(binding ? `Hardware: ${binding} · ${action.value ? "assigned" : "normal"}` : id ? "Choose a function and press LEARN to bind the real control." : "Select a drawn control to assign it.");
    }
    function setAssignment(id, action) {
      const r = record(), c = r.controls[id] || (r.controls[id] = {});
      c.action = action;
      if (c.key) { if (action) r.map[c.key] = action; else delete r.map[c.key]; }
      persist(); select(id);
    }
    function clearAssignment(id) {
      const r = record(), c = r.controls[id];
      if (c?.key) delete r.map[c.key];
      delete r.controls[id]; persist(); select(id);
    }
    function preview(n) {
      send([0x90, n, 90], device);
      setTimeout(() => send([0x80, n, 0], device), 170);
    }
    const lit = (id, on) => el?.querySelector(`[data-control="${id}"]`)?.classList.toggle("lit", on);
    const blink = (id) => { lit(id, true); clearTimeout(flash.get(id)); flash.set(id, setTimeout(() => lit(id, false), 180)); };
    function observe(data, from) {
      const [st, a, b] = data, cmd = st & 0xf0;
      if (st >= 0xf0 || !from) return;
      const noteOn = cmd === 0x90 && b > 0, noteOff = cmd === 0x80 || (cmd === 0x90 && b === 0), cc = cmd === 0xb0;
      const key = (cc ? "c" : "n") + (st & 15) + ":" + a;
      if (learning && el && from === device && (noteOn || cc && b > 0)) {
        const r = record(), c = r.controls[selected] || (r.controls[selected] = {});
        if (c.key) delete r.map[c.key];
        for (const [id, other] of Object.entries(r.controls)) if (id !== selected && other.key === key) delete other.key;
        delete r.map[key];
        c.key = key; if (c.action) r.map[key] = c.action;
        persist(); learning = false; select(selected);
      }
      if (cc) (seenCC[from] = seenCC[from] || new Set()).add(a);
      if (!el || from !== device) return;
      const p = prof(), bound = Object.entries(record().controls).find(([, v]) => v.key === key)?.[0];
      if (noteOn || noteOff) {
        // a learned pad, else any note on channel 10 is a pad; everything else is a key
        const id = bound && !bound.startsWith("k") ? bound : !bound && (st & 15) === 9 && p.pads ? "p" + padIndex(p.pads, a) : "";
        if (id) {
          lit(id, noteOn);
          if (noteOn) hint(`Pad ${+id.slice(1) + 1} · note ${a} · channel ${(st & 15) + 1}`);
          return;
        }
        if (!p.keys) return;
        if (a < base || a >= base + p.keys) { base = Math.max(0, Math.min(127 - p.keys, Math.floor(a / 12) * 12)); drawDevice(); }
        lit("k" + a, noteOn);
      } else if (cc) {
        const r = bound && !bound.startsWith("k") ? bound : knobRank(seenCC[from], a, p.cc0);
        const id = typeof r === "string" ? r : r >= 0 && r < p.knobs ? "c" + r : "";
        if (id) { blink(id); hint(`Knob ${+id.slice(1) + 1} · CC ${a} = ${b}`); }
      }
    }
    function route(from, key, cc, on, value) {
      const id = saved[from]?.map?.[key], action = id && MI.actions().find((a) => a.id === id);
      if (!action) return false;
      run(action, from + "/" + key, cc, on, value);
      return true;
    }
    return { open, close, observe, route };
  }
  window.createMidiPanel = createMidiPanel;
  window.pocketMidiHelpers = { padIndex, knobRank, guess };
})();
