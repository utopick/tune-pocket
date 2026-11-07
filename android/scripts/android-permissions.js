#!/usr/bin/env node
// Adds the permissions the WebView needs for the microphone to the generated Android manifest.
// Run from android/ after `npx cap add android`. Capacitor's WebView then asks for them at runtime the first time the
// page calls getUserMedia (see BridgeWebChromeClient.onPermissionRequest): both must be declared, or
// Android denies the request without showing a prompt.
const fs = require("fs");
const file = "native/app/src/main/AndroidManifest.xml"; // android.path in capacitor.config.json
const PERMS = ["android.permission.RECORD_AUDIO", "android.permission.MODIFY_AUDIO_SETTINGS"];
let xml = fs.readFileSync(file, "utf8");
const add = PERMS.filter((p) => !xml.includes(`"${p}"`))
  .map((p) => `    <uses-permission android:name="${p}" />\n`)
  .join("");
if (add) xml = xml.replace(/(\s*)<\/manifest>\s*$/, `\n${add}</manifest>\n`);
fs.writeFileSync(file, xml);
for (const p of PERMS) if (!xml.includes(`"${p}"`)) throw new Error("could not add " + p);
console.log("[android-permissions] manifest has", PERMS.join(", "));
