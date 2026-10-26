# Sound Detective pilot playtest

This is a procedure to run with actual participants, not measured results.

## Preparation

- Recruit 6–10 willing classmates, ideally beginners. No in-app name is required.
- Use a separate game folder or progress directory for each participant. Keep existing player progress.
- Use the same volume, headphones and short tutorial. Let participants finish a simple practice task before observing the main cases.
- Pick two category cases and a difficulty in advance. Use the same tasks across participants, balancing which case is played first. Do not demonstrate the hidden answers beforehand.

## Each task

1. Open Analysis / versions → Playtest log and enable recording before the task.
2. Ask the participant to use the witness description to build the sound, request help if needed, and submit. Keep submissions unlimited. Set a three-minute observation limit externally, without changing normal gameplay.
3. Observe whether the participant understands the controls, hears a useful difference, and knows what to try next. Record the first point where help is needed. Avoid coaching them into a particular numerical answer.
4. At completion or the time limit, stop recording and export CSV. Keep incomplete tasks and failed submissions.
5. Record a short usefulness rating (1–5), difficulty rating (1–5), and one free comment. Use the anonymous ID shown in the CSV to relate these notes; do not put participant names into the game files.

Suggested observer sheet columns:

`anonymous_id, case, difficulty, completed, task_seconds, submissions, helpfulness_1_to_5, difficulty_1_to_5, first_obstacle, comment`

## Interpretation

The logs contain local elapsed times, event types, difficulty, attempt counts, submitted scores and example-control names. Edits and listening do not count as submissions. Pauses and time spent navigating may be included in elapsed time; the observer's task timer should define task duration. Recording is opt-in and can be disabled at any time. It does not record microphone audio or send information to a service.

The current logger supports exploratory observation. It does **not** automatically enforce blind A/B conditions, create unseen study targets, balance target difficulty or prove that hints improve learning. A later controlled study should freeze scores and assistance conditions, use distinct matched targets, counterbalance condition order and include incomplete tasks. Do not label ordinary play logs as such a study.

## Another Windows computer

Use the public installer on a second physical computer and check installation, first tutorial, English/Traditional Chinese, two window sizes, output device changes, category difficulty switching, loop stop/focus loss, collection export, save/reopen and free composition. Keep any error report and note Windows version/audio device. Results from the development computer do not replace this check.
