// Run with: node --test tests/midi-device.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync(require.resolve("../midi-device.js"), "utf8");

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
