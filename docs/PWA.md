# Installable web app (GitHub Pages)

The site is https://utopick.github.io/tune-pocket/ and is served from `main`, root folder (Settings ▸ Pages ▸ Deploy from a branch ▸ `main` / `(root)`). There is no Pages workflow.

Files that make it a PWA: `manifest.webmanifest`, `sw.js`, `icons/icon-192.png`, `icons/icon-512.png`, and the registration code in `index.html`. The worker caches only the app shell for offline use and tries the network first, so online visits get updates. Microphone, MIDI hardware and third-party resources (SING's lyrics search) are never cached.

## Checking a release

1. After pushing `main`, check that `/tune-pocket/`, `/manifest.webmanifest`, `/sw.js` and `/icons/icon-192.png` return 200 over HTTPS.
2. In Chrome DevTools ▸ Application, look at Manifest, Service Workers and Cache Storage. Visit once online, then reload offline.
3. Install from the Chrome menu or address bar (Android, desktop). On iPhone/iPad use Safari ▸ Share ▸ Add to Home Screen. Allow the microphone and MIDI when the browser asks. Web MIDI does not exist in Safari/iOS.

`localhost` over HTTP counts as a secure context: the dev server in the parent folder serves the working tree at `/tune-pocket/`. If you use a custom domain or change the project path, update the manifest's `id`, `start_url` and `scope`; the service worker takes its scope from its own location.

Before a PWA test branch is merged, `pages-preview.sh` (parent folder) can publish it under a subfolder of Pages. Delete that subfolder when the branch is merged.
