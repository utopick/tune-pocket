#!/usr/bin/env node
// Bundles the app and its local MIDI device helper into a standalone page for Capacitor.
const fs = require("fs");
const { webSource } = require("../package.json").pocket;
fs.mkdirSync("www", { recursive: true });
const html = fs.readFileSync(webSource, "utf8");
const helper = fs.readFileSync("../midi-device.js", "utf8");
const tag = '<script src="midi-device.js"></script>';
if (!html.includes(tag)) throw new Error("Missing MIDI device script tag");
fs.writeFileSync("www/index.html", html.replace(tag, `<script>${helper}</script>`));
console.log(`[prepare-www] bundled ${webSource} + midi-device.js -> www/index.html`);
