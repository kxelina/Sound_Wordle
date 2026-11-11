# Sound Detective Main Branch Report

**Branch:** `main`  
**Revision reviewed:** `7b1d37f` (`Expand free composition with instruments, meters and multi-bar editing`)  
**Report date:** 2026-11-11

## Scope

This report describes the desktop application and tests present on `main` at the revision above. The separate `portable-web-edition` branch and its browser application are not part of this report or of `main`.

## Application Overview

Sound Detective is a Windows desktop sound-construction and music-restoration game built with Python, PySide6, and SuperCollider. The player investigates cases by listening to references or witness descriptions, editing sound controls or notes, auditioning changes, and submitting an answer. English and Traditional Chinese are supported.

## Player-Facing Functions

### Timbre Cases: T01–T09

Players recreate reference sounds by adjusting the available synthesis controls, introduced progressively across cases. Controls include harmonics, ADSR envelope, filters, delay, and reverb. T09, “The Extra Knock,” uses a short source event and delay to construct fading repeats; its optional cause question is ungraded.

### Sound Wordle: W01–W09

Players construct hidden sounds from witness clues. Submissions are unlimited and hints are free. The target remains hidden until the case requirements are met.

- **W01:** staged single-sound reconstruction using envelope, harmonics, and echo requirements.
- **W02:** a four-note phrase with rhythm, melody, and timbre stages.
- **W03–W06:** synthesized rain, bird-like chirps, plucked-string-like sound, and radio noise.
- **W07:** two-note doorbell; rhythm must pass before pitch is unlocked.
- **W08:** three short sounds over four beats, with a required silent third beat.
- **W09:** hollow electronic tone using grouped harmonic features and multiple acceptable harmonic balances.

Category cases W03–W06 and W09 offer Beginner, Standard, and Advanced difficulties with two, four, or five editable controls. Other controls remain fixed for that difficulty. Scores are based on authored sound-construction features and accepted ranges; they are not claims of measured perceptual similarity.

### Music Restoration: M01

M01 restores a locally supplied music recording in stages: Filter, Delay, Reverb, then Pitch. Repair checks and submissions are separate actions. Completion enables full-song playback. The recording and related evidence audio are local-only and are not included in the repository; M01 is unavailable when its required local assets are absent or invalid.

### Free Composition

Free composition is separate from the W02 challenge draft and is ungraded. It supports Synthesizer, Piano, Violin, and Guitar synthesized timbres; C2–C6 notes; chords; extendable bars; eight time signatures; 60–160 BPM; editable room, hall, and echo effects; undo/redo; save/load; playback; and WAV export. Notes can be edited in a multi-bar piano roll, including pitch, timing, and duration.

### Shared Player Features

- Five-step interactive tutorial with isolated practice state, skip, and replay.
- Automatic progress saving and recovery handling for invalid saves.
- Undo/redo for supported parameter and melody edits.
- Free hints, equipment navigation, and eligible control/device highlights.
- Submission-to-submission score changes and component improvement/setback summaries.
- First-clear case reviews with available starting, answer, and target audio, controls, score components, hints, and timing.
- Evidence cabinet for saved synthetic first-clear answers, with replay, inspection, and WAV export.
- Optional, opt-in local anonymous playtest logging with CSV export. It does not record microphone audio or upload participant data.
- Startup diagnostics, settings for language/volume/window size, and shared playback controls.

## Implementation Map

- `sound_detective/ui/studio.py`: main room, case board, tutorial/review flow, and case routing.
- `sound_detective/ui/device_panel.py`: embedded case equipment workspace.
- `sound_detective/ui/case_one.py`: timbre-case interface.
- `sound_detective/ui/hidden_sound.py`: W01.
- `sound_detective/ui/melody.py`: W02, W07, W08, and the W02-associated free-composition mode.
- `sound_detective/ui/sound_categories.py`: W03–W06 and W09.
- `sound_detective/ui/music_case.py`: M01 restoration interface.
- `sound_detective/game/`: case definitions, scoring, progress, save validation, reviews, evidence, and playtest records.
- `sound_detective/audio/` and `supercollider/`: synthesis, rendering, audio analysis, preview, playback, and export.
- `launcher/`: Windows launcher and offline installer packaging.

## Tests and Validation

The development suite contains 11 pytest modules:

`test_features.py`, `test_note_dragging.py`, `test_sound_categories.py`, `test_player_journey.py`, `test_learning_tools.py`, `test_after_hours.py`, `test_wire_ghost.py`, `test_submission_guidance.py`, `test_knock_volume.py`, `test_device_workspace.py`, and `test_composition_studio.py`.

The tests cover game rules and save integrity, user journeys, UI state/layout, melody editing, composition, audio rendering, WAV export, hints, review/evidence flows, and optional music assets. Separate `validate_*_ui.py` scripts exercise selected real Qt scenes and audio workflows. The documented pytest command and required dependencies are in the root README and `SoundDetectiveDevelopment/README.md`.

Existing validation records are historical results for particular environments. They are not a fresh test run for every machine or a substitute for perceptual or educational research.

## Scope and Limitations

- This is the desktop application on `main`; the standalone app in `PortableWeb/` exists only on the separate `portable-web-edition` branch.
- Windows is the documented desktop launch target for this branch. The Windows executable/installer requires its corresponding packaged runtime; source launch requires Python dependencies and SuperCollider.
- M01 requires separately supplied local recording assets.
- Construction scores and guidance are software rules; they do not establish human listening similarity, learning effectiveness, or user-study results.
