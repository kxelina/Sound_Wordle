# Sound Detective

A sound-making game about **synthesis** and **audio effects**. Listen to a sound,
adjust the controls, and see how close your answer is.

## What you can play

- **Timbre Cases (T01–T09):** recreate sounds with harmonics, envelopes, filters,
  delay, and reverb.
- **Sound Wordle (W01–W09):** follow clues to build hidden sounds. Submit as often as
  you like and use free hints.

For simple instructions on playing the game, read the
[English / 繁體中文 Player Guide](SoundDetective/docs/PLAYER_GUIDE.md).

## Run the game

Install **Python 3.11** and **SuperCollider** first.

### Windows

From PowerShell in the project folder:

```powershell
cd SoundDetective
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m sound_detective.play
```

### Linux

Install Python 3.11, SuperCollider, and the system packages needed by PySide6. Then
run these commands from the project folder:

```bash
cd SoundDetective
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-linux.txt
bash run-linux.sh
```

The launch check can verify the setup before starting the game:

```bash
cd SoundDetective
bash run-linux.sh --check
```

## Run tests

`pytest` is separate from the game's requirements. Install it once in the project's
virtual environment, then run the focused gameplay checks from the repository folder:

```bash
SoundDetective/.venv/bin/python -m pip install pytest
SoundDetective/.venv/bin/python -m pytest SoundDetectiveDevelopment/test_submission_guidance.py SoundDetectiveDevelopment/test_wire_ghost.py SoundDetectiveDevelopment/test_after_hours.py SoundDetectiveDevelopment/test_learning_tools.py SoundDetectiveDevelopment/test_player_journey.py SoundDetectiveDevelopment/test_sound_categories.py SoundDetectiveDevelopment/test_note_dragging.py -q
```

Some music-related tests require audio files that are not included in this repository.

## More information

- [Player Guide](SoundDetective/docs/PLAYER_GUIDE.md)
- [Environment setup](SoundDetective/docs/ENVIRONMENT.md)
- [Architecture](SoundDetective/docs/ARCHITECTURE.md)
- [Test and validation notes](SoundDetectiveDevelopment/VALIDATION.md)
