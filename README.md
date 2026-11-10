![TUNE.Pocket](.github/banner.png)

![TUNE.Pocket on five screens, each in a different theme](.github/readme/hero.png)


# TUNE.Pocket

Tune was the first app I actually coded with the help of AI for personal reasons. I found myself going through hurdles to find a good off-line guitalele tuner, and always ended up having to use an ad-ridden guitar tuner app and a lot of traditional fifth chord manual tuning. 

So I tried to make a Cordova baked monolithic HTML tuner... and I've been using it for a year. Self-hosted, because Cordova didn't work properly (mic issues).

Fast-forward to this weekend, I finished up retouching Track.Pocket (from the old Tune code and some of my Family Forge tracker code) and as an afterthought ended up in an hyperfocused refactor.

Thus came TUNE.Pocket, a pocket tuner, note detector, scale finder and jam band for guitar, bass, violin, guitalele and ukulele, the sister app of [TRACK.Pocket](https://github.com/utopick/track-pocket) and [SING.Pocket](https://github.com/utopick/sing-pocket). It runs from one self-contained HTML file, with no install, no dependencies and no network requests.

It should run fully offline, although opening the HTML file directly can cause microphone permission issues, so use the hosted GitHub page instead or self-host the HTML.

**Open it:** [utopick.github.io/tune-pocket](https://utopick.github.io/tune-pocket/) · **Install it:** it is a web app (PWA): on Android, Chrome ▸ **Install app**; on iPhone, Safari ▸ Share ▸ **Add to Home Screen**; on a computer, the install icon in the address bar. Once installed it opens like an app and works offline.

I've been adding features and tweaking a lot, so they come out not fully tested, and there could be bugs. Leave me an issue and I'll fix it.

There is a help wiki inside (también en español), with small interactive demos you can touch and hear: the tuner, the metronome, the looper's quantize and the circle of fifths.

I want to apologize to my neighbours for my live session afternoons and state here that I actually made a cow move gracefully out of the way with a tin whistle song. I have witnesses.



<p align="center"><img src=".github/readme/demo.gif" width="320" alt="TUNE.Pocket in use: a string coming into tune, five loops playing, the metronome and the circle of fifths"></p>

## Why did I release these apps? 

Because GitHub allows me to host them in a GitHub site if I make them public, and I don't want to host them myself. 

Also because my friends told me that they are useful and some of you may want a free, ad-less gadget to pass the time.

## Ads and cookies

Yeah, no.

No ads, no cookies, no nothing. This is free and clean. No hidden stealers, no weird intentions.

Why is it free? Because not everything should be a product.

![A strip of TUNE.Pocket screens](.github/readme/strip.png)


## AI use

I'm a programmer and I have been coding for a living for over two decades, but life has given me too little free time that I want to spend offline and outside, making music and art. So I used a lot of AI to build this in a quick and easy way.

I'm not going to take credit for the code, even though I started this app from my own older code. I built it with the help of an AI coding assistant (Claude, by Anthropic), which wrote and reworked much of the code following my designs and notes.

The app itself uses no AI: everything runs on your device, and nothing you play, sing or record is sent to any AI service or anywhere else for that matter. If that isn't the case just shame me publicly and I'll fix it.

I did waste a lot of tokens by making it code it in a non-minified way, so if the bubble bursts and we go back to the basics it could be maintainable. 

If you want to try something made by me by hand (95%, I did use an early model to find some bugs but solved them by hand) in which I made the code, assets, music and all, check out Nanaya, my Pico-8 tower defense game: https://www.lexaloffle.com/bbs/?tid=153336

![alt text](.github/readme/nanaya.png)


## How to run it

Open `index.html` in a modern web browser and tap **●** to listen. Your browser may ask for permission to play audio, so interact with the page first if you hear nothing.

The microphone needs `https://` or `localhost`, which is why the hosted page (or the installed app) is the easy way.

## The basics

- **Tuner:** pick the instrument and tuning, tap **●** and play a string. The nearest string pad lights up, and the meter and trace show how far off you are. Tap a pad to lock onto that string; **AUTO** follows the nearest one again. **TONE** plays the reference.
- **Detect:** shows any note you play or sing, with its frequency and cents, and draws it over time.
- **Scales:** 15 scales in any key, with a fretboard that follows the tuner's instrument and tuning. Play the scale, an arpeggio, or a root drone to practise over.
- **Jam:** a drum, bass and chord band in 8 styles, in any key, major or minor, with tap tempo and a mixer.
- **Circle of fifths:** every key with its relative minor and signature; the key's chords light up and play, with a I–V–vi–IV progression, triads or sevenths, and links to Scales and Jam.
- **Metronome:** a wireframe metronome you set by dragging its weight, with a swinging pendulum and numbered beats below. Pick 1–12 beats a bar, eighths, triplets or sixteenths, and four click sounds, or tap the tempo. It keeps ticking in the other views, so you can practise scales in time.
- **Looper:** 16 pads. Tap an empty one and it counts in a bar, then records a loop of 1, 2, 4 or 8 bars from the microphone. Tap a loop to start or stop it; all loops stay locked to the same bars. There are FX pads (the band's effects plus repeat, reverse and octave), overdub, reverse, normalize, crop to whole beats, quantize to a grid (by hand, or automatically as each loop lands with AUTO Q, off by default), nudge, clear and undo. Loops last until you close the app. Use headphones.
- **Setup:** custom tunings (notes like `E2`, `F#3`, `Bb1`, or frequencies in Hz), theme, options and help.

The A4 reference (415–466 Hz) is at the end of the instrument bar.

![The views: tuner, scales, jam, circle of fifths, metronome and looper](.github/readme/views.png)

### Themes

Six looks, from **THEME** in Setup: Dark, Light, Terminal, Dungeon synth, DMG and Demoscene. All three Pocket apps share them.

They were surprinsingly designed by Claude from some sketches, so go figure. 

![The circle of fifths in the six themes](.github/readme/themes.png)

### Your settings

Settings and custom tunings are stored in your browser (`localStorage`); they are not uploaded anywhere. Tunings saved by the old LFTuner load automatically. Clearing browser storage removes them.

## Install it (PWA)

TUNE.Pocket is a progressive web app: the hosted page can be installed and then runs on its own, offline. It is `index.html` plus a tiny service worker (`sw.js`, which keeps the app files for offline use), a manifest and two icons. Nothing else is downloaded, and nothing is uploaded.

- **Android:** open the page in Chrome and choose **Install app** (or **Add to Home Screen**). The first time you use the microphone, allow it when the browser asks.
- **iPhone / iPad:** in Safari, Share ▸ **Add to Home Screen**.
- **Computer:** Chrome or Edge show an install icon in the address bar.
- **Updates:** the app looks for a new version whenever it is online; close and reopen it to get it.
- **MIDI keyboards and pads:** Chrome, Edge and Chrome on Android can use them (Web MIDI). Safari and iPhone cannot. The **MIDI** panel in the options lists what the browser sees, has an assign wizard and a TEST that shows what each key sends.
- Your data lives in the browser's storage for that site (separate from other sites and from any older Android APK). Export what you want to keep before clearing browser data.

**The Android APK is retired.** It was a Capacitor wrapper of this same page; the web app now does the same job without a build or an install from outside the store. Its code is kept in the [`android-legacy`](https://github.com/utopick/tune-pocket/tree/android-legacy) branch and the old APKs stay in [Releases](https://github.com/utopick/tune-pocket/releases); neither is updated any more.

## Files

- `index.html` — the complete app (markup, styles, and audio code)
- `midi-device.js` — the MIDI panel (device drawings, assign wizard)
- `manifest.webmanifest`, `sw.js`, `icons/` — what makes it installable and offline
- `docs/` — notes for whoever maintains it; `tests/` — a small test for the MIDI helpers
- `LICENSE` — license terms

## License

TUNE.Pocket is released under the MIT License (see `LICENSE`).

AI assisted coding uses the uncredited work of a lot of coders through the years (me included) so anything I make that's not for work its as free as possible.

Have fun.

### Third-party code

The banner, app icons and favicons are lettered in [Inter](https://rsms.me/inter/) (SIL Open Font License 1.1), converted to shapes, so no font file is included. The app itself has no third-party code.

## The readmes

Yeah. They are all similar. I copied and pasted. No one ever reads them all. Kilroy was here.


Anyway, listen to me: You matter. A lot. I don't know you stranger, but you have my admiration and love. Keep making art.