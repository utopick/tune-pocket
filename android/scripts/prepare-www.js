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
fs.mkdirSync("www/icons", { recursive: true });
for (const name of ["icon-192.png", "icon-512.png"]) fs.copyFileSync(`../icons/${name}`, `www/icons/${name}`);
fs.copyFileSync("../manifest.webmanifest", "www/manifest.webmanifest");
console.log(`[prepare-www] bundled ${webSource} + midi-device.js + PWA icons -> www/`);
