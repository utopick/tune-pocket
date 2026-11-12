"""End-to-end checks for a Pocket app, driven through a real Chrome with Selenium.

The same file lives in track-pocket, tune-pocket and sing-pocket; it works out which app it is in from the folder name.
Setup (once):   python3 -m venv .venv && .venv/bin/pip install selenium
Run:            .venv/bin/python tests/e2e.py            (add -v for the names; HEAD=1 to watch the browser)
Needs Chrome installed; Selenium downloads the matching driver by itself.
"""
import functools, http.server, json, os, sys, threading, unittest, urllib.request
from selenium import webdriver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.basename(ROOT).split("-")[0]  # track | tune | sing
# a name that would run script if any place put it into the page unescaped
EVIL = "<img src=x onerror=\"__pwned.push('%s')\">"

# runs before every page script: counts errors and watches for script that ran from data
HOOK = """
window.__errs = []; window.__pwned = [];
addEventListener('error', e => __errs.push(String(e.message)));
addEventListener('unhandledrejection', e => __errs.push('promise: ' + (e.reason && e.reason.message || e.reason)));
const ce = console.error; console.error = (...a) => { __errs.push('console: ' + a.join(' ')); ce.apply(console, a); };
localStorage.getItem('%s.welcome') || localStorage.setItem('%s.welcome', '1');
""" % (APP, APP)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def log_message(self, *a): pass


def setUpModule():
    global SRV, BASE
    SRV = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=SRV.serve_forever, daemon=True).start()
    BASE = "http://127.0.0.1:%d/" % SRV.server_address[1]


def tearDownModule(): SRV.shutdown()


class Page(unittest.TestCase):
    """A fresh Chrome (empty storage) for each test."""
    def setUp(self):
        o = webdriver.ChromeOptions()
        if not os.environ.get("HEAD"): o.add_argument("--headless=new")
        o.add_argument("--window-size=390,844"); o.add_argument("--autoplay-policy=no-user-gesture-required")
        self.d = webdriver.Chrome(options=o)
        self.d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": HOOK})
        self.addCleanup(self.d.quit)

    def open(self, wait=0.8):
        self.d.get(BASE + "index.html"); self.d.implicitly_wait(0); __import__("time").sleep(wait)

    def js(self, code, *a): return self.d.execute_script(code, *a)

    def wait(self, s): __import__("time").sleep(s)

    def reopen(self, wait=1.2): self.d.refresh(); self.wait(wait)

    def errors(self): return self.js("return window.__errs || []")

    def assertClean(self):
        self.assertEqual(self.js("return window.__pwned"), [], "script ran from data")
        self.assertEqual(self.errors(), [])

    def tour(self):
        """Open every view and every help page, in both themes."""
        for v in self.js("return [...document.querySelectorAll('#hViews [data-v]')].map(e => e.dataset.v)"):
            self.js("document.querySelector('#hViews [data-v=\"%s\"]').click()" % v); self.wait(0.15)
        for th in ("dark", "light"):
            self.js("setTheme(arguments[0])", th)
            for s in self.js("return HELP.map(h => h.id)"):
                self.js("openHelp(arguments[0])", s); self.wait(0.05)
            self.js("closeHelp()")


class Common(Page):
    def test_boots_and_every_view_opens(self):
        self.open(); self.tour(); self.assertClean()

    def test_installable_files_are_served(self):
        for f in ("manifest.webmanifest", "sw.js", "icons/icon-192.png", "icons/icon-512.png"):
            with urllib.request.urlopen(BASE + f) as r: self.assertEqual(r.status, 200, f)
        m = json.load(urllib.request.urlopen(BASE + "manifest.webmanifest"))
        for k in ("name", "start_url", "icons"): self.assertIn(k, m)

    def test_no_external_requests(self):
        # a Pocket app only talks to itself (SING's lyrics search is the one allowed host, and only when asked)
        self.open()
        urls = self.js("return performance.getEntriesByType('resource').map(e => e.name)")
        self.assertEqual([u for u in urls if not u.startswith(BASE)], [])


@unittest.skipUnless(APP == "track", "TRACK only")
class Track(Page):
    def song(self, mutate):
        return self.js("const e = JSON.parse(serialize()); (%s)(e); return e" % mutate)

    def test_song_file_cannot_run_script(self):
        self.open()
        self.js("""const e = JSON.parse(serialize());
          e.song.name = arguments[0]; e.song.patterns[0].name = arguments[1]; e.song.mix[0].preset = arguments[2];
          loadData(e); showTab('mix'); showTab('trk'); varEnter(); document.querySelector('#vExp').click();""",
                EVIL % "song name", EVIL % "pattern name", EVIL % "preset")
        self.wait(0.6); self.assertClean()

    def test_malformed_songs_are_rejected_or_repaired_and_never_stick(self):
        cases = {"no patterns": "e.song.patterns = []", "order past the end": "e.song.order = [99]", "empty order": "e.song.order = []",
                 "huge length": "e.song.patterns[0].len = 1e9", "short rows": "e.song.patterns[0].ch = [[]]",
                 "bpm text": "e.song.bpm = 'abc'", "chN 99": "e.song.chN = 99"}
        self.open()
        for name, m in cases.items():
            with self.subTest(name):
                self.js("const e = JSON.parse(serialize()); %s; try { loadData(e) } catch (x) {} saveNow()" % m)
                self.reopen()
                self.assertTrue(self.js("return song.patterns.length > 0 && !!document.querySelector('#grid, #pk')"), "does not boot")

    def test_qr_readers_read_what_the_app_draws(self):
        """Both readers behind SCAN (ours and jsQR) read the app's own codes from a turned, tilted picture, and nothing from noise."""
        self.open()
        if not self.js("return typeof qrRead === 'function'"): self.skipTest("no QR reader in this build")
        bad = self.js("""const bad = [], shot = (Q, deg, tilt) => {
            const W = 960, H = 720, N = Q.length, size = 500 / (N + 8), c = Math.cos(deg * Math.PI / 180), s = Math.sin(deg * Math.PI / 180), data = new Uint8ClampedArray(W * H * 4);
            for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
              let X = x - W / 2, Y = y - H / 2; const w = 1 + tilt * (X + 0.6 * Y); X /= w; Y /= w;
              const u = (c * X + s * Y) / size + N / 2, v = (-s * X + c * Y) / size + N / 2, k = (y * W + x) * 4;
              const page = u >= -4 && v >= -4 && u < N + 4 && v < N + 4, on = u >= 0 && v >= 0 && u < N && v < N && Q[Math.floor(v)][Math.floor(u)];
              data[k] = data[k + 1] = data[k + 2] = (page ? (on ? 40 : 215) : 90 + 60 * Math.sin(x / 37) * Math.cos(y / 23)) * (0.75 + 0.25 * x / W); data[k + 3] = 255;
            }
            return { data, width: W, height: H };
          };
          for (const t of ['https://x.test/', 'https://x.test/#a=' + 'Ab3-_9'.repeat(28), 'ñ€' + 'Z9'.repeat(200)]) for (const [deg, tilt] of [[0, 0], [-23, 0.0001], [187, 0.0001]]) {
            const p = shot(qrMake(t), deg, tilt);
            if (qrRead(p) !== t) bad.push('own ' + t.length + ' ' + deg);
            if ((jsQR(p.data, p.width, p.height) || {}).data !== t) bad.push('jsQR ' + t.length + ' ' + deg);
          }
          const noise = { data: Uint8ClampedArray.from({ length: 320 * 240 * 4 }, (_, i) => (i * 2654435761 >>> 24)), width: 320, height: 240 };
          if (qrRead(noise) !== null) bad.push('own read noise');
          return bad""")
        self.assertEqual(bad, [])

    def test_camera_reads_a_code_in_the_pairing_dialog(self):
        self.open()
        if not self.js("return !!document.querySelector('#syScanA')"): self.skipTest("no SCAN in this build")
        self.assertTrue(self.js("syFace(); return document.querySelector('#syHQ').hidden"))
        self.js("syCamScan(false)"); self.wait(0.2)  # no pairing running: the camera stays closed
        self.assertTrue(self.js("return !SYM.cam && document.querySelector('#syCam').hidden"))
        # a pretend camera that shows a code: each reader sees it in the camera loop, and STOP closes the camera
        self.js("""const c = document.createElement('canvas'), g = c.getContext('2d'), Q = qrMake('https://x.test/#j=abc'), k = 500 / (Q.length + 8);
          c.width = c.height = 1000; g.fillStyle = '#fff'; g.fillRect(0, 0, 1000, 1000); g.fillStyle = '#000';  // the code in the middle: only that part is read
          Q.forEach((row, r) => row.forEach((on, x) => on && g.fillRect(250 + (x + 4) * k, 250 + (r + 4) * k, k + 0.5, k + 0.5)));
          setInterval(() => g.clearRect(0, 0, 1, 1), 50);
          navigator.mediaDevices.getUserMedia = async () => c.captureStream(15);""")
        for lib, name in ((False, "Own reader"), (True, "jsQR")):
            with self.subTest(name):
                self.js("syDlg({ scan: 'a', txt: 'x' }); syCamScan(arguments[0])", lib); self.wait(1.5)
                self.assertFalse(self.js("return document.querySelector('#syCam').hidden"))
                self.assertTrue(self.js("const b = document.querySelector('#syHQBody'), r = document.querySelector('#syCam').getBoundingClientRect(); return r.width > 199 && Math.abs(r.width - r.height) < 2 && b.scrollHeight <= b.clientHeight"), "the camera view needs scrolling")
                self.assertTrue(self.js("return syLog.some(l => l.includes(arguments[0] + ' read a code'))", name), "the camera loop read nothing")
                self.js("syStop(true)")
                self.assertTrue(self.js("return !SYM.cam && document.querySelector('#syHQ').hidden"))
        self.assertEqual(self.errors(), [])

    def until(self, code, what, secs=12):
        end = __import__("time").time() + secs
        while __import__("time").time() < end:
            v = self.js(code)
            if v: return v
            self.wait(0.15)
        self.fail("never happened: " + what + " | log: " + str(self.js("return syLog.slice(-6)")))

    def test_three_devices_sync(self):
        """Three tabs pair through the dialog (the codes are handed over in place of the camera): more than one guest, the list, knobs, the Variator."""
        self.open()
        if not self.js("return typeof syDlg === 'function'"): self.skipTest("no QR sync in this build")
        tabs = [self.d.current_window_handle]
        for _ in range(2):
            self.d.switch_to.new_window("tab"); self.open(); tabs.append(self.d.current_window_handle)
        on = lambda i: self.d.switch_to.window(tabs[i])
        for g in (1, 2):
            on(0); self.js("syHost()")
            inv = self.until("return SYNC.ui && SYNC.ui.qr", "the host's code")
            self.assertFalse(self.js("return document.querySelector('#syHQ').hidden || document.querySelector('#syScanBar').hidden"))
            on(g); self.js("syJoinRead(arguments[0].split('#j=')[1])", inv)
            ans = self.until("return SYNC.ui && SYNC.ui.qr", "the guest's answer code")
            on(0); self.assertTrue(self.js("return syAnswerIn(arguments[0].split('#a=')[1])", ans))
            num = self.until("return SYNC.ui && SYNC.ui.chk && SYNC.ui.num", "the check on the host")
            self.assertFalse(self.js("return document.querySelector('#syChkBar').hidden"))
            on(g); self.assertEqual(self.until("return SYNC.ui && SYNC.ui.num", "the check on the guest"), num)
            self.assertFalse(self.js("return document.querySelector('#syHQ').hidden"), "the guest waits in the dialog")
            on(0); self.js("document.querySelector('#syYes').click()")
            self.until("return syN() === %d && document.querySelector('#syHQ').hidden" % g, "guest %d confirmed, the earlier ones still in" % g)
            on(g); self.until("return syN() === 1 && document.querySelector('#syHQ').hidden", "the guest is in and its dialog closed")
        on(0); self.assertEqual(self.js("return document.querySelectorAll('#syList div').length"), 4)  # the title and three devices
        on(1); self.until("return SYNC.who && SYNC.who.l.length === 3 && document.querySelectorAll('#syList div').length === 4", "the guest's list of devices")
        # knobs: the value and its drawing follow on the other devices
        self.js("showTab('mix')"); before = self.js("return [document.querySelector('#mstK').innerHTML, document.querySelector('#mixRows .kn[data-k=vol]').innerHTML]")
        on(0); self.js("document.querySelector('#master').value = 0.33; mixSet(S.col, 'vol', 0.21)")
        on(1); self.until("return +document.querySelector('#master').value === 0.33 && song.mix[S.col].vol === 0.21", "the knob values on a guest")
        after = self.js("return [document.querySelector('#mstK').innerHTML, document.querySelector('#mixRows .kn[data-k=vol]').innerHTML]")
        self.assertNotEqual(before[0], after[0], "the master knob was not drawn again"); self.assertNotEqual(before[1], after[1], "the channel knob was not drawn again")
        # one device makes the sound: the host at first, then the one that takes it
        on(0); self.assertFalse(self.js("return SYNC.silent")); on(2); self.assertTrue(self.js("return SYNC.silent"))
        on(1); self.assertTrue(self.js("return SYNC.silent")); self.js("document.querySelector('#sySound').click()")
        on(0); self.until("return SYNC.silent && /sound/.test(document.querySelectorAll('#syList div')[2].textContent)", "the host went silent and lists who sounds")
        on(2); self.until("return SYNC.silent && SYNC.who.snd === 1", "the other guest stays silent and knows who sounds")
        self.js("document.querySelector('#sySoundAll').click()")  # SOUND EVERYWHERE from a guest: all of them sound
        for i in (0, 1, 2):
            on(i); self.until("return !SYNC.silent && document.querySelector('#sySoundAll').classList.contains('on')", "sound everywhere on device %d" % i)
        on(1); self.js("document.querySelector('#sySound').click()")  # and back to one
        on(0); self.until("return SYNC.silent", "the host silent again"); on(2); self.until("return SYNC.silent", "the other guest silent again")
        on(1); self.until("return !SYNC.silent && document.querySelector('#sySound').classList.contains('on')", "the sound on the guest that took it")
        # the Variator opened on a guest: every device is in it, with the same seed and patterns, and no piano gets locked to its key
        on(0); name0, scale0 = self.js("return [song.name, S.scaleT]")
        on(1); self.js("VAR.seed = 777; showTab('var')"); sig = "return varAway && VAR.seed === %d && JSON.stringify([song.order, song.patterns.map(p => p.len), song.bpm, song.chInst])"
        same = lambda seed, want, what: self.until("return (() => { %s })() === arguments[0]".replace("arguments[0]", __import__("json").dumps(want)) % (sig % seed), what)
        want = self.js(sig % 777)
        for i in (0, 2):
            on(i); same(777, want, "the Variator on device %d" % i)
            self.assertEqual(self.js("return S.scaleT"), scale0, "the Variator's key locked the piano")
        on(0); self.js("showTab('var')"); self.assertEqual(self.js("return +document.querySelector('#vSeed').value"), 777)
        self.js("VAR.seed = 778; varRegen()"); want = self.js(sig % 778)
        on(1); same(778, want, "the new seed on the guest that opened it")
        self.assertEqual(self.js("return +document.querySelector('#vSeed').value"), 778, "the Variator screen was not drawn again")
        # another screen: the song keeps playing on all
        self.js("togglePlay()")
        self.until("return S.playing", "play on the guest"); on(0); self.until("return S.playing", "play on the host")
        on(1); self.js("showTab('smp')"); self.wait(0.8)
        self.assertTrue(self.js("return S.playing && !!varAway"), "leaving the Variator screen stopped the song")
        on(0); self.assertTrue(self.js("return S.playing")); self.js("togglePlay()"); self.until("return !S.playing", "stop")
        # BACK TO OUR SONG on one device ends the Variator on all
        self.js("varLeave(); showTab('trk')")
        for i in (1, 2):
            on(i); self.until("return !varAway && song.name === arguments[0]" .replace("arguments[0]", __import__("json").dumps(name0)), "the song came back on device %d" % i)
        # a guest opens the Variator again and leaves the sync on another screen: its own song comes back there, and the others stay
        on(1); self.js("showTab('var'); showTab('file'); syLeave()"); self.assertTrue(self.js("return !varAway && !syN()"))
        on(0); self.until("return syN() === 1 && document.querySelectorAll('#syList div').length === 3 && !SYNC.silent", "the host's list after the guest with the sound left, and the sound back on the host")
        for i in range(3):
            on(i); self.assertEqual(self.errors(), [])


@unittest.skipUnless(APP == "tune", "TUNE only")
class Tune(Page):
    def test_tempo_is_locked_while_recording(self):
        self.open()
        self.assertEqual(self.js("const a = S.met.bpm; LP.rec = {i: 0}; setBpm(a + 40); const held = S.met.bpm === a; LP.rec = null; setBpm(a + 40); return [held, S.met.bpm === a + 40]"), [True, True])

    def test_custom_tuning_name_is_escaped(self):
        self.open()
        self.js("localStorage.setItem('customTunings', JSON.stringify([{name: arguments[0], instrument: 'guitar', strings: ['E2','A2']}]))", EVIL % "tuning")
        self.reopen(); self.tour(); self.js("renderSaved && renderSaved()"); self.assertClean()

    def test_custom_tunings_move_to_the_prefixed_key(self):
        self.open()
        self.js("localStorage.setItem('customTunings', JSON.stringify([{name: 'Mine', instrument: 'guitar', strings: ['E2', 'A2']}]))")
        self.reopen()
        self.assertEqual(self.js("return [localStorage.getItem('customTunings'), JSON.parse(localStorage.getItem('tune.customTunings'))[0].name]"), [None, "Mine"])

    def test_loops_survive_a_reload_and_a_session_comes_back(self):
        self.open()
        self.js("""showView('loop'); ctx = new AudioContext(); lpGraph(ctx);
          const buf = ctx.createBuffer(1, 44100, ctx.sampleRate); buf.getChannelData(0).fill(0.25);
          LP.loops[2] = lpMake({buf, bars: 2, a: 0, vol: 0.6}); S.met.bpm = 91;""")
        self.wait(3.8)  # the autosave runs every 3 seconds
        self.reopen(); self.js("showView('loop')"); self.wait(1.5)
        self.assertEqual(self.js("return [!!LP.loops[2], LP.loops[2] && LP.loops[2].bars, S.met.bpm]"), [True, 2, 91])
        # a named session: saved, the pads emptied, opened again
        self.js("document.querySelector('#sName').value = 'Take 1'; sessSave()"); self.wait(0.8)
        self.js("LP.loops.forEach((L, i) => L && lpPut(i, null))")
        self.js("sessOpen('Take 1')"); self.wait(1.2)
        self.assertEqual(self.js("return LP.loops.filter(Boolean).length"), 1)

    def test_damaged_loop_files_are_refused(self):
        self.open()
        for bad in [None, {}, {"loops": "x"}, {"loops": [{"pcm": "AAAA", "rate": 5}]}, {"loops": [{"pcm": "", "rate": 44100}]},
                    {"loops": [{"pcm": "AAAA", "rate": 44100}] * 17}]:
            with self.subTest(bad):
                self.assertTrue(self.js("try { lpVet(arguments[0]); return false } catch (e) { return true }", bad))
        # a good one passes, and out-of-range numbers are brought into range
        got = self.js("const o = lpVet({bpm: 9999, beats: 99, loops: [{pcm: 'AAAA', rate: 44100, bars: 500, a: 1e9, o: -1e9, vol: 99}]}); return [o.bpm === BMAX, o.beats, o.loops[0].bars, o.loops[0].a, o.loops[0].o, o.loops[0].vol]")
        self.assertEqual(got, [True, 16, 64, 4096, -64, 2])

    def test_circle_of_fifths_chords_fit_every_instrument(self):
        self.open()
        got = self.js("""const out = {};
          for (const i of [...document.querySelectorAll('#inst option')].map(o => o.value)) {
            S.inst = i; const ms = stringMidis(), lo = Math.min(...ms), hi = Math.max(...ms) + (KIND(i) === 'wind' ? 19 - (Math.max(...ms) - lo) : 12); let bad = 0, n = 0;
            for (const minor of [false, true]) for (let k = 0; k < 12; k++) for (const sev of [false, true])
              for (const ch of cofChords(k, minor)) for (const [m] of cofVoicing(ch, cofIvs(ch, sev, cofDom(ch, minor)), 1.6)) { n++; if (i !== 'piano' && (m < lo || m > hi)) bad++; }
            out[i] = [bad, n > 0];
          } return out""")
        for inst, (bad, any_) in got.items():
            with self.subTest(inst): self.assertEqual((bad, any_), (0, True))
        self.assertGreaterEqual(len(got), 8)

    def test_damaged_settings_do_not_stop_the_app(self):
        bad = [{"view": "zzz"}, {"inst": "zzz"}, {"tun": 99}, {"a4": "abc"}, {"a4": 0}, {"jam": {"mix": None}}, {"scl": {"root": 99, "type": 99}}]
        self.open()
        for v in bad:
            with self.subTest(v):
                self.js("localStorage.setItem('tune.state', arguments[0]); sessionStorage.clear()", json.dumps(v))
                self.reopen(1.5)
                self.assertTrue(self.js("return !!window.__up && !!document.querySelector('#hViews [data-v]')"))


@unittest.skipUnless(APP == "sing", "SING only")
class Sing(Page):
    def test_exercise_name_is_escaped(self):
        self.open()
        self.js("localStorage.setItem('sing.state', JSON.stringify({cex: [{name: arguments[0], n: [60, 62], d: [1, 1]}]}))", EVIL % "exercise")
        self.reopen(); self.tour(); self.assertClean()

    def test_damaged_settings_do_not_stop_the_app(self):
        bad = [{"view": "zzz"}, {"ex": "zzz"}, {"voice": "zzz"}, {"bpm": "abc"}, {"cex": [{"n": [], "d": []}]},
               {"cex": [{"name": "x", "n": [1, 2], "d": [1]}]}, {"key": 99}, {"vx": None}, {"game": None}]
        self.open()
        for v in bad:
            with self.subTest(v):
                self.js("localStorage.setItem('sing.state', arguments[0]); sessionStorage.clear()", json.dumps(v))
                self.reopen(1.5)
                self.assertTrue(self.js("return !!window.__up && !!document.querySelector('#hViews [data-v]')"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
