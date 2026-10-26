# Sound_Wordle

**Sound Detective — Every sound leaves a trace.**

A Windows desktop sound-construction game built with Python, PySide6 and SuperCollider.

- **T01–T08:** recreate timbres with harmonics, ADSR, filters, delay and reverb.
- **Sound Wordle:** build hidden sounds from witness clues, with unlimited submissions and free hints.
  W01/W02 cover a signal and a melody. W03/W04 cover rain and bird-like chirps,
  W05 a plucked string-like note, and W06 radio static.
- **Free composition:** write a melody using draggable piano-roll notes.
- **M01 music restoration:** included as code/configuration; song recordings are local-only and are not distributed here.
- English and Traditional Chinese interfaces, edit history, progress saves and WAV export.

[Full English / 繁體中文 player guide](SoundDetective/README.md)

## Run from source on Windows

Install **Python 3.11** and **SuperCollider** (the development machine uses 3.14.1).
From the repository folder, run PowerShell:

```powershell
cd SoundDetective
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m sound_detective.play
```

Use the Python entry above for this source checkout. The current native EXE entry performs
startup checks that also require M01's local music assets. Those recordings and the
complete offline installer are not included in the repository. With the Python entry,
missing M01 audio disables that case while the synthesized challenges and free composition remain available.
SuperCollider is invoked automatically; it does not need to be opened manually.

The environments, temporary renders, user progress and bundled runtimes are excluded from Git.
Read [environment notes](SoundDetective/docs/ENVIRONMENT.md) for engine path configuration.

## Tests and records

After installing the dependencies, run the source-only Wordle and piano-roll checks from the repository root:

```powershell
.\SoundDetective\.venv\Scripts\python.exe -m pytest SoundDetectiveDevelopment/test_sound_categories.py SoundDetectiveDevelopment/test_note_dragging.py -q
```

These checks include actual SuperCollider rendering. Some additional music-restoration
checks in `test_features.py` require the local M01 assets. Earlier full local validation
results are documented in [VALIDATION.md](SoundDetectiveDevelopment/VALIDATION.md);
they should not be confused with a perceptual study or results on another computer.

The source checkout was verified on the development Windows computer on October 26,
2026: **54 source-only checks passed with the M01 recordings omitted**.

[Architecture](SoundDetective/docs/ARCHITECTURE.md) ·
[AI assistance and references](SoundDetective/docs/AI_ASSISTANCE.md)

---

## 繁體中文

**Sound Detective：每個聲音都留下線索。**

這是一款 Windows 桌面聲音合成遊戲，使用 Python、PySide6 與 SuperCollider。

- **T01–T08 音色案件：**調整諧波、ADSR、濾波、回聲與混響來還原聲音。
- **Sound Wordle：**依證人口供製作隱藏聲音，不限提交，提示免費。
  W01/W02 為信號及旋律；W03/W04 為小雨及鳥鳴般哨音；W05 為撥弦音；W06 為收音機雜音。
- **自由創作：**拖曳音符編寫旋律，調整音色並匯出 WAV。
- **M01 音樂修復：**保留程式與設定，原曲及證物錄音僅保存在本機。

[完整玩家指南：英文及繁體中文](SoundDetective/README.md)

安裝 Python 3.11 與 SuperCollider 後，依上方 PowerShell 指令建立環境，
並使用 `python -m sound_detective.play` 啟動此原始碼版本。
目前原生 EXE 的啟動檢查仍要求 M01 的本機音源；此倉庫不提供那些錄音或完整離線安裝包。
使用 Python 入口時，缺少音源只會讓歌曲案件無法選擇，其他合成挑戰與自由創作仍可使用。

[開發測試與驗證紀錄](SoundDetectiveDevelopment/VALIDATION.md) ·
[外部資源及 AI 輔助紀錄](SoundDetective/docs/AI_ASSISTANCE.md)
