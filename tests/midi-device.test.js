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
    window: {}, location: { pathname: "/tune-pocket/" },
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
  const other = { ...context, window: {}, location: { pathname: "/sing-pocket/" } };
  vm.createContext(other);
  vm.runInContext(source, other);
  assert.equal(other.window.createMidiPanel(MI, () => {}, () => {}).route("MPK mini Play mk3", "n9:36", false, true, 100), false);
});

test("real-time clock and unmapped messages pass through", () => {
  const context = { window: {}, location: { pathname: "/track-pocket/" }, localStorage: { getItem: () => null } };
  vm.createContext(context);
  vm.runInContext(source, context);
  const panel = context.window.createMidiPanel({ names: [], actions: () => [] }, () => { throw Error("unexpected action"); }, () => {});
  panel.observe([0xf8], "Launchkey MIDI");
  panel.observe([0x90, 60, 100], "Launchkey MIDI");
  assert.equal(panel.route("Launchkey MIDI", "n0:60", false, true, 100), false);
});

test("pads and knobs are matched without learning", () => {
  const context = { window: {}, location: { pathname: "/track-pocket/" }, localStorage: { getItem: () => null } };
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
  assert.equal(guess("MPK mini Play mk3"), "akai");
  assert.equal(guess("nanoPAD2"), "korgpad");
});

test("the starting assignment: pads and knobs do what the app says until the user changes it", () => {
  const storage = new Map();
  const context = { window: {}, location: { pathname: "/track-pocket/" }, localStorage: { getItem: (k) => storage.get(k), setItem: (k, v) => storage.set(k, v) } };
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
  panel.observe([0xb0, 2, 64], dev); // the first CC the MPK knob sends: knob 1
  assert.equal(panel.fallback(dev, "c0:2", true, false, 64), true);
  assert.equal(panel.fallback(dev, "c0:3", true, false, 64), true);
  assert.equal(panel.fallback(dev, "c0:4", true, false, 64), false); // knob 3 has no default
  assert.equal(panel.fallback(dev, "n9:36", false, true, 100), true); // pad 1 (channel 10)
  assert.equal(panel.fallback(dev, "n9:37", false, true, 100), false); // a label only: it plays as a note
  assert.equal(panel.fallback(dev, "n0:36", false, true, 100), false); // a key, not a pad
  assert.deepEqual(calls, ["vol0", "bpm", "live0"]);
  // the user's own assignment wins, and the action is not also on its default control
  MI.map["c0:9"] = "bpm";
  assert.equal(panel.fallback(dev, "c0:3", true, false, 64), false);
  // CLEAR turns every default off
  panel.defaultsOff();
  assert.equal(panel.fallback(dev, "c0:2", true, false, 64), false);
  assert.equal(panel.fallback(dev, "n9:36", false, true, 100), false);
  // a model with unknown knob numbers gets no knob defaults
  const gen = context.window.createMidiPanel({ ...MI, names: ["Some keyboard"] }, (a) => calls.push(a.id), () => {});
  gen.observe([0xb0, 70, 1], "Some keyboard");
  assert.equal(gen.fallback("Some keyboard", "c0:70", true, false, 1), false);
  assert.equal(gen.fallback("Some keyboard", "n9:36", false, true, 100), true); // but its pads (8 on the generic layout) do
});

test("Korg nanoPAD2 pads (channel 1, 16 pads) and the nanoKEY2 are recognised", () => {
  const context = { window: {}, location: { pathname: "/sing-pocket/" }, localStorage: { getItem: () => null } };
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
