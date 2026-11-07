#!/usr/bin/env node
// Copies the single-file app into www/, the folder Capacitor packages into the APK.
const fs = require("fs");
const { webSource } = require("../package.json").pocket;
fs.mkdirSync("www", { recursive: true });
fs.copyFileSync(webSource, "www/index.html");
console.log(`[prepare-www] ${webSource} -> www/index.html`);
