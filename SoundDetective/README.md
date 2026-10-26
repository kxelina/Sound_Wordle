# Sound Detective

*Every sound leaves a trace.*

[English player guide](#english-player-guide) · [繁體中文玩家指南](#繁體中文玩家指南)

## English player guide

Welcome to your sound detective's workspace. Listen to evidence, investigate what has changed, and use the equipment on your desk to reconstruct sounds and restore music. You can also enter the music studio to compose your own melody.

The game currently includes **eight timbre cases, one music-restoration case, six hidden-sound challenges, and free composition**.

### Start playing

If you received **SoundDetective-Setup.exe**, run it and choose an empty folder you can write to. The installer includes the software needed to run the game and can create a desktop shortcut. Existing game folders and saves will not be overwritten.

If you already have the game folder, open **SoundDetective.exe**.

1. Select **Start Game** to enter the room.
2. Click the **board on the wall** to choose a mode and case, then select **Accept case**.
3. Click the **desk or mixing console** to move closer.
4. Click a piece of equipment to open its controls.

The desk and board have highlighted outlines to help you find them. Use **Back to desk** to change equipment and the wall board to change activities. New players can start with **T01**.

Open **Settings** to change window size, volume or language. The default language is English; select **繁體中文** for Traditional Chinese. Headphones can help you hear small differences.

### Choose an activity

| Activity | What you do |
| --- | --- |
| **Timbre Cases · T01–T08** | Listen to a reference tone and recreate it. Cases gradually introduce envelopes, harmonics, filters, delay and reverb. |
| **Music Studio · M01** | Restore a distorted recording, one step at a time: **Filter → Delay → Reverb → Pitch**. Completing every step unlocks playback of the full original song. |
| **Sound Wordle · W01** | Build a hidden sound from witness clues. The target becomes playable after you meet all three stages' requirements. |
| **Sound Wordle · W02** | Reconstruct a hidden phrase in three stages: **rhythm → melody → timbre**. The target is revealed after completion. |
| **Sound Wordle · W03–W06** | Choose **Nature**, **Instruments** or **Noise / electronics** and synthesize rain, bird-like chirps, a plucked note or radio static from witness clues. |
| **Free composition** | Choose this card under **Music Studio**. Write a one-bar melody on a 16-step grid, adjust its sound and effects, and choose a tempo of 60–160 BPM. There is no score. |

The hidden-sound challenges allow unlimited submissions and free hints. In W01/W02, **Hear the concept** plays a teaching example when you need help understanding a sound feature.

Free composition supports one note at a time, within C4–C5. Its draft is saved separately from your W02 challenge, so you can switch between them without replacing either draft.

### Build a sound by category

On the wall board, choose **Sound Wordle**, then a sound category. The original W01/W02 challenges remain under **Signals / melody**.

| Case | Sound | Main controls |
| --- | --- | --- |
| **W03 · Nature** | Gentle rain at the window | Drop density, brightness, drop length, continuous rain curtain and intensity movement |
| **W04 · Nature** | Short, rising bird-like whistles | Centre pitch, pitch glide, chirp length, spacing and harmonic colour |
| **W05 · Instruments** | A plucked string-like note | Pitch, decay, brightness, body tone and pick noise |
| **W06 · Noise / electronics** | An untuned radio | Noise bandwidth, pink-noise blend, flutter depth/speed and crackles |

Accept a case, open the desk's **Synthesizer**, and use **Sound sources** to shape it. Each case starts with a rough sound and five relevant controls. These are stylized synthesized sounds; no bird or rain recording is played underneath.

In W04, drag the two points on the pitch curve up or down to shape the chirp. Drag the right point left or right to shorten or lengthen it. Knobs and number fields update with the curve.

The witness description is available immediately. **More help** gives three free layers: the largest difference, the control and direction to try, then a useful goal range. Help does not reduce progress. Submit whenever you want; edits and auditions do not count as attempts.

Each submission shows **construction progress**, with attribute results below. The score rewards moving toward accepted ranges for the sound's construction controls, rather than comparing audio waveforms. Multiple settings can pass. Reach **90 overall and at least 85 for every attribute** to reveal the reference and unlock A/B playback. This value is not a listening-similarity percentage.

**Analysis / versions** shows the measured spectrum and RMS envelope from your last audition. Open its **Versions** tab to restore one of your last 30 submissions. Gold is your sound; green is the revealed target. Play again after editing to update the plots. Reference settings appear here after completion. Extra Delay and Reverb are unused in these four cases.

**Export my WAV** saves the full 3.6-second stereo passage under **userdata/wordle/exports**. Export uses the same synthesized sound as auditioning and excludes your playback-volume setting. **Reset sound** resets controls while keeping attempts, clues and completion. Undo/redo works for these edits; progress is saved automatically.

### Get to know the equipment

Hover over buttons and controls for a short explanation of what they do.

| Control | What to listen for |
| --- | --- |
| **Harmonics · H1–H8** | Move the vertical faders to change the balance of the sound's components and its tone colour. |
| **ADSR** | Shape the start of the sound, its decay, its held level and its release after the note ends. |
| **Filter** | Change which frequency regions are reduced, making a sound brighter, darker or thinner. |
| **Delay** | Adjust repeated echoes, their spacing and how long they last. |
| **Reverb** | Adjust the sense of space and the reverberant tail. |
| **Audition deck** | Play the available evidence, your current version, or an A/B comparison. |

Drag a knob up or down to adjust it, or enter an exact value in the nearby number box. Hold **Shift** while dragging a knob for finer control. Locked controls become available when the current case or stage allows them.

After changing a setting, play your sound again to hear the update. Listening and editing do not count as submissions; only pressing **Submit** records an attempt.

### Scores and clues

**Timbre cases:** each submission shows your reconstruction progress. A score of **75 or more** unlocks a diagnosis for that submitted version. To clear the case, reach **90 overall**, with every scored module at **85 or more**. After editing, submit again for an updated score and diagnosis.

**Music restoration:** reach **90 or more** in each step, then submit to continue. In the pitch step, every marked region must also be within the tuning tolerance shown on screen. Completed repairs stay in place.

Scores guide you toward each case's goal; they are not percentages of how similar two sounds would seem to a listener. After a timbre case is solved, open its review to compare your answer with the target settings.

### Restore music and compare your progress

In M01, enable the current repair device, adjust its estimates, and listen to **My repair**. Turning a repair device off leaves that part of the distortion in place. Use **Check & get a clue** whenever you need a direction; checking does not add a submission.

Open **Audition & versions** to use the comparison tools:

- Set the start and end times, then play **My repair** to hear that passage. Enable **Loop repair** to repeat it.
- During pitch calibration, **Selected note** sets the range to the selected note and a little surrounding audio.
- **Remember version** keeps your current repair as a comparison reference.
- **Before → now** plays your remembered version followed by your latest repair over the same range.
- **Restore version** brings back the remembered controls. You can undo this action.
- Checking or submitting shows whether your score moved closer to or further from the goal compared with your previous check.

Each new restoration step starts a fresh comparison reference. Editing, changing the range, leaving the equipment screen or stopping playback cancels the current preview.

In the pitch view, drag **green note blocks** up or down, hold **Shift** for fine tuning, and double-click to audition a region. Grey blocks provide context and cannot be edited. This view changes pitch while keeping the recording's timing.

When the restoration is complete, the full original song plays on repeat. Use **Stop** on the audition deck or return to the main menu to end playback.

### Controls at a glance

| Action | Control |
| --- | --- |
| Learn what a control does | Hover over it |
| Undo an edit | **Ctrl+Z** or **Undo** |
| Redo an edit | **Ctrl+Y**, **Ctrl+Shift+Z** or **Redo** |
| Stop audio while using equipment | **Esc** or **Stop** |
| Add a note in W02 / free composition | Click an empty piano-roll cell |
| Move a composed note | Drag the note |
| Change a composed note's length | Drag either bright edge |
| Delete a composed note | Right-click it, or select it and press **Delete** |

Notes show their new pitch and length while you drag. Scroll vertically to reach other pitches; beat numbers stay visible.

Undo and redo retain your submissions, hints and cleared stages. Free composition and W02 have separate edit histories. History lasts for the current session; clearing a music-restoration step starts a new history. To edit a solved timbre case again, select **Restart case**.

### Saving and help

Your progress, current drafts and settings save automatically. Keep the **userdata** folder to retain them. To transfer progress to another installation, close both games and copy that folder into the new game folder. Keep the rest of the installed game folder together as well; moving only the entry EXE will not move the game.

If something is wrong:

- **No sound:** check the in-game volume and your Windows output device, then stop and play again.
- **A control is greyed out:** finish the current stage, or enable the relevant device if it is available.
- **A preview is preparing:** wait for it to finish. After another edit, play again to hear the latest version.
- **The score looks unchanged after an edit:** submit again; the displayed result belongs to the last submitted version.
- **The problem continues:** open **Settings → Startup diagnostics**. It checks the files and audio setup and lets you export a report to share when asking for help.

---

## 繁體中文玩家指南

歡迎來到你的聲音偵探工作室。聆聽證物、找出聲音的變化，再使用桌上的設備還原音色、修復音樂。你也可以進入音樂工作室，創作自己的旋律。

目前遊戲包含 **8 個音色案件、1 個音樂修復案件、6 個隱藏聲音挑戰，以及自由創作**。

### 開始遊戲

如果你拿到的是 **SoundDetective-Setup.exe**，執行它並選擇可寫入的空白資料夾。安裝包已包含遊戲需要的執行軟體，也可建立桌面捷徑；不會覆寫既有遊戲資料夾與存檔。

如果已經有完整遊戲資料夾，直接開啟 **SoundDetective.exe**。

1. 點選「**開始遊戲**」，進入房間。
2. 點擊牆上的「**案件板**」，選擇玩法與案件，再按「**接受案件**」。
3. 點擊「**工作桌或調音台**」，靠近桌上的設備。
4. 點擊一台設備，開啟它的控制介面。

桌子和案件板會有高亮描邊，方便辨認。按「返回桌面」可更換設備，點案件板可切換玩法。第一次遊玩建議從 **T01** 開始。

在「**設定**」中可以調整視窗大小、音量和語言。遊戲預設英文，選擇 **繁體中文** 即可切換介面。使用耳機會更容易聽出細微差異。

### 選擇玩法

| 玩法 | 你的任務 |
| --- | --- |
| **音色還原 · T01–T08** | 聆聽參照單音，調整設備來還原它。各關逐步介紹包絡、諧波、濾波、回聲與混響。 |
| **音樂工作室 · M01** | 分階段修復扭曲的錄音，順序為「**濾波 → 回聲 → 混響 → 音高**」。全部完成後，解鎖完整原曲播放。 |
| **聲音重建 · W01** | 根據證人口供製作隱藏的單音；三個階段都達標後，才可播放目標。 |
| **聲音重建 · W02** | 依序重建隱藏樂句的「**節奏 → 旋律 → 音色**」，完成後揭曉目標。 |
| **聲音重建 · W03–W06** | 選擇「自然聲音」「樂器聲音」或「噪聲與電子」，根據口供合成小雨、鳥鳴般的哨音、撥弦音或收音機雜音。 |
| **自由創作** | 在「音樂工作室」分類選擇此卡片。使用一小節、16 格的卷簾編寫旋律，調整音色與效果，並選擇 60–160 BPM 的速度；不評分。 |

隱藏聲音挑戰不限提交次數，提示免費。W01/W02 中遇到不熟悉的聲音特徵，可以按「**聽聽概念**」聆聽教學示例。

自由創作的音域為 C4–C5，一次演奏一個音。創作草稿與 W02 挑戰分開儲存，切換時會保留各自的內容。

### 依類別製作聲音

在牆上案件板選擇「**聲音重建**」，再選聲音類別。原有 W01/W02 保留在「**信號與旋律**」。

| 案件 | 聲音 | 主要控制 |
| --- | --- | --- |
| **W03 · 自然聲音** | 窗邊小雨 | 雨點密度、明亮度、雨滴長度、背景雨幕、雨勢變化 |
| **W04 · 自然聲音** | 短促上滑的鳥鳴般哨音 | 中心音高、音高滑動、鳥鳴長度、間隔、諧波色彩 |
| **W05 · 樂器聲音** | 撥弦般的單音 | 音高、衰減、明亮度、琴身厚度、撥弦雜音 |
| **W06 · 噪聲與電子** | 未調準的收音機 | 噪聲頻寬、粉紅噪聲比例、顫動深度／速度、爆裂聲 |

接受案件後，點桌上的「**合成器**」，使用「**聲源設備**」製作聲音。每關從一個粗略聲音開始，開放五個相關控制項。這些是具有相應特徵的合成聲音，沒有在底下播放真實鳥叫或雨聲錄音。

W04 的音高曲線可以直接操作：上下拖曳兩個端點改變音高，左右拖動右端點改變鳥鳴長度。旋鈕、數值框與曲線會同步更新。

一開始就能讀取口供。「**再給我一點幫助**」依序提供三層免費提示：主要差異、建議控制項及方向、可接受的目標範圍。提示不扣進度分數。調整和試聽不計次，只有提交才記錄一次嘗試。

每次提交顯示「**合成進度**」及分項結果。分數依合成控制所代表的聲音特徵與可接受範圍計算，允許不同設定通關，沒有直接比較音訊波形。達到**總分 90，各項至少 85**後，解鎖目標試聽與 A/B。此分數不是聽覺相似度百分比。

「**分析與版本**」顯示上次試聽的實測頻譜和 RMS 包絡；切換至「**版本記錄**」頁籤可恢復最近 30 次提交中的控制值。金色是你的聲音，綠色是通關後揭曉的目標；修改後請重新試聽以更新圖表。通關後此處也會顯示參考設定。這四關不使用額外的 Delay 或 Reverb。

「**匯出我的 WAV**」將完整 3.6 秒雙聲道片段存到 **userdata/wordle/exports**，與試聽使用相同合成結果，不套用播放音量。「**重設聲音**」只重設控制，保留提交、提示及通關記錄；可以撤銷／重做修改，進度會自動儲存。

### 認識桌上的設備

將滑鼠停在按鈕或控制項上，就能查看簡短的功能說明。

| 控制項 | 可以改變什麼 |
| --- | --- |
| **諧波 · H1–H8** | 上下推動推桿，改變聲音各個成分的比例，調整音色。 |
| **ADSR 包絡** | 調整聲音的起音、衰減、持續音量，以及音符結束後的尾音。 |
| **Filter 濾波** | 削弱不同頻段，讓聲音變亮、變暗或變薄。 |
| **Delay 回聲** | 調整重複回聲、回聲間隔與持續時間。 |
| **Reverb 混響** | 調整空間感與混響尾音。 |
| **試聽機** | 播放目前可用的證物、自己的版本，或依次進行 A/B 比較。 |

旋鈕可以上下拖曳，也可以在旁邊的數值框輸入精確數值。拖曳旋鈕時按住 **Shift**，可進行更細的調整。尚未開放的控制項會保持鎖定，直到目前案件或階段允許使用。

修改設定後，請再次播放，聽取更新後的聲音。試聽與調整不計次數；只有按「**提交**」才會記錄一次嘗試。

### 分數與線索

**音色案件：**每次提交都會顯示還原進度。本次提交達 **75 分**後，會開放該版本的診斷。通關需要**總分至少 90 分，而且每個計分模組至少 85 分**。再次修改後，請重新提交，取得更新的分數與診斷。

**音樂修復：**每個步驟達到 **90 分**後，提交即可繼續。音高校正階段還需要每個標記片段都進入畫面顯示的調音容差。已完成的修復會保持。

分數用來引導你接近案件目標，不代表人耳認為兩段聲音有多少百分比相似。音色案件通關後，可以開啟復盤，對照自己的答案與目標設定。

### 修復音樂與比較進度

在 M01 中，先啟用目前的修復設備，調整估計值，再播放「**目前還原**」。關閉修復器會保留該類失真。需要調整方向時，按「**檢查並取得提示**」；檢查不增加提交次數。

開啟「**試聽對比**」頁，即可使用以下工具：

- 設定起止秒數，再播放「目前還原」，試聽指定片段；勾選「**循環還原**」可重複播放。
- 音高校正階段可按「**選中音符**」，快速選取該音符及前後少許聲音。
- 「**記住版本**」會將目前修復記為對比基準。
- 「**之前 → 目前**」會在相同時間範圍內，依次播放記下的版本與最新修復。
- 「**恢復版本**」會恢復記下的控制項；這項操作也可以復原。
- 檢查或提交後，畫面會顯示分數相較上次檢查更接近或更遠離目標。

每個新的修復步驟都會建立新的對比基準。修改設定、變更範圍、離開設備畫面或停止播放，都會取消目前試聽。

進入音高畫面後，上下拖曳**綠色音塊**可調整音高；按住 **Shift** 可細調，雙擊可試聽片段。灰色音塊提供上下文參照，不能修改。這個畫面會保留錄音的時間位置。

完成修復後，完整原曲會循環播放。按試聽機的「**停止**」，或返回主選單，即可結束播放。

### 常用操作

| 操作 | 使用方式 |
| --- | --- |
| 查看功能說明 | 將滑鼠停在控制項上 |
| 復原編輯 | **Ctrl+Z** 或「復原」 |
| 重做編輯 | **Ctrl+Y**、**Ctrl+Shift+Z** 或「重做」 |
| 使用設備時停止聲音 | **Esc** 或「停止」 |
| 在 W02／自由創作中加音 | 點擊鋼琴卷簾的空格 |
| 移動創作的音符 | 拖曳音符 |
| 改變創作音符的長度 | 拖曳音符左右的亮色邊緣 |
| 刪除創作的音符 | 按右鍵，或選中後按 **Delete** |

拖曳時會即時顯示新的音高與長度。上下捲動可查看其他音高，拍數標記會保持可見。

復原與重做會保留提交、提示及已通過的階段。自由創作與 W02 各有獨立的編輯歷史。歷史只在本次遊玩期間保留；音樂修復通過一步後，會開始新的歷史。若要再次調整已通關的音色案件，請按「重新挑戰」。

### 保存與遇到問題時的處理

案件進度、目前草稿和設定會自動儲存。請保留 **userdata** 資料夾。需要將進度搬到另一份遊戲時，先關閉兩邊的遊戲，再將這個資料夾複製到新的遊戲目錄。其餘已安裝的遊戲檔案也請放在一起；只移動入口 EXE 不會搬走整個遊戲。

如果遇到問題：

- **沒有聲音：**檢查遊戲音量與 Windows 輸出裝置，再停止並重新播放。
- **控制項呈灰色：**先完成目前階段，或啟用已開放的相關設備。
- **畫面正在準備音訊：**等待試聽完成準備；再次修改後，重新播放即可聽取最新版本。
- **調整後分數沒變：**請再次提交；畫面上的成績屬於上次提交的版本。
- **問題仍未解決：**前往「**設定 → 啟動診斷**」，檢查遊戲檔案與音訊設定，也可以匯出報告，供尋求協助時使用。
