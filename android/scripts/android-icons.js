#!/usr/bin/env node
// Puts the app's own icon and launch screen into the generated Android project, in place of Capacitor's.
// Run from android/ after `npx cap add android`. The PNGs come from icons/res/ (drawn from icons/icon.svg):
//   ic_launcher / ic_launcher_round   48 dp, for launchers before Android 8
//   ic_launcher_foreground            108 dp, transparent: Android 8+ masks it (circle, squircle...) over the background colour
// The launch screen becomes the icon on the app's dark background (Capacitor's has its own logo).
const fs = require("fs");
const path = require("path");
const BG = "#0d0f12";
const res = "native/app/src/main/res"; // android.path in capacitor.config.json

// 1. the icons
const src = "icons/res";
let n = 0;
for (const dir of fs.readdirSync(src)) {
  fs.mkdirSync(path.join(res, dir), { recursive: true });
  for (const f of fs.readdirSync(path.join(src, dir))) {
    fs.copyFileSync(path.join(src, dir, f), path.join(res, dir, f));
    n++;
  }
}
// the adaptive icon's background colour
fs.writeFileSync(
  path.join(res, "values/ic_launcher_background.xml"),
  `<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">${BG}</color>\n</resources>\n`,
);
// Capacitor's vector foreground (drawable-v24) would win over ours on Android 7+: remove it
const vec = path.join(res, "drawable-v24/ic_launcher_foreground.xml");
if (fs.existsSync(vec)) fs.unlinkSync(vec);
for (const f of ["mipmap-anydpi-v26/ic_launcher.xml", "mipmap-anydpi-v26/ic_launcher_round.xml"]) {
  const p = path.join(res, f);
  if (fs.existsSync(p)) fs.writeFileSync(p, fs.readFileSync(p, "utf8").replace(/@(drawable|mipmap)\/ic_launcher_foreground/, "@mipmap/ic_launcher_foreground"));
}

// 2. the launch screen: the dark background with the icon in the middle, on every screen size
for (const dir of fs.readdirSync(res)) {
  const p = path.join(res, dir, "splash.png");
  if (dir.startsWith("drawable") && fs.existsSync(p)) fs.unlinkSync(p);
}
fs.mkdirSync(path.join(res, "drawable"), { recursive: true });
fs.writeFileSync(
  path.join(res, "drawable/splash.xml"),
  `<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:drawable="@color/ic_launcher_background" />
    <item><bitmap android:gravity="center" android:src="@mipmap/ic_launcher_foreground" /></item>
</layer-list>
`,
);
// Android 12+ draws its own launch screen from the theme: dark, with the icon
const styles = path.join(res, "values/styles.xml");
let xml = fs.readFileSync(styles, "utf8");
if (!xml.includes("windowSplashScreenBackground"))
  xml = xml.replace(
    /(<style name="AppTheme.NoActionBarLaunch"[^>]*>)/,
    `$1\n        <item name="windowSplashScreenBackground">@color/ic_launcher_background</item>\n        <item name="windowSplashScreenAnimatedIcon">@mipmap/ic_launcher_foreground</item>`,
  );
if (!xml.includes("windowSplashScreenBackground")) throw new Error("could not set the launch screen colour in styles.xml");
fs.writeFileSync(styles, xml);
console.log(`[android-icons] ${n} icon files, launch screen ${BG}`);
