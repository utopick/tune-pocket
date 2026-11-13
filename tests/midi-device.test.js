// Run with: node --test tests/midi-device.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
// the panel lives in index.html, in <script id="midi-device">
const source = fs.readFileSync(require.resolve("../index.html"), "utf8").match(/<script id="midi-device">([\s\S]*?)<\/script>/)[1];

test("learned bindings route only on their own input and Pocket app", () => {
  const storage = new Map();
  const key = "pocket.midi.devices.v1.tune-pocket";
  storage.set(key, JSON.stringify({ "MPK mini Play mk3": { profile: "akai", map: { "n9:36": "play" }, controls: { p0: { key: "n9:36", action: "play" } } } }));
  const context = {
    performance, setTimeout, window: {}, location: { pathname: "/tune-pocket/" },
    localStorage: { getItem: (k) => storage.get(k), setItem: (k, v) => storage.set(k, v) },
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  const calls = [];
  const MI = { names: ["MPK mini Play mk3", "Launchkey MIDI"], actions: () => [{ id: "play", group: "Transport", name: "PLAY", kind: "tap" }] };
  const panel = context.window.createMidiPanel(MI, (...args) => calls.push(args), () => {});
  assert.equal(panel.route("Launchkey MIDI", "n9:36", false, true, 100), false);
  assert.equal(panel.route("MPK mini Play mk3", "n0:36", false, true, 100), false);
  assert.equal(panel.route("MPK mini Play mk3", "n9:36", false, true, 100), true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][1], "MPK mini Play mk3/n9:36");
  assert.equal(calls[0][3], true);
  // A different Pocket app at the same localhost origin does not inherit these mappings.
  const other = { ...context, performance, setTimeout, window: {}, location: { pathname: "/sing-pocket/" } };
  vm.createContext(other);
  vm.runInContext(source, other);
  assert.equal(other.window.createMidiPanel(MI, () => {}, () => {}).route("MPK mini Play mk3", "n9:36", false, true, 100), false);
});

test("real-time clock and unmapped messages pass through", () => {
  const context = { performance, setTimeout, window: {}, location: { pathname: "/track-pocket/" }, localStorage: { getItem: () => null } };
  vm.createContext(context);
  vm.runInContext(source, context);
  const panel = context.window.createMidiPanel({ names: [], actions: () => [] }, () => { throw Error("unexpected action"); }, () => {});
  panel.observe([0xf8], "Launchkey MIDI");
  panel.observe([0x90, 60, 100], "Launchkey MIDI");
  assert.equal(panel.route("Launchkey MIDI", "n0:60", false, true, 100), false);
});

test("pads and knobs are matched without learning", () => {
  const context = { performance, setTimeout, window: {}, location: { pathname: "/track-pocket/" }, localStorage: { getItem: () => null } };
  vm.createContext(context);
  vm.runInContext(source, context);
  const { padIndex, knobRank, guess } = context.window.pocketMidiHelpers;
  assert.equal(padIndex(8, 36), 0);
  assert.equal(padIndex(8, 43), 7);
  assert.equal(padIndex(8, 44), 0); // the second pad bank wraps round
  assert.equal(padIndex(16, 51), 15);
  assert.equal(knobRank(new Set(), 23, 21), 2); // a known model: knob = CC - first CC
  assert.equal(knobRank(new Set(), 20, 21), -1);
  assert.equal(knobRank(new Set([70, 72, 74]), 72), 1); // unknown model: by rank among the CCs seen
  assert.equal(knobRank(new Set([64, 70]), 64), -1); // the sustain pedal is not a knob
  assert.equal(guess("Launchkey MK4 37 MIDI Out"), "novation37");
  // the Play mk3 sends a drum kit on its pads and its own CCs on its knobs (a real report): pads 1-4 are the lower row
  const mpk = { banks: [[36, 38, 42, 46, 48, 45, 51, 49], [60, 62, 63, 64, 58, 75, 56, 77]], ccs: [74, 71, 91, 93, 73, 72, 6] };
  assert.deepEqual([36, 38, 42, 46, 48, 45, 51, 49].map((n) => padIndex(8, n, mpk.banks)), [0, 1, 2, 3, 4, 5, 6, 7]);
  assert.deepEqual([60, 62, 63, 64, 58, 75, 56, 77].map((n) => padIndex(8, n, mpk.banks)), [0, 1, 2, 3, 4, 5, 6, 7]);
  assert.equal(padIndex(8, 37, mpk.banks), 1); // a note outside the lists falls back to the 36-based count
  assert.deepEqual([74, 71, 91, 93, 73, 72, 6].map((cc) => knobRank(new Set(), cc, 2, mpk.ccs)), [0, 1, 2, 3, 4, 5, 6]);
  assert.equal(knobRank(new Set(), 98, 2, mpk.ccs), -1);
  assert.equal(guess("MPK mini Play mk3"), "akai");
  assert.equal(guess("nanoPAD2"), "korgpad");
});

test("the starting assignment: pads and knobs do what the app says until the user changes it", () => {
  const storage = new Map();
  const context = { performance, setTimeout, window: {}, location: { pathname: "/track-pocket/" }, localStorage: { getItem: (k) => storage.get(k), setItem: (k, v) => storage.set(k, v) } };
  vm.createContext(context);
  vm.runInContext(source, context);
  const calls = [];
  const MI = {
    names: ["MPK mini Play mk3"], map: {},
    defaults: () => ({ knobs: [["vol0", "VOL CH1"], ["bpm", "BPM"]], pads: [["live0", "PAT A"]], padText: "DRUM" }),
    actions: () => ["vol0", "bpm", "live0", "other"].map((id) => ({ id, group: "g", name: id.toUpperCase(), kind: "tap" })),
  };
  const dev = "MPK mini Play mk3";
  const panel = context.window.createMidiPanel(MI, (a) => calls.push(a.id), () => {});
  panel.observe([0xb0, 74, 64], dev); // the first CC the MPK knob sends: knob 1
  assert.equal(panel.fallback(dev, "c0:74", true, false, 64), true);
  assert.equal(panel.fallback(dev, "c0:71", true, false, 64), true);
  assert.equal(panel.fallback(dev, "c0:91", true, false, 64), false); // knob 3 has no default
  assert.equal(panel.fallback(dev, "n9:36", false, true, 100), true); // pad 1 (channel 10)
  assert.equal(panel.fallback(dev, "n9:37", false, true, 100), false); // a label only: it plays as a note
  assert.equal(panel.fallback(dev, "n0:36", false, true, 100), false); // a key, not a pad
  assert.deepEqual(calls, ["vol0", "bpm", "live0"]);
  // the user's own assignment wins, and the action is not also on its default control
  MI.map["c0:9"] = "bpm";
  assert.equal(panel.fallback(dev, "c0:71", true, false, 64), false);
  // CLEAR turns every default off
  panel.defaultsOff();
  assert.equal(panel.fallback(dev, "c0:74", true, false, 64), false);
  assert.equal(panel.fallback(dev, "n9:36", false, true, 100), false);
  // a model with unknown knob numbers gets no knob defaults
  const gen = context.window.createMidiPanel({ ...MI, names: ["Some keyboard"] }, (a) => calls.push(a.id), () => {});
  gen.observe([0xb0, 70, 1], "Some keyboard");
  assert.equal(gen.fallback("Some keyboard", "c0:70", true, false, 1), false);
  assert.equal(gen.fallback("Some keyboard", "n9:36", false, true, 100), true); // but its pads (8 on the generic layout) do
});

test("Korg nanoPAD2 pads (channel 1, 16 pads) and the nanoKEY2 are recognised", () => {
  const context = { performance, setTimeout, window: {}, location: { pathname: "/sing-pocket/" }, localStorage: { getItem: () => null } };
  vm.createContext(context);
  vm.runInContext(source, context);
  assert.equal(context.window.pocketMidiHelpers.guess("nanoPAD2 PAD"), "korgpad");
  assert.equal(context.window.pocketMidiHelpers.guess("nanoKEY2 KEYBOARD"), "korgkey");
  const calls = [];
  const MI = { names: ["nanoPAD2 PAD"], map: {}, defaults: () => ({ pads: Array.from({ length: 16 }, (_, i) => ["p" + i, "PAD " + i]) }), actions: () => Array.from({ length: 16 }, (_, i) => ({ id: "p" + i, group: "g", name: "P" + i, kind: "tap" })) };
  const panel = context.window.createMidiPanel(MI, (a) => calls.push(a.id), () => {});
  assert.equal(panel.fallback("nanoPAD2 PAD", "n0:36", false, true, 100), true); // pad 1 sends on channel 1
  assert.equal(panel.fallback("nanoPAD2 PAD", "n0:51", false, true, 100), true); // pad 16
  assert.equal(panel.fallback("nanoPAD2 PAD", "n9:36", false, true, 100), false); // channel 10 is not this model's pad channel
  assert.deepEqual(calls, ["p0", "p15"]);
});

test("a device map read from a file keeps only known fields in range", () => {
  const context = { performance, setTimeout, window: {}, location: { pathname: "/track-pocket/" }, localStorage: { getItem: () => null } };
  vm.createContext(context);
  vm.runInContext(source, context);
  const { vetHw } = context.window.pocketMidiHelpers;
  const good = vetHw({ keys: 25, pads: 8, padCh: 9, padNotes: [[36, 38]], ccs: [74, 6], sus: 64, bend: 0, mod: 1, expr: 11, fn: { play: "rt:250", stop: "n9:80", f1: "c0:117", rec: "mmc:6" } });
  assert.deepEqual(JSON.parse(JSON.stringify(good)), { keys: 25, pads: 8, padCh: 9, padNotes: [[36, 38]], ccs: [74, 6], knobs: 2, cc0: 0, sus: 64, bend: 0, mod: 1, expr: 11, fn: { play: "rt:250", stop: "n9:80", f1: "c0:117", rec: "mmc:6" } });
  assert.equal(vetHw({ keys: 9999, ccs: ["x"], padNotes: [[300]], fn: { play: "<script>", evil: "n0:1" } }), null);
  assert.equal(vetHw("x"), null);
  assert.deepEqual(Object.keys(vetHw({ keys: 61, fn: { play: "n0:300", stop: "rt:252" } }).fn), ["stop"]);
});

test("the MPK Play mk3 layout is told from the messages only one layout sends", () => {
  const storage = new Map();
  const context = { performance, setTimeout, window: {}, location: { pathname: "/track-pocket/" }, localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v) } };
  vm.createContext(context);
  vm.runInContext(source, context);
  const MI = { names: ["MPK mini Play mk3"], map: {}, actions: () => [] };
  const panel = context.window.createMidiPanel(MI, () => {}, () => {});
  const mpk = "MPK mini Play mk3";
  assert.equal(panel.padNo(mpk, 38), 1); // the internal-sounds layout (drum kit order) until told otherwise
  panel.observe([0xb0, 70, 20], mpk); // CC 70 only exists in the standard layout
  assert.equal(panel.padNo(mpk, 38), 2); // pads 36 to 43 in order
  assert.equal(panel.padNo(mpk, 46), 2); // bank B, 44 to 51
  assert.equal(panel.susCc(mpk), 64);
  panel.observe([0xb0, 91, 20], mpk); // CC 91 only exists in the internal one
  assert.equal(panel.padNo(mpk, 38), 1);
  panel.observe([0x99, 41, 100], mpk); // pad note 41 only in the standard
  assert.equal(panel.padNo(mpk, 38), 2);
  panel.observe([0xb0, 74, 20], "Some Keyboard"); // other devices are left alone
  assert.equal(panel.padNo("Some Keyboard", 38), 2); // generic: (38 - 36) % 8
});

test("with the mod key held, pads and knobs act as the second set", () => {
  const storage = new Map();
  const mpk = "MPK mini Play mk3";
  storage.set("pocket.midi.hw.v1", JSON.stringify({ [mpk]: { keys: 25, pads: 8, padCh: 9, padNotes: [[36, 37, 38, 39, 40, 41, 42, 43]], ccs: [70, 71, 72, 73, 74, 75, 76, 77], knobs: 8, cc0: 0, modKey: "c0:64" } }));
  const context = { performance, setTimeout, window: {}, location: { pathname: "/track-pocket/" }, localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v) } };
  vm.createContext(context);
  vm.runInContext(source, context);
  const ran = [];
  const ids = Array.from({ length: 16 }, (_, i) => "k" + i);
  const MI = { names: [mpk], map: {}, defaults: () => ({ knobs: ids.map((id) => [id, id]), pads: ids.map((id) => ["p" + id, id]) }), actions: () => [...ids, ...ids.map((id) => "p" + id)].map((id) => ({ id, group: "x", name: id, kind: "knob" })) };
  const panel = context.window.createMidiPanel(MI, (a) => ran.push(a.id), () => {});
  panel.fallback(mpk, "c0:70", true, false, 64);
  panel.observe([0xb0, 64, 127], mpk); // the mod key (the pedal) goes down
  panel.fallback(mpk, "c0:70", true, false, 64);
  panel.fallback(mpk, "c0:77", true, false, 64);
  assert.equal(panel.padNo(mpk, 39), 11);
  panel.observe([0xb0, 64, 0], mpk); // and up
  panel.fallback(mpk, "c0:70", true, false, 64);
  assert.equal(panel.padNo(mpk, 39), 3);
  assert.deepEqual(ran, ["k0", "k8", "k15", "k0"]);
  const { vetHw } = context.window.pocketMidiHelpers;
  assert.equal(vetHw({ keys: 25, modKey: "c0:64" }).modKey, "c0:64");
  assert.equal(vetHw({ keys: 25, modKey: "rt:250" }).modKey, undefined);
  assert.equal(vetHw({ keys: 25, modKey: "<b>" }).modKey, undefined);
});

test("the sustain pedal is the mod key by default, and one switch turns it off", () => {
  const storage = new Map();
  const mpk = "MPK mini Play mk3", other = "Some Keyboard";
  const context = { performance, setTimeout, window: {}, location: { pathname: "/track-pocket/" }, localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v) } };
  vm.createContext(context);
  vm.runInContext(source, context);
  const MI = { names: [mpk, other], map: {}, actions: () => [] };
  const panel = context.window.createMidiPanel(MI, () => {}, () => {});
  assert.equal(panel.modPedal(), true);
  for (const d of [mpk, other]) {
    assert.equal(panel.layerOf(d), false);
    panel.observe([0xb0, 64, 127], d); // the pedal goes down
    assert.equal(panel.layerOf(d), true);
    panel.observe([0xb0, 64, 0], d);
    assert.equal(panel.layerOf(d), false);
  }
  panel.observe([0xb0, 64, 127], mpk);
  assert.equal(panel.padNo(mpk, 38), 9); // the second set: 8 more
  panel.modPedal(false); // the switch: off, and a held pedal is let go
  assert.equal(panel.layerOf(mpk), false);
  panel.observe([0xb0, 64, 127], mpk);
  assert.equal(panel.layerOf(mpk), false);
  assert.equal(panel.modPedal(), false);
});
