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
