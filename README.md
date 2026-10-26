# Sound_Wordle

**Sound Detective — Every sound leaves a trace.**

A Windows desktop sound-construction game built with Python, PySide6 and SuperCollider.

- **T01–T09:** recreate timbres with harmonics, ADSR, filters, delay and reverb.
- **Sound Wordle:** build hidden sounds from witness clues, with unlimited submissions and free hints.
  W01/W02 cover a signal and a melody. W03/W04 cover rain and bird-like chirps,
  W05 a plucked string-like note, and W06 radio static. W07 is an original two-note doorbell; W08 reconstructs a rhythm with a required silent beat.
- **T09 · The Extra Knock:** use one short source event and Delay to reconstruct fading repeats, with an optional ungraded cause question.
- **Free composition:** write a melody using draggable piano-roll notes.
- **M01 music restoration:** included as code/configuration; song recordings are local-only and are not distributed here.
- English and Traditional Chinese interfaces, edit history, progress saves and WAV export.
- A five-step interactive tutorial and persistent first-clear reviews with audio comparisons.
- Category difficulties with 2/4/5 controls, one-control teaching examples, auto-updating loop auditions and an exportable evidence cabinet.
- Optional local anonymous playtest logs; no participant data is uploaded.

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

After creating the environment, you can use the Python entry above or **SoundDetective.exe**.
M01's local recordings are optional for startup: missing or unusable assets disable that
case while all synthesized challenges and free composition remain available.
The public offline installer can be built without those recordings using `--public`;
recordings and bundled installers are excluded from this source repository.
SuperCollider is invoked automatically; it does not need to be opened manually.

Choose **Learn to play** for isolated exercises in listening, Release, H2, chirp editing
and practice submission. Fresh players are offered the lesson on Start Game.
Cleared cases unlock a first-clear review with starting/answer/target auditions,
component progress, reference controls and available time/history. Music completion
keeps full-song playback; open that review manually.

The environments, temporary renders, user progress and bundled runtimes are excluded from Git.
Read [environment notes](SoundDetective/docs/ENVIRONMENT.md) for engine path configuration.

## Tests and records

After installing the dependencies, run the source-only Wordle and piano-roll checks from the repository root:

```powershell
.\SoundDetective\.venv\Scripts\python.exe -m pytest SoundDetectiveDevelopment/test_after_hours.py SoundDetectiveDevelopment/test_learning_tools.py SoundDetectiveDevelopment/test_player_journey.py SoundDetectiveDevelopment/test_sound_categories.py SoundDetectiveDevelopment/test_note_dragging.py -q
```

These checks include actual SuperCollider rendering. Some additional music-restoration
checks in `test_features.py` require the local M01 assets. Earlier full local validation
results are documented in [VALIDATION.md](SoundDetectiveDevelopment/VALIDATION.md);
they should not be confused with a perceptual study or results on another computer.

Validation records include a source checkout without M01 recordings and local checks
with those assets present. See the dated validation notes for exact counts and scope.

[Architecture](SoundDetective/docs/ARCHITECTURE.md) ·
[AI assistance and references](SoundDetective/docs/AI_ASSISTANCE.md)

---

## 繁體中文

**Sound Detective：每個聲音都留下線索。**

這是一款 Windows 桌面聲音合成遊戲，使用 Python、PySide6 與 SuperCollider。

- **T01–T09 音色案件：**調整諧波、ADSR、濾波、回聲與混響來還原聲音。
- **Sound Wordle：**依證人口供製作隱藏聲音，不限提交，提示免費。
  W01/W02 為信號及旋律；W03/W04 為小雨及鳥鳴般哨音；W05 為撥弦音；W06 為收音機雜音。
- **自由創作：**拖曳音符編寫旋律，調整音色並匯出 WAV。
- **M01 音樂修復：**保留程式與設定，原曲及證物錄音僅保存在本機。

新增 T09「多出來的一聲」、W07「會說話的門鈴」及 W08「空白的一拍」，不需要歌曲素材，各自保存進度並支援首次作品收藏。

[完整玩家指南：英文及繁體中文](SoundDetective/README.md)

安裝 Python 3.11 與 SuperCollider 後，依上方 PowerShell 指令建立環境，
並使用 `python -m sound_detective.play` 啟動此原始碼版本。
環境建立後，也可以使用原生 `SoundDetective.exe`。缺少或無法驗證 M01 音源時，只有歌曲案件暫不可玩，其他合成挑戰與自由創作仍可啟動。此倉庫不提供原曲錄音或完整執行環境；可用 `--public` 建立不帶歌曲的離線安裝包。

主選單「新手練習」提供獨立的五步操作教程，新玩家第一次開始遊戲時會獲得引導。通關後可查看首次結案復盤，比較起點、答案與目標聲音，查看分項進度及參考設定。音樂修復仍保留完整原曲播放，復盤手動開啟。

分類聲音另有入門／標準／進階難度、單控制教學示例、循環更新試聽及首次作品收藏；可選擇啟用本機匿名試玩記錄。

[開發測試與驗證紀錄](SoundDetectiveDevelopment/VALIDATION.md) ·
[外部資源及 AI 輔助紀錄](SoundDetective/docs/AI_ASSISTANCE.md)
