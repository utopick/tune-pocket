"""End-to-end checks for a Pocket app, driven through a real Chrome with Selenium.

The same file lives in track-pocket, tune-pocket, sing-pocket and play-pocket; it works out which app it is in from the folder name.
Setup (once):   python3 -m venv .venv && .venv/bin/pip install selenium
Run:            .venv/bin/python tests/e2e.py            (add -v for the names; HEAD=1 to watch the browser)
Needs Chrome installed; Selenium downloads the matching driver by itself.
"""
import functools, http.server, json, os, sys, threading, unittest, urllib.request
from selenium import webdriver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.basename(ROOT).split("-")[0]  # track | tune | sing | play
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


# a fake MIDI keyboard (an MPK mini Play mk3 by name): the tests send it messages with self.midi(...)
FAKE_MIDI = """(() => { const inp = { id: 'm', name: 'MPK mini Play mk3', manufacturer: 'AKAI', state: 'connected', type: 'input', onmidimessage: null }; window.__inp = inp;
  navigator.requestMIDIAccess = () => Promise.resolve({ inputs: new Map([['m', inp]]), outputs: new Map(), onstatechange: null, sysexEnabled: false }); })();"""


class Page(unittest.TestCase):
    """A fresh Chrome (empty storage) for each test."""
    def setUp(self):
        o = webdriver.ChromeOptions()
        if not os.environ.get("HEAD"): o.add_argument("--headless=new")
        o.add_argument("--mute-audio"); o.add_argument("--window-size=390,844"); o.add_argument("--autoplay-policy=no-user-gesture-required")
        if APP == "play":  # the rig needs an input: Chrome's pretend microphone (a beep), allowed without asking
            o.add_argument("--use-fake-device-for-media-stream"); o.add_argument("--use-fake-ui-for-media-stream")
        self.d = webdriver.Chrome(options=o)
        self.d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": HOOK})
        self.addCleanup(self.d.quit)

    def open(self, wait=0.8):
        self.d.get(BASE + "index.html"); self.d.implicitly_wait(0); __import__("time").sleep(wait)

    def js(self, code, *a): return self.d.execute_script(code, *a)

    def wait(self, s): __import__("time").sleep(s)

    def midi_open(self):
        self.d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": FAKE_MIDI})
        self.open()
        self.js("document.querySelector('#midiDev').click()"); self.wait(0.9)

    def midi_pads_open(self):
        """The fake MPK with eight pads on notes 36 to 43 (pad N is note 35 + N) and the MIDI device connected."""
        self.d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": FAKE_MIDI})
        self.open()
        self.js("localStorage.setItem('pocket.midi.hw.v1', JSON.stringify({'MPK mini Play mk3': {keys: 25, pads: 8, padCh: 9, padNotes: [[36,37,38,39,40,41,42,43]], ccs: [70,71,72,73,74,75,76,77], knobs: 8, cc0: 0}}))")
        self.reopen(); self.js("document.querySelector('#midiDev').click()"); self.wait(0.9)

    def pad(self, n, hold=0.1):
        self.midi(0x99, 35 + n, 100); self.wait(hold); self.midi(0x89, 35 + n, 0); self.wait(0.15)

    def midi(self, *d): self.js("window.__inp.onmidimessage({ data: new Uint8Array(arguments[0]) })", list(d))

    def reopen(self, wait=1.2): self.d.refresh(); self.wait(wait)

    def errors(self): return self.js("return window.__errs || []")

    def assertClean(self):
        self.assertEqual(self.js("return window.__pwned"), [], "script ran from data")
        self.assertEqual(self.errors(), [])

    def tour(self):
        """Open every view and every help page, in both themes."""
        for v in self.js("return [...document.querySelectorAll('#hViews [data-v], header > [data-v]')].map(e => e.dataset.v)"):
            self.js("document.querySelector('#hViews [data-v=\"%s\"], header > [data-v=\"%s\"]').click()" % (v, v)); self.wait(0.15)
        for th in ("dark", "light"):
            self.js("setTheme(arguments[0])", th)
            for s in self.js("return HELP.map(h => h.id)"):
                self.js("openHelp(arguments[0])", s); self.wait(0.05)
            self.js("closeHelp()")


class Common(Page):
    def test_boots_and_every_view_opens(self):
        self.open(); self.tour(); self.assertClean()

    # ---- MIDI: the MAP wizard and ASSIGN, on a fake keyboard
    def test_map_wizard_learns_a_keyboard_and_goes_back(self):
        self.midi_open()
        self.js("document.querySelector('#midiTest').click()"); self.wait(0.4)
        step = lambda: self.js("return document.querySelector('#mdWiz h3').textContent")
        self.midi(0x90, 60, 9); self.assertIn("LEFTMOST", step())
        self.midi(0x90, 48, 90); self.midi(0x90, 72, 90); self.assertIn("MOD KEY", step())
        self.midi(0x90, 48, 90)  # the leftmost key cannot be the mod key
        self.assertIn("MOD KEY", step())
        self.js("document.querySelector('[data-do=wizBack]').click()"); self.assertIn("RIGHTMOST", step())
        self.midi(0x90, 72, 90); self.assertIn("MOD KEY", step())
        self.midi(0xb0, 64, 127); self.assertIn("PADS", step())  # the pedal is the mod key
        for n in (36, 38, 42): self.midi(0x99, n, 100)
        self.midi(0x90, 72, 90); self.midi(0x90, 48, 90); self.assertIn("KNOBS", step())  # rightmost then leftmost ends the list
        for cc in (74, 71, 91, 99, 98, 6): self.midi(0xb0, cc, 50)  # 98 and 99 are NRPN selectors, not knobs
        for _ in range(8): self.js("var b = document.querySelector('[data-do=wizNext]'); b && b.click()")
        m = json.loads(self.js("return localStorage.getItem('pocket.midi.hw.v1')"))["MPK mini Play mk3"]
        self.assertEqual((m["keys"], m["ccs"], m["modKey"], m["padNotes"]), (25, [74, 71, 91, 6], "c0:64", [[36, 38, 42]]))
        self.assertEqual(self.errors(), [])

    def test_assign_takes_each_control_once(self):
        self.midi_open()
        if self.js("return MI.actions().filter((a) => a.kind === 'knob').length") < 3: self.skipTest("this app has fewer than three knob functions")
        self.js("document.querySelector('#midiMap').click()"); self.wait(0.3)
        self.js("document.querySelector('[data-ml=nokeys]').click(); MI.learn.i = MI.actions().findIndex((a) => a.kind === 'knob'); miLearnFace()")
        step = lambda: self.js("return MI.learn.i")
        first = step()
        for i in range(30): self.midi(0xb0, 74, i * 4); self.wait(0.05)  # one knob kept turning for 1.5 s
        self.assertEqual(step(), first + 1)
        self.wait(0.7)
        while self.js("return MI.actions()[MI.learn.i].kind") != "knob": self.js("miStep(1)")  # the next knob function
        n = step(); self.midi(0xb0, 71, 10); self.wait(0.6); self.assertEqual(step(), n + 1)
        while self.js("return MI.actions()[MI.learn.i].kind") != "knob": self.js("miStep(1)")
        n = step(); self.wait(0.6); self.midi(0xb0, 74, 99); self.wait(0.2); self.assertEqual(step(), n)  # taken already
        self.assertEqual(self.errors(), [])

    def test_function_mapper_holds_keys_skips_with_two_keys_and_maps_mod(self):
        self.midi_open()
        self.js("document.querySelector('#midiMap').click()"); self.wait(0.3)
        self.midi(0x90, 48, 90); self.midi(0x90, 72, 90)  # the leftmost and the rightmost key
        self.js("MI.learn.i = MI.actions().findIndex((a, i, l) => a.kind !== 'knob' && l[i + 1] && l[i + 1].kind !== 'knob'); miLearnFace()")
        i0 = self.js("return MI.learn.i")
        self.midi(0x99, 36, 100); self.wait(1.0); self.midi(0x89, 36, 0)  # let go early: not taken
        self.assertEqual(self.js("return Object.keys(MI.map).length"), 0)
        self.midi(0x90, 72, 90); self.midi(0x90, 48, 90)  # rightmost then leftmost: skip this function
        self.assertEqual(self.js("return MI.learn.i"), i0 + 1)
        self.wait(0.5); self.midi(0x99, 37, 100); self.wait(3.4)  # held 3 seconds: taken
        self.assertEqual(self.js("return MI.map['n9:37']"), self.js("return MI.actions()[%d].id" % (i0 + 1)))
        self.midi(0x89, 37, 0)
        self.js("MI.learn.i = MI.actions().findIndex((a) => a.kind !== 'knob' && !Object.values(MI.map).includes(a.id)); miLearnFace()")
        self.wait(0.5); self.midi(0xb0, 64, 127); self.midi(0x99, 38, 100); self.wait(3.4); self.midi(0x89, 38, 0); self.midi(0xb0, 64, 0)  # MOD + a pad
        self.assertIn("m+n9:38", self.js("return Object.keys(MI.map)"))
        self.midi(0x90, 48, 90); self.midi(0x90, 72, 90)  # leftmost then rightmost: done
        self.assertIsNone(self.js("return MI.learn"))
        self.assertEqual(self.errors(), [])

    def test_sustain_pedal_is_the_mod_key_and_the_switch_turns_it_off(self):
        self.midi_open()
        self.js("document.querySelector('#midiView').click()"); self.wait(0.3)
        self.midi(0xb0, 64, 127)
        self.assertTrue(self.js("return !!document.querySelector('#mdHint') && /MOD held/.test(document.querySelector('#mdHint').textContent)"))
        self.midi(0xb0, 64, 0)
        self.js("document.querySelector('[data-do=close]').click(); document.querySelector('#midiMod').click()"); self.wait(0.2)
        self.assertEqual(self.js("return document.querySelector('#midiMod').textContent"), "MOD OFF")
        self.assertEqual(self.errors(), [])

    # ---- MIDI: hostile input, every MAP step, state across a reload (QA additions)
    STEPS = ["CONNECTION", "LEFTMOST", "RIGHTMOST", "MOD KEY", "PADS", "KNOBS", "SUSTAIN", "STICK", "PLAY", "STOP", "RECORD", "OTHER FUNCTION"]

    def step(self): return self.js("var h = document.querySelector('#mdWiz:not([hidden]) h3'); return h ? h.textContent : ''")

    def click(self, sel): self.js("document.querySelector(arguments[0]).click()", sel)

    def test_map_back_works_at_every_step_and_cancel_keeps_nothing(self):
        self.midi_open()
        self.click("#midiTest"); self.wait(0.4)
        self.assertTrue(self.js("return document.querySelector('[data-do=wizBack]').disabled"), "BACK at the first step")
        self.midi(0x90, 60, 9); self.midi(0x90, 48, 90); self.midi(0x90, 72, 90)
        for want in self.STEPS[3:]:
            self.assertIn(want, self.step()); self.click("[data-do=wizNext]") if want != "OTHER FUNCTION" else None
        for want in reversed(self.STEPS[:-1]):  # BACK from each step to the one before it
            self.click("[data-do=wizBack]"); self.assertIn(want, self.step())
        self.click("[data-do=wizNext]"); self.click("[data-do=wizNext]")  # NEXT at LEFTMOST skips both key steps
        self.assertIn("MOD KEY", self.step())
        self.click("[data-do=wizBack]"); self.assertIn("LEFTMOST", self.step())  # and BACK goes round them too
        self.click("[data-do=wizCancel]")
        self.assertEqual(self.step(), "")
        self.assertIsNone(self.js("return localStorage.getItem('pocket.midi.hw.v1')"))
        self.assertEqual(self.errors(), [])

    def test_map_is_kept_after_a_reload_and_reset_map_forgets_it(self):
        self.midi_open()
        self.click("#midiTest"); self.wait(0.4)
        self.midi(0x90, 60, 9); self.midi(0x90, 48, 90); self.midi(0x90, 72, 90); self.click("[data-do=wizNext]")
        self.click("[data-do=wizNext]")  # no pads
        for cc in (20, 21, 22): self.midi(0xb0, cc, 30)
        self.midi(0x90, 72, 90); self.midi(0x90, 48, 90)  # rightmost then leftmost ends the knobs
        while self.step(): self.click("[data-do=wizNext]")
        self.reopen(); self.click("#midiDev"); self.wait(0.9); self.click("#midiView"); self.wait(0.4)
        self.assertEqual(json.loads(self.js("return localStorage.getItem('pocket.midi.hw.v1')"))["MPK mini Play mk3"]["ccs"], [20, 21, 22])
        self.midi(0xb0, 21, 40)
        self.assertIn("Knob 2", self.js("return document.querySelector('#mdHint').textContent"), "the map was not used after the reload")
        self.assertFalse(self.js("return document.querySelector('#mdUnmap').hidden"))
        self.click("#mdUnmap")
        self.assertTrue(self.js("return document.querySelector('#mdUnmap').hidden"))
        self.assertNotIn("MPK mini Play mk3", json.loads(self.js("return localStorage.getItem('pocket.midi.hw.v1')")))
        self.midi(0xb0, 21, 41)
        self.assertNotIn("Knob", self.js("return document.querySelector('#mdHint').textContent"), "RESET MAP kept the knobs")
        self.assertEqual(self.errors(), [])

    IMPORT = """const dt = new DataTransfer(); dt.items.add(new File([arguments[0]], 'map.json', {type: 'application/json'}));
      const i = document.querySelector('#mdFile'); i.files = dt.files; i.dispatchEvent(new Event('change'));"""

    def test_import_refuses_damaged_and_oversized_device_maps(self):
        self.midi_open()
        self.click("#midiView"); self.wait(0.4)
        hint = lambda: self.js("return document.querySelector('#mdHint').textContent")
        hw = lambda: self.js("return localStorage.getItem('pocket.midi.hw.v1')")
        for text, want in (("{broken", "not a device map"), ("null", "not a device map"), ("[]", "not a device map"), ('{"format": "other", "map": {"keys": 25}}', "not a device map"),
                           ('{"format": "pocket-device", "map": {"keys": 9999, "ccs": ["x"], "fn": {"play": "<script>"}}}', "Nothing usable"),
                           ('{"format": "pocket-device", "map": "keys"}', "Nothing usable")):
            with self.subTest(text):
                self.js(self.IMPORT, text); self.wait(0.3)
                self.assertIn(want, hint()); self.assertIsNone(hw())
        self.js("document.querySelector('#mdHint').textContent = 'x'")
        self.js(self.IMPORT, '{"format": "pocket-device", "map": {"keys": 61}, "pad": "%s"}' % ("x" * 120000)); self.wait(0.3)  # over 100 kB: not read at all
        self.assertEqual((hint(), hw()), ("x", None))
        self.js(self.IMPORT, json.dumps({"format": "pocket-device", "model": "generic", "name": EVIL % "import", "map": {"keys": 61, "ccs": [20, 21], "extra": EVIL % "map"}})); self.wait(0.3)
        self.assertIn("Map imported", hint())
        self.assertEqual(json.loads(hw())["MPK mini Play mk3"], {"keys": 61, "ccs": [20, 21], "knobs": 2, "cc0": 0})
        self.click("[data-do=report]"); self.click("[data-do=export]"); self.wait(0.3)
        self.assertClean()

    # (was a bug, fixed) importHw checks the model with PROFILES[o.model], so "constructor" / "__proto__" / "toString" pass and are kept
    def test_import_keeps_only_a_known_model(self):
        self.midi_open()
        self.click("#midiView"); self.wait(0.4)
        self.js(self.IMPORT, '{"format": "pocket-device", "model": "constructor", "map": null}'); self.wait(0.3)
        rec = json.loads(self.js("return localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('pocket.midi.devices.v1.')))") or "{}")
        self.assertNotEqual(rec.get("MPK mini Play mk3", {}).get("profile"), "constructor")

    def test_device_with_a_hostile_name_is_shown_as_text(self):
        evil = EVIL % "device"
        self.d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": FAKE_MIDI.replace("'MPK mini Play mk3'", json.dumps(evil))})
        self.open(); self.click("#midiDev"); self.wait(0.9)
        self.click("#midiView"); self.wait(0.4)
        self.midi(0x90, 60, 90); self.midi(0xb0, 74, 10)
        self.click("[data-do=map]"); self.midi(0x90, 60, 9); self.click("[data-do=wizCancel]")
        self.click("[data-do=report]"); self.click("[data-do=lights]"); self.click("[data-do=close]")
        self.assertClean()

    ODD = [[0xf0, 0x7f, 0x7f, 0x06, 0x02, 0xf7], [0xf0, 1, 2, 3, 0xf7], [0xf8], [0xfe], [0xfa], [0xfc], [0xff], [0xf2, 1, 2], [60, 100], [0x90], [0x90, 61],
           [0x9f, 62, 100], [0x8f, 62, 0], [0x90, 63, 0], [0x99, 36, 0], [0xbf, 74, 127], [0xb0, 99, 0], [0xb0, 98, 55], [0xb0, 6, 64], [0xb0, 38, 1], [0xb0, 101, 127], [0xb0, 100, 127],
           [0xa0, 60, 10], [0xd0, 10], [0xc0, 5], [0xe0, 0, 64], [0xef, 127, 127], [0xb0, 120, 0], [0xb0, 123, 0]]

    def test_odd_midi_messages_do_not_throw_anywhere(self):
        self.midi_open()
        def burst():
            for d in self.ODD: self.midi(*d)
            self.midi(0xb0, 64, 0)  # let the pedal up again
        burst()  # straight to the app
        self.click("#midiView"); self.wait(0.3); burst()  # with the panel open
        self.click("[data-do=map]"); burst()  # while MAP listens
        self.click("[data-do=wizCancel]"); self.click("[data-do=close]")
        self.click("#midiMap"); self.wait(0.3); burst()  # while ASSIGN listens
        self.midi(0x90, 48, 90); self.midi(0x90, 72, 90); burst()
        self.js("midiAssignEnd()"); self.wait(0.2)
        self.assertEqual(self.errors(), [])

    def test_closing_the_panel_mid_map_gives_the_messages_back(self):
        self.midi_open()
        self.click("#midiTest"); self.wait(0.4)
        self.midi(0x90, 60, 9); self.midi(0x90, 48, 90)
        self.click("[data-do=close]")
        self.assertFalse(self.js("return !!midiPanel.observe([0x90, 60, 100], 'MPK mini Play mk3')"), "MAP still takes the messages")
        self.click("#midiView"); self.wait(0.3)
        self.assertEqual(self.step(), "")
        self.assertIsNone(self.js("return localStorage.getItem('pocket.midi.hw.v1')"))
        self.assertEqual(self.errors(), [])

    # (was a bug, fixed) observe() skips modTrack while MAP listens, so a pedal let go during MAP leaves the second set on
    def test_mod_let_go_during_map_does_not_stay_held(self):
        self.midi_open()
        self.midi(0xb0, 64, 127)
        self.assertTrue(self.js("return midiPanel.layerOf('MPK mini Play mk3')"))
        self.click("#midiTest"); self.wait(0.3)
        self.midi(0xb0, 64, 0)
        self.click("[data-do=wizCancel]"); self.click("[data-do=close]")
        self.assertFalse(self.js("return midiPanel.layerOf('MPK mini Play mk3')"), "MOD stuck on after MAP")

    def test_two_devices_each_keep_their_own_map(self):
        two = FAKE_MIDI.replace("window.__inp = inp;", "window.__inp = inp; const lk = { id: 'l', name: 'Launchkey 37 MIDI', manufacturer: 'Novation', state: 'connected', type: 'input', onmidimessage: null }; window.__lk = lk;").replace("new Map([['m', inp]])", "new Map([['m', inp], ['l', lk]])")
        self.d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": two})
        self.open(); self.click("#midiDev"); self.wait(0.9)
        self.assertEqual(self.js("return MI.names.length"), 2)
        self.click("#midiView"); self.wait(0.3)
        self.assertEqual(self.js("return [...document.querySelectorAll('#mdSource option')].map(o => o.value)"), ["MPK mini Play mk3", "Launchkey 37 MIDI"])
        self.js("const s = document.querySelector('#mdSource'); s.value = 'Launchkey 37 MIDI'; s.dispatchEvent(new Event('change'))")
        self.assertEqual(self.js("return document.querySelector('#mdProfile').value"), "novation37")
        lk = lambda *d: self.js("window.__lk.onmidimessage({ data: new Uint8Array(arguments[0]) })", list(d))
        self.click("[data-do=map]")
        self.midi(0x90, 60, 90)  # the other device: MAP does not listen to it
        self.assertIn("CONNECTION", self.step())
        lk(0x90, 60, 9); lk(0x90, 48, 90); lk(0x90, 84, 90)
        while self.step(): self.click("[data-do=wizNext]")
        hw = json.loads(self.js("return localStorage.getItem('pocket.midi.hw.v1')"))
        self.assertEqual(list(hw), ["Launchkey 37 MIDI"]); self.assertEqual(hw["Launchkey 37 MIDI"]["keys"], 37)
        lk(0xb0, 64, 127)
        self.assertEqual(self.js("return [midiPanel.layerOf('Launchkey 37 MIDI'), midiPanel.layerOf('MPK mini Play mk3')]"), [True, False])
        lk(0xb0, 64, 0)
        self.assertEqual(self.errors(), [])

    def test_assign_moves_a_control_from_one_function_to_the_next(self):
        self.midi_open()
        self.click("#midiMap"); self.wait(0.3)
        self.js("document.querySelector('[data-ml=nokeys]').click(); MI.learn.i = MI.actions().findIndex((a) => a.kind !== 'knob'); miLearnFace()")
        a = self.js("return MI.actions()[MI.learn.i].id")
        self.wait(0.5); self.midi(0x99, 37, 100); self.wait(3.4); self.midi(0x89, 37, 0)
        self.assertEqual(self.js("return MI.map['n9:37']"), a)
        self.js("midiAssignEnd()")
        # a second run: the same pad for another function takes it away from the first one (one control, one function)
        self.click("#midiMap"); self.wait(0.3)
        self.js("document.querySelector('[data-ml=nokeys]').click(); MI.learn.i = MI.actions().findIndex((x) => x.kind !== 'knob' && x.id !== arguments[0]); miLearnFace()", a)
        b = self.js("return MI.actions()[MI.learn.i].id")
        self.wait(0.5); self.midi(0x99, 37, 100); self.wait(3.4); self.midi(0x89, 37, 0)
        self.assertEqual(self.js("return MI.map"), {"n9:37": b})
        self.assertEqual(self.errors(), [])

    # (was a bug, fixed) miLearnMsg only ignores the MOD key when it is a CC, so a MOD key MAP found on a note starts a 3 s hold itself
    def test_assign_with_a_mod_key_on_a_note(self):
        self.d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": FAKE_MIDI})
        self.open()
        self.js("localStorage.setItem('pocket.midi.hw.v1', JSON.stringify({'MPK mini Play mk3': {keys: 25, modKey: 'n0:50'}}))")
        self.reopen(); self.click("#midiDev"); self.wait(0.9)
        self.click("#midiMap"); self.wait(0.3)
        self.js("document.querySelector('[data-ml=nokeys]').click(); MI.learn.i = MI.actions().findIndex((a) => a.kind !== 'knob'); miLearnFace()")
        self.wait(0.5); self.midi(0x90, 50, 100); self.wait(0.2); self.midi(0x99, 38, 100); self.wait(3.4); self.midi(0x89, 38, 0); self.midi(0x80, 50, 0)  # MOD (a key) + a pad
        self.assertEqual(list(self.js("return MI.map")), ["m+n9:38"])

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
    def test_midi_pads_follow_the_screen(self):
        self.midi_pads_open()
        self.assertIsNone(self.js("return MI.defaults().pads"))  # the editor: keys, and drum pads on a drum channel
        self.js("pkGo('pats')"); self.wait(0.3)
        self.assertEqual(self.js("return MI.defaults().pads.slice(0, 2).map((p) => p[0])"), ["pad0", "pad1"])
        n = self.js("return song.patterns.length")
        self.assertLess(n, 8)
        self.pad(n + 1); self.wait(0.3)  # the pad over the "+" square (left to right, from the top left) makes a new pattern
        self.assertEqual(self.js("return song.patterns.length"), n + 1)
        self.js("showTab('smp')"); self.wait(0.3)
        self.assertEqual(self.js("return MI.defaults().pads.length"), 16)
        self.pad(3); self.wait(0.2)
        self.assertEqual(self.js("return S.smpSel"), 2)  # pad 3 is the third sample square
        self.js("showTab('trk'); pkGo('edit')"); self.wait(0.3)
        self.assertIsNone(self.js("return MI.defaults().pads"))
        self.assertEqual(self.errors(), [])

    def song(self, mutate):
        return self.js("const e = JSON.parse(serialize()); (%s)(e); return e" % mutate)

    def test_midi_variator_knobs_and_pads(self):
        self.d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": FAKE_MIDI})
        self.open()
        self.js("localStorage.setItem('pocket.midi.hw.v1', JSON.stringify({'MPK mini Play mk3': {keys: 25, pads: 8, padCh: 9, padNotes: [[36,37,38,39,40,41,42,43]], ccs: [70,71,72,73,74,75,76,77], knobs: 8, cc0: 0}}))")
        self.reopen(); self.js("document.querySelector('#midiDev').click()"); self.wait(0.9)
        self.js("document.querySelector('button[data-v=var]').click()"); self.wait(0.5)
        self.js("document.querySelector('#vVars').click()"); self.wait(0.3)
        for i in range(8): self.midi(0xb0, 70 + i, 0 if i % 2 == 0 else 127)
        self.wait(0.7)
        self.assertEqual(self.js("return [VAR.k.dens, VAR.k.swing, VAR.k.fill, VAR.k.chg, VAR.k.range, VAR.k.rep, VAR.k.len, +$('#master').value]"), [0, 1, 0, 1, 0, 1, 0, 1])
        self.js("document.querySelector('#vChs').click(); VAR.low = 'pats'; varRender()"); self.wait(0.3)
        self.midi(0x99, 38, 100); self.wait(0.1); self.midi(0x89, 38, 0); self.wait(0.4)  # a short press: the song goes on from that pattern
        self.assertEqual(self.js("return [S.playing, S.mode, S.ordSel]"), [True, "song", 2])
        self.midi(0x99, 40, 100); self.wait(0.6); self.midi(0x89, 40, 0); self.wait(0.4)  # a held press loops it
        self.assertEqual(self.js("return [S.mode, VAR.liveSlot]"), ["live", 4])
        self.assertEqual(self.errors(), [])

    def test_keys_only_play_until_write_mode_is_on(self):
        self.open()
        wrote = lambda: self.js("return pat().ch[S.col][S.row] != null && pat().ch[S.col][S.row] !== 0")
        self.js("S.row = 3; pat().ch[S.col][3] = null; noteOn('t', 60, S.col, true)")
        self.assertFalse(wrote(), "the keys wrote with WRITE off")
        self.js("noteOff && 0; document.querySelector('#pkLive').click()")  # the button: WRITE
        self.assertTrue(self.js("return S.liveWrite"))
        self.js("noteOn('t2', 62, S.col, true)")
        self.assertTrue(wrote(), "the keys did not write with WRITE on")
        self.js("document.querySelector('#pkLive').click(); pat().ch[S.col][3] = null; S.row = 3")  # back to PLAY
        self.assertFalse(self.js("return S.liveWrite"))
        # tapping a square while stopped turns WRITE on
        self.js("document.querySelector('#sq .sq').dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, pointerId: 7, clientX: 5, clientY: 5})); dispatchEvent(new PointerEvent('pointerup', {pointerId: 7, clientX: 5, clientY: 5}))")
        self.assertTrue(self.js("return S.liveWrite"), "a tapped square did not turn WRITE on")
        self.assertEqual(self.errors(), [])

    def test_a_square_tapped_while_playing_keeps_the_keys_on_play(self):
        self.open()
        self.js("togglePlay()"); self.wait(0.3)
        self.js("document.querySelector('#sq .sq').dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, pointerId: 8, clientX: 5, clientY: 5})); dispatchEvent(new PointerEvent('pointerup', {pointerId: 8, clientX: 5, clientY: 5}))")
        self.assertFalse(self.js("return S.liveWrite"), "a square tapped while playing turned WRITE on")
        self.js("togglePlay()")
        self.assertEqual(self.errors(), [])

    def test_song_file_cannot_run_script(self):
        self.open()
        self.js("""const e = JSON.parse(serialize());
          e.song.name = arguments[0]; e.song.patterns[0].name = arguments[1]; e.song.mix[0].preset = arguments[2];
          loadData(e); showTab('mix'); showTab('trk'); varEnter(); document.querySelector('#vExp').click();""",
                EVIL % "song name", EVIL % "pattern name", EVIL % "preset")
        self.wait(0.6); self.assertClean()

    def test_variator_builds_a_song_for_every_style_and_seed(self):
        self.open()
        bad = self.js("""const out = [];
          for (const s of Object.keys(V_STY)) for (let i = 0; i < 400; i++) { VAR.style = s; VAR.seed = String((i * 2654435 + 12345) % 100000000);
            try { varBuild(); } catch (e) { out.push(s + " " + VAR.seed + " " + e.message); if (out.length > 5) return out; } }
          return out""")
        self.assertEqual(bad, [])

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
    def test_midi_pads_follow_the_screen(self):
        self.midi_pads_open()
        self.js("document.querySelector('button[data-v=cof]').click()"); self.wait(0.4)
        self.assertEqual(self.js("return [MI.holdDefaults(), MI.defaults().pads.length > 0]"), [False, True])
        self.pad(3); self.wait(0.1)  # pad 3: the third chord of the key
        self.assertTrue(self.js("return !!document.querySelector('#cofPads [data-ch=\"2\"].lit')"))
        self.js("document.querySelector('button[data-v=loop]').click()"); self.wait(0.4)
        self.assertEqual(self.js("return MI.defaults().pads[0][0]"), "pad0")
        self.js("document.querySelector('#lPads').addEventListener('pointerdown', (e) => (window.__lp = e.target.closest('[data-p]').dataset.p), true)")
        self.pad(2); self.wait(0.2)  # pad 2: the second loop pad (a recording needs the microphone, so only the touch is checked)
        self.assertEqual(self.js("return window.__lp"), "1")
        self.js("document.querySelector('button[data-v=jam]').click()"); self.wait(0.3)
        self.assertEqual(self.js("return MI.defaults().pads[0][0]"), "jfx:" + self.js("return JFX[0][0]"))  # the JAM keeps its own
        self.assertEqual(self.errors(), [])

    def test_tempo_is_locked_while_recording(self):
        self.open()
        self.assertEqual(self.js("const a = S.met.bpm; LP.rec = {i: 0}; setBpm(a + 40); const held = S.met.bpm === a; LP.rec = null; setBpm(a + 40); return [held, S.met.bpm === a + 40]"), [True, True])

    def test_every_jam_genre_plays(self):
        self.open()
        for g in self.js("return GENRES.map((x) => x[0])"):
            with self.subTest(g):
                self.js("document.querySelector('button[data-v=jam]').click(); document.querySelector('#genres [data-g=%s]').click(); if (!J.on) jamStart();" % g)
                self.wait(0.5)
                self.js("if (J.on) jamStop()")
                self.assertClean()

    def test_jam_knobs_are_master_swing_bass_bpm_chords_drums_on_midi(self):
        self.d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": FAKE_MIDI})
        self.open()
        self.js("localStorage.setItem('pocket.midi.hw.v1', JSON.stringify({'MPK mini Play mk3': {keys: 25, pads: 8, padCh: 9, padNotes: [[36,37,38,39,40,41,42,43]], ccs: [70,71,72,73,74,75,76,77], knobs: 8, cc0: 0}}))")
        self.reopen(); self.js("document.querySelector('#midiDev').click(); document.querySelector('button[data-v=jam]').click()"); self.wait(0.9)
        self.assertEqual(self.js("return [...document.querySelectorAll('#jKn b')].map((e) => e.textContent)"), ["MASTER", "SWING", "BASS", "BPM", "CHORDS", "DRUMS"])
        for i in range(6): self.midi(0xb0, 70 + i, 0 if i % 2 == 0 else 127)
        self.assertEqual(self.js("return [S.jam.master, S.jam.swing, S.jam.mix.bass, S.jam.bpm, S.jam.mix.chord, S.jam.mix.drums]"), [0, 0.5, 0, 220, 0, 1])
        self.assertEqual(self.errors(), [])

    # (was a bug, fixed) tune.state's jam.master / jam.swing are not checked on load; a bad value makes the band throw when it starts
    def test_damaged_jam_master_and_swing_do_not_stop_the_band(self):
        self.open()
        self.js("localStorage.setItem('tune.state', JSON.stringify({view: 'jam', jam: {master: 'loud', swing: 'x'}}))")
        self.reopen(1.5)
        self.js("setTimeout(() => { if (!J.on) jamStart(); }, 0)"); self.wait(0.8)
        self.js("if (J.on) jamStop()")
        self.assertEqual(self.errors(), [])

    def test_jam_knobs_drag_and_double_tap_back_to_default(self):
        self.open()
        self.js("document.querySelector('button[data-v=jam]').click()"); self.wait(0.3)
        self.js("jamKnob('master', 0.2); jamKnob('swing', 1); jamKnob('bpm', 1)")
        self.assertEqual(self.js("return [S.jam.master, S.jam.swing, S.jam.bpm]"), [0.2, 0.5, 220])
        self.js("jamKnob('master', null); jamKnob('swing', null)")  # what a double tap does
        self.assertEqual(self.js("return [S.jam.master, S.jam.swing]"), [0.8, None])
        self.reopen(); self.assertEqual(self.js("return [S.jam.master, S.jam.swing, S.jam.bpm]"), [0.8, None, 220])
        self.assertEqual(self.errors(), [])

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
    def test_midi_pads_follow_the_screen(self):
        self.midi_pads_open()
        self.assertEqual(self.js("return MI.defaults().pads[0][0]"), "pad0")  # the warm-up: the exercise squares
        self.pad(3); self.wait(0.3)
        self.assertEqual(self.js("return S.ex === EXS[2].id"), True)
        self.js("if (W.on) warmStop()")
        self.js("document.querySelector('#hViews [data-v=vox]').click()"); self.wait(0.3)
        self.assertEqual(self.js("return MI.defaults().pads[0][0]"), "vx0")  # the sampler keeps its own
        self.assertEqual(self.errors(), [])

    def test_master_and_tempo_knobs_on_midi(self):
        self.d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": FAKE_MIDI})
        self.open()
        self.js("localStorage.setItem('pocket.midi.hw.v1', JSON.stringify({'MPK mini Play mk3': {keys: 25, pads: 8, padCh: 9, padNotes: [[36,37,38,39,40,41,42,43]], ccs: [70,71,72,73,74,75,76,77], knobs: 8, cc0: 0}}))")
        self.reopen(); self.js("document.querySelector('#midiDev').click(); getCtx()"); self.wait(0.9)
        self.midi(0xb0, 70, 64)
        self.assertEqual(self.js("return [Math.round(S.master * 100), Math.round(ctx.masterGain.gain.value * 100), ctx.destination === ctx.masterGain]"), [50, 50, True])
        self.midi(0xb0, 73, 127)
        self.assertEqual(self.js("return S.bpm"), 160)
        self.assertEqual(self.errors(), [])

    # (was a bug, fixed) sing.state's master is not checked on load; getCtx() throws setting the gain and the first sound fails
    def test_damaged_master_volume_does_not_stop_the_sound(self):
        self.open()
        self.js("localStorage.setItem('sing.state', JSON.stringify({master: 'loud'}))")
        self.reopen(1.5)
        self.js("setTimeout(() => getCtx(), 0)"); self.wait(0.5)
        self.assertEqual(self.errors(), [])

    def test_play_button_stays_and_rec_is_in_the_ribbons(self):
        self.open()
        for v in self.js("return [...document.querySelectorAll('#hViews [data-v]')].map(e => e.dataset.v)"):
            self.js("document.querySelector('#hViews [data-v=\"%s\"]').click()" % v); self.wait(0.15)
            with self.subTest(v): self.assertTrue(self.js("const r = document.querySelector('#play').getBoundingClientRect(); return r.width > 0 && r.height > 0"), "the play button is hidden")
        self.assertTrue(self.js("return !!document.querySelector('#wRec') && !!document.querySelector('#sRec')"))
        self.assertEqual(self.js("return document.querySelectorAll('header #rec, header [id*=Rec]').length"), 0)
        self.assertEqual(self.errors(), [])

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


@unittest.skipUnless(APP == "play", "PLAY only")
class Play(Page):
    PUT = "return new Promise(ok => idbDo('readwrite', s => (arguments[0].forEach(r => s.put(r)), s.count()), arguments[1]).then(ok))"

    def test_every_control_has_a_title(self):
        self.open()
        for v in self.js("return [...document.querySelectorAll('header > [data-v]')].map(e => e.dataset.v)"):
            self.js("showView(arguments[0]); ['lEdit', 'lFxP'].forEach(i => document.querySelector('#' + i).hidden = false); document.querySelectorAll('.fpanel').forEach(e => e.hidden = false)", v)
            bare = self.js("return [...document.querySelectorAll('main button, main select, main input[type=range], #vTabs button, header button')].filter(b => b.offsetParent && !b.title && !b.closest('label[title]')).map(b => b.id || b.textContent.trim().slice(0, 20))")
            with self.subTest(v): self.assertEqual(bare, [])

    def test_board_file_and_saved_board_are_checked(self):
        self.open()
        got = self.js("""const k = FXI.od.knobs[0], fx = vetFx({ od: { on: 'yes', [k[0]]: 1e9 }, zzz: { on: true }, amp: 7 }), sl = vetSlots(['od', 'od', 'zzz', arguments[0], 'amp'].concat(Array(60).fill('cab')));
          return [fx.od.on, fx.od[k[0]] === k[3], 'zzz' in fx, sl.length, sl.filter(Boolean)]""", EVIL % "slot")
        self.assertEqual(got, [False, True, False, 27, ["od", "amp", "cab"]])
        for bad in ["[]", "7", '{"slots": "x", "fx": "x", "mix": 3, "loop": "x", "sel": {"pedal": 99}}', '{"slots": [1, {}], "fx": {"od": null}, "mix": {"gtr": {"v": "loud"}}, "loop": {"bpm": "fast", "sync": {}}}', "{broken"]:
            with self.subTest(bad):
                self.js("localStorage.setItem('play.state', arguments[0]); localStorage.setItem('play.lat', arguments[0]); localStorage.setItem('play.opts', arguments[0]); localStorage.setItem('play.audioIn', arguments[0])", bad)
                self.reopen(); self.tour()
                self.assertTrue(self.js("return S.slots.length === 27 && S.loop.bpm >= 40 && document.querySelector('#unit').children.length > 0"))
                self.assertClean()

    def test_track_name_is_escaped(self):
        self.open()
        self.js(self.PUT.replace("arguments[0]", "[{ id: 'x', name: arguments[0], size: 1, blob: new Blob(['x']) }, { id: 'y', name: 7 }, null].filter(Boolean)"), EVIL % "track", "tracks")
        self.reopen(); self.js("showView('tracks')"); self.wait(0.3)
        self.assertEqual(self.js("return TR.list.length"), 1)
        self.js("document.querySelector('#trList [data-del]').click()"); self.tour(); self.assertClean()

    def test_damaged_kept_loops_are_refused(self):
        self.open()
        self.js(self.PUT.replace("arguments[0]", """[{ id: 0, sr: 44100, bars: 99, a: 'x', o: -5, vol: 99, data: new Float32Array(44100) }, { id: 1, sr: 5, data: new Float32Array(44100) }, { id: 2, sr: 44100, data: 'AAAA' },
          { id: 3, sr: 44100, data: new Float32Array(3) }, { id: 99, sr: 44100, data: new Float32Array(44100) }, { id: 4 }]"""), None, "loops")
        self.reopen(); self.wait(0.5)
        self.assertEqual(self.js("return [LP.loops.filter(Boolean).length, LP.loops[0].bars, LP.loops[0].vol]"), [1, 2, 1.5])
        self.js("showView('loop')"); self.assertClean()

    def test_looper_records_the_input_and_keeps_the_loop(self):
        self.open()
        self.js("document.querySelector('#listen').click()"); self.wait(2.5)
        self.assertTrue(self.js("return A.mic && A.ctx.state === 'running'"), "not listening")
        self.js("showView('loop'); S.loop.bpm = 240; S.loop.bars = 1; lpPad(0)"); self.wait(5)  # one bar of count-in, one bar recorded
        self.assertTrue(self.js("return !!LP.loops[0] && !LP.rec && Math.abs(LP.loops[0].buf.duration - 1) < 0.05"))
        for b in ("lEditB", "lRev", "lNorm", "lQuant", "lUndo", "lFxB", "lAll"):
            self.js("document.querySelector('#' + arguments[0]).click()", b); self.wait(0.2)
        self.wait(1); self.reopen(1.5)
        self.assertEqual(self.js("return LP.loops.filter(Boolean).length"), 1)
        self.assertEqual(self.errors(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
