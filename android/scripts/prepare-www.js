#!/usr/bin/env node
// Copies the single-file app (pocket.webSource in package.json) into android/www/, the folder Capacitor packages.
const fs = require("fs");
const { webSource } = require("../package.json").pocket;
fs.mkdirSync("www", { recursive: true });
fs.copyFileSync(webSource, "www/index.html");
console.log(`[prepare-www] ${webSource} -> www/index.html`);
