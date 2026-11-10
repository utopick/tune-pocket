# MIDI device diagram experiment

This branch adds OPTIONS → MIDI → DEVICE to each Pocket app. Connect MIDI first; choose an input port and diagram. Keys light on note-on and go dark on note-off (including note-on velocity zero). A key outside the displayed octave shifts the visible keyboard window. Click a drawn key to preview its note. The diagrams are original CSS schematics, not product photos; no network is needed at runtime.

To assign a real control: select a drawn key/pad/knob, select a Pocket function, click **LEARN FROM HARDWARE**, then press or turn that control. The binding uses the actual incoming channel and note/CC number, not a guessed factory map. Assignments persist per Pocket app and input-port name in localStorage. Inputs with the same name cannot currently be distinguished; use a different port name if available. The existing ASSIGN mapping remains a fallback for controls not assigned here. CLEAR CONTROL removes the selected diagram control's learned binding; it does not erase the older ASSIGN mappings.

Profiles inferred from `../../midi_test.txt` (the parent-folder test report is not part of this repository):

- **Synido Scale Pocket:** report shows notes on channel 1 and CC 64 sustain, but no pad/knob messages. Compact keyboard diagram; layout is provisional.
- **Akai MPK mini Play mk3:** report shows notes on channels 1 and 10, CC 2–8, CC 64, mod and pitch bend. The 25-key / eight-pad diagram is based on the [Akai product page](https://www.akaipro.com/mpk-mini-play-mk3/); knob layout is indicative, not a verified MIDI map.
- **Casio PX-S1100:** report shows A0–C8, channels 1–3 and CC 64. The diagram shows the 88-note range, not its non-MIDI front-panel buttons. [Casio product page](https://www.casio.com/us/electronic-musical-instruments/product.PX-S1100BK/).
- **Novation Launchkey:** no Launchkey report was recovered, so the exact generation/size and MIDI channel/pad map remain unknown. Select 25/37/49/61/88 keys to match your unit; pad/encoder placeholders are inspired by the [Novation Launchkey range](https://novationmusic.com/launchkey), not asserted as exact for every generation. Use LEARN for each control, especially the DAW port.

No manufacturer image was embedded or scraped. These schematics are intentionally approximate until the user tests the actual devices. Hardware-specific default control assignments would be unsafe without their MIDI messages; the learning workflow is functional in all three apps, using each app's existing `MI.actions()` list.

`midi-device.js` is copied identically into all three repositories. The Android `www` build and release HTML inline it so they remain standalone; the dev server loads it from each repo folder. Test with `node --check midi-device.js`, `cd android && npm run www`, and a browser with Web MIDI. Do not use the dev server's `@main` URL for uncommitted branch work.
