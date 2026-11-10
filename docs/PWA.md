# Installable web app (GitHub Pages)

The site is already available at https://utopick.github.io/tune-pocket/. This branch adds `manifest.webmanifest`, `sw.js`, two PNG icons in `icons/`, and the links/registration in `index.html`. The worker caches only the app shell (including `midi-device.js`) for offline use; it tries the network first so online visits receive updates. Microphone, MIDI hardware, and third-party resources are not cached.

## Publish

1. Push this repository's `midi-device-test` branch if you want a review/PR: `git push -u origin midi-device-test`. **That alone does not update the existing Pages URL.**
2. Once tested, merge the branch to the branch configured in GitHub **Settings → Pages → Build and deployment** (usually `main`, root `/`). Push that branch. If Pages isn't enabled, choose **Deploy from a branch**, select `main` and `/(root)`, and save. There is no Pages Actions workflow in this repository.
3. Check that `/tune-pocket/`, `/tune-pocket/manifest.webmanifest`, `/tune-pocket/sw.js`, `/tune-pocket/midi-device.js`, and `/tune-pocket/icons/icon-192.png` return 200 over HTTPS. In Chrome DevTools → Application, check Manifest, Service Workers, and Cache Storage. Visit once online, then test an offline reload.
4. Install from Chrome's menu/address-bar install action on Android/desktop. On iPhone/iPad use Safari → Share → Add to Home Screen. Installation and offline caching do not grant hardware permissions; allow the microphone/MIDI in the browser when prompted. Web MIDI support depends on the browser/platform (Safari/iOS does not support this project's Web MIDI flow).

`localhost` over HTTP is a secure context for testing: the parent-folder dev server serves the branch working tree at `/tune-pocket/`. A `@main` preview is not the feature branch. If you use a custom domain or change the project path, update the manifest's `id`, `start_url`, and `scope`; the service worker derives its scope from its own location.

The Android APK workflow remains available. Its `npm run www` step bundles the MIDI helper and copies the icons/manifest, without registering the web service worker inside the native WebView. The GitHub Release HTML is standalone but a `file://` page is not installable as a PWA.
