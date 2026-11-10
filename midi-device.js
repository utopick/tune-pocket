// Shared, offline MIDI device schematic and per-device assignments. Kept identical in all Pocket apps.
// The drawings are original diagrams, not manufacturer product images.
(function () {
  "use strict";
  const PROFILES = {
    synido: { title: "Synido Scale Pocket", keys: 25, base: 48, pads: 0, knobs: 1, source: "https://www.synido.com/products/scale-pocket-portable-mini-piano-midi-controller-learn-scales-play-music" },
    akai: { title: "Akai MPK mini Play mk3", keys: 25, base: 48, pads: 8, knobs: 4, source: "https://www.akaipro.com/mpk-mini-play-mk3/" },
    casio: { title: "Casio PX-S1100", keys: 88, base: 21, pads: 0, knobs: 0, source: "https://www.casio.com/us/electronic-musical-instruments/product.PX-S1100BK/" },
    novation25: { title: "Novation Launchkey · 25-key diagram", keys: 25, base: 48, pads: 16, knobs: 8, source: "https://novationmusic.com/launchkey" },
    novation37: { title: "Novation Launchkey · 37-key diagram", keys: 37, base: 48, pads: 16, knobs: 8, source: "https://novationmusic.com/launchkey" },
    novation49: { title: "Novation Launchkey · 49-key diagram", keys: 49, base: 48, pads: 16, knobs: 8, source: "https://novationmusic.com/launchkey" },
    novation61: { title: "Novation Launchkey · 61-key diagram", keys: 61, base: 36, pads: 16, knobs: 8, source: "https://novationmusic.com/launchkey" },
    novation88: { title: "Novation Launchkey · 88-key diagram", keys: 88, base: 21, pads: 16, knobs: 8, source: "https://novationmusic.com/launchkey" },
    generic: { title: "MIDI keyboard · generic diagram", keys: 25, base: 48, pads: 16, knobs: 8, source: "" },
  };
  const css = `#mdPanel{position:fixed;inset:0;z-index:96;background:#000b;display:flex;align-items:center;justify-content:center;padding:12px;color:#eaf0f5;font:12px/1.45 system-ui}
#mdPanel *{box-sizing:border-box}#mdPanel .mdCard{width:min(850px,100%);max-height:94vh;overflow:auto;background:#1a2029;border:1px solid #54606e;border-radius:14px;padding:16px}
#mdPanel header{display:flex;align-items:center;justify-content:space-between;gap:10px}#mdPanel h2{margin:0;font-size:19px}#mdPanel button,#mdPanel select{background:#303b49;color:#fff;border:1px solid #647486;border-radius:6px;padding:8px;min-height:36px;font:inherit}
#mdPanel button{cursor:pointer}#mdPanel button:focus-visible,#mdPanel select:focus-visible{outline:2px solid #69ccfa}#mdPanel .mdRow{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:12px 0}#mdPanel label{display:grid;gap:3px}#mdPanel small{color:#b4c4d1}#mdPanel a{color:#8bd5fc}
#mdPanel .mdDevice{background:#30343a;border:4px solid #101318;border-radius:12px;padding:14px;margin:12px 0;overflow-x:auto}#mdPanel .mdControls{display:flex;flex-wrap:wrap;align-items:center;gap:9px;min-height:45px;margin-bottom:12px}
#mdPanel .mdPads{display:grid;grid-template-columns:repeat(8,32px);gap:5px}#mdPanel .mdPads button{width:32px;height:32px;min-height:32px;padding:0;background:#58515c}#mdPanel .mdKnobs{display:flex;gap:6px;flex-wrap:wrap}#mdPanel .mdKnobs button{width:32px;height:32px;min-height:32px;border-radius:50%;padding:0}
#mdPanel .mdKeys{display:flex;height:105px;min-width:max-content;position:relative}#mdPanel .mdKey{position:relative;display:block;flex:none;border:1px solid #292d34;border-radius:0 0 3px 3px;padding:0;min-height:0;font:9px system-ui}
#mdPanel .mdWhite{width:18px;height:105px;background:#f2f1ec;color:#333;z-index:1;align-self:flex-start}#mdPanel .mdBlack{width:12px;height:62px;background:#111923;color:#fff;z-index:2;margin-left:-6px;margin-right:-6px;align-self:flex-start}
#mdPanel .mdKey:focus-visible{z-index:3}#mdPanel .lit{background:#38d5fb!important;color:#09232c!important;box-shadow:0 0 14px #38d5fb}#mdPanel .chosen{outline:3px solid #ffbf52;outline-offset:2px;z-index:4}
#mdPanel .mdMap{border-top:1px solid #647486;padding-top:10px}#mdPanel .mdMap select{max-width:100%;min-width:200px}#mdPanel .mdHint{min-height:1.5em;color:#ffce84}`;
  const storageKey = "pocket.midi.devices.v1." + location.pathname.split("/").filter(Boolean)[0];
  const load = () => { try { return JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch { return {}; } };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const guess = (s) => /scale pocket|synido/i.test(s) ? "synido" : /mpk mini play|akai/i.test(s) ? "akai" : /casio|privia|px-s/i.test(s) ? "casio" : /launchkey|novation/i.test(s) ? "novation25" : "generic";
  const noteName = (n) => ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"][n % 12] + (Math.floor(n / 12) - 1);
  function createMidiPanel(MI, run, send) {
    const saved = load();
    let el, device = "", profile = "", selected = "", learning = false, base = 48;
    const flash = new Map();
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
      el.innerHTML = `<div class="mdCard" role="dialog" aria-modal="true" aria-label="MIDI device diagram"><header><h2>MIDI DEVICE · LIVE DIAGRAM</h2><button data-do="close">DONE</button></header><div class="mdRow"><label>Input port<select id="mdSource"></select></label><label>Diagram<select id="mdProfile"></select></label></div><small>Original schematic, not to scale. Choose the actual keyboard size. Ports may include a separate DAW input. Octave and pad banks can change note numbers.</small><div class="mdDevice"><div class="mdControls"><div class="mdKnobs"></div><div class="mdPads"></div></div><div class="mdKeys"></div></div><div class="mdMap"><div class="mdRow"><strong id="mdSelected">Select a key, pad or knob</strong><label>Pocket function<select id="mdAction"></select></label><button data-do="learn">LEARN FROM HARDWARE</button><button data-do="clear">CLEAR CONTROL</button></div><div class="mdHint" id="mdHint"></div><small>Choose a diagram control and a Pocket function, then press or turn its real counterpart. Assignments are saved for this input port and this Pocket app. Unassigned keys still play normally. Click a drawn key to preview it.</small><p><a id="mdSourceLink" target="_blank" rel="noopener noreferrer">Manufacturer reference ↗</a></p></div></div>`;
      document.body.appendChild(el);
      sourceOptions();
      el.querySelector("#mdSource").onchange = (e) => { device = e.target.value; learning = false; selected = ""; draw(); };
      el.querySelector("#mdProfile").onchange = (e) => { profile = e.target.value; record().profile = profile; persist(); selected = ""; draw(); };
      el.querySelector("#mdAction").onchange = () => { if (selected) setAssignment(selected, el.querySelector("#mdAction").value); };
      el.onclick = (e) => {
        const control = e.target.closest("[data-control]");
        if (control) { select(control.dataset.control); if (control.dataset.control.startsWith("k")) preview(+control.dataset.control.slice(1)); return; }
        const action = e.target.closest("[data-do]")?.dataset.do;
        if (action === "close") close();
        if (action === "learn" && selected) { learning = true; hint("Now press the matching hardware control on " + device + "."); }
        if (action === "clear" && selected) { clearAssignment(selected); hint("Assignment removed."); }
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
      el.querySelector(".mdKnobs").innerHTML = Array.from({length:p.knobs},(_,i)=>`<button data-control="c${i}" title="Knob ${i+1}">◉</button>`).join("");
      el.querySelector(".mdPads").innerHTML = Array.from({length:p.pads},(_,i)=>`<button data-control="p${i}" title="Pad ${i+1}">${i+1}</button>`).join("");
      drawKeys(); select("");
      hint("Listening to " + device + ". Press a key to see it light up.");
    }
    function drawKeys() {
      if (!el) return;
      el.querySelector(".mdKeys").innerHTML = Array.from({length:prof().keys},(_,i)=>{
        const n = base + i, black = [1,3,6,8,10].includes(n%12);
        return `<button class="mdKey ${black ? "mdBlack" : "mdWhite"}" data-control="k${n}" data-note="${n}" title="${noteName(n)}"></button>`;
      }).join("");
    }
    function select(id) {
      selected = id; if (!el) return;
      el.querySelectorAll(".chosen").forEach((x)=>x.classList.remove("chosen"));
      el.querySelector(`[data-control="${id}"]`)?.classList.add("chosen");
      el.querySelector("#mdSelected").textContent = id ? (id[0] === "k" ? noteName(+id.slice(1)) : id[0] === "p" ? `Pad ${+id.slice(1)+1}` : `Knob ${+id.slice(1)+1}`) : "Select a key, pad or knob";
      const actions = MI.actions(), groups = [...new Set(actions.map((a)=>a.group))];
      const action = el.querySelector("#mdAction");
      action.innerHTML = `<option value="">Unassigned · normal key</option>` + groups.map((g)=>`<optgroup label="${esc(g)}">${actions.filter((a)=>a.group===g).map((a)=>`<option value="${esc(a.id)}">${esc(a.name)}</option>`).join("")}</optgroup>`).join("");
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
      send([0x90,n,90],device);
      setTimeout(()=>send([0x80,n,0],device),170);
    }
    function observe(data, from) {
      const [st,a,b] = data, cmd = st & 0xf0;
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
      if (!el || from !== device) return;
      if (noteOn || noteOff) {
        if (a < base || a >= base + prof().keys) { base = Math.max(0,Math.min(127-prof().keys,Math.floor(a/12)*12)); drawKeys(); }
        const k = el.querySelector(`[data-note="${a}"]`);
        k?.classList.toggle("lit",noteOn);
      }
      const bound = Object.entries(record().controls).find(([,v])=>v.key===key)?.[0];
      if (bound && !bound.startsWith("k")) {
        const node = el.querySelector(`[data-control="${bound}"]`);
        if (node) { node.classList.add("lit"); clearTimeout(flash.get(bound)); flash.set(bound,setTimeout(()=>node.classList.remove("lit"),180)); }
      }
    }
    function route(from,key,cc,on,value) {
      const id = saved[from]?.map?.[key], action = id && MI.actions().find((a)=>a.id===id);
      if (!action) return false;
      run(action,from+"/"+key,cc,on,value);
      return true;
    }
    return {open,close,observe,route};
  }
  window.createMidiPanel = createMidiPanel;
})();
