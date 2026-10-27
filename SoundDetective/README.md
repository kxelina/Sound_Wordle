# Sound Detective

*Every sound leaves a trace.*

[English player guide](#english-player-guide) · [繁體中文玩家指南](#繁體中文玩家指南)

## English player guide

Welcome to your sound detective's workspace. Listen to evidence, investigate what has changed, and use the equipment on your desk to reconstruct sounds and restore music. You can also enter the music studio to compose your own melody.

The game currently includes **nine timbre cases, one music-restoration case, nine hidden-sound challenges, and free composition**.

### Start playing

If you received **SoundDetective-Public-Setup.exe** or **SoundDetective-Setup.exe**, run it and choose an empty folder you can write to. The installer includes the software needed to run the game and can create a desktop shortcut. Existing game folders and saves will not be overwritten.

The public edition works without song recordings. M01 appears unavailable when its local music assets are missing or unusable; the timbre cases, Sound Wordle and free composition remain playable.

If you already have the game folder, open **SoundDetective.exe**.

1. Select **Start Game** to enter the room.
2. Click the **board on the wall** to choose a mode and case, then select **Accept case**.
3. Click the **desk or mixing console** to move closer.
4. Click a piece of equipment to open its controls.

The desk and board have highlighted outlines to help you find them. Use **Back to desk** to change equipment and the wall board to change activities. New players can start with **T01**.

Open **Settings** to change window size, volume or language. The default language is English; select **繁體中文** for Traditional Chinese. Headphones can help you hear small differences.

### Learn to play

A new player's first **Start Game** offers five separate exercises: audition a sound, shorten Release, raise H2, drag a chirp's pitch and length, and submit a practice answer. After editing, listen to your changed sound before continuing. The final exercise requires pressing **Practice submission**.

Use **Skip tutorial** whenever you want. You can reopen **Learn to play** from the main menu; existing players are not forced through the lesson. Practice controls, hints and submissions are separate from all cases. Finishing opens the case board.

### Choose an activity

| Activity | What you do |
| --- | --- |
| **Timbre Cases · T01–T09** | Listen to a reference tone and recreate it. Cases gradually introduce envelopes, harmonics, filters, delay and reverb. |
| **Music Studio · M01** | Restore a distorted recording, one step at a time: **Filter → Delay → Reverb → Pitch**. Completing every step unlocks playback of the full original song. |
| **Sound Wordle · W01** | Build a hidden sound from witness clues. The target becomes playable after you meet all three stages' requirements. |
| **Sound Wordle · W02** | Reconstruct a hidden phrase in three stages: **rhythm → melody → timbre**. The target is revealed after completion. |
| **Sound Wordle · W03–W06** | Choose **Nature**, **Instruments** or **Noise / electronics** and synthesize rain, bird-like chirps, a plucked note or radio static from witness clues. |
| **Free composition** | Choose this card under **Music Studio**. Write a one-bar melody on a 16-step grid, adjust its sound and effects, and choose a tempo of 60–160 BPM. There is no score. |

The hidden-sound challenges allow unlimited submissions and free hints. In W01/W02, **Hear the concept** plays a teaching example when you need help understanding a sound feature.

Free composition supports one note at a time, within C4–C5. Its draft is saved separately from your W02 challenge, so you can switch between them without replacing either draft.

### New after-hours cases

- **T09 · The Extra Knock** — find it under Timbre Cases, then open the Delay machine. Rebuild several fading echoes from one fixed short knock. Explore the optional cause choices without changing controls, attempts or score. Parameter diagnoses follow the usual 75-point rule. All three Delay controls are open. Submissions have no gameplay limit; the latest 30 records and the independent first-clear answer are kept.
- **W07 · A Doorbell with a Message** — under Sound Wordle → Signals / melody. First build the two-note rhythm, then drag the notes vertically to tune the high, short first sound and lower, longer second sound. Timbre is already set. Passing the rhythm alone does not reveal the target.
- **W08 · The Silent Beat** — in the same category. Recreate three short sounds across four beats, leaving beat 3 quiet. Pitch and timbre stay fixed; adding or extending a note into the required pause prevents completion even when the average timing score is high.

W07/W08 have their own three-tier clues, drafts, histories and target unlocks. Use Hear the concept for a generic example. These original signals do not need song recordings. Free composition remains a separate activity in Music Studio. All three completed cases can be reviewed and collected.

### Build a sound by category

On the wall board, choose **Sound Wordle**, then a sound category. The original W01/W02 challenges remain under **Signals / melody**.

| Case | Sound | Main controls |
| --- | --- | --- |
| **W03 · Nature** | Gentle rain at the window | Drop density, brightness, drop length, continuous rain curtain and intensity movement |
| **W04 · Nature** | Short, rising bird-like whistles | Centre pitch, pitch glide, chirp length, spacing and harmonic colour |
| **W05 · Instruments** | A plucked string-like note | Pitch, decay, brightness, body tone and pick noise |
| **W06 · Noise / electronics** | An untuned radio | Noise bandwidth, pink-noise blend, flutter depth/speed and crackles |
| **W09 · Noise / electronics** | The Wire Ghost: a hollow console-like hum | H1–H5 harmonic faders; fixed pitch, envelope and effects |

**W09** accepts different harmonic balances. Build a sound richer than a pure whistle, with mostly odd upper harmonics and a moderate frequency centre. Beginner opens H2/H3, Standard H2–H5, and Advanced H1–H5. Its score uses three grouped features: odd share of upper-harmonic power, upper-harmonic power and spectral centre. Changing all amplitudes together does not improve it. Silent drafts can be saved, but cannot be played or submitted. Help tier 2 shows your model features; tier 3 adds their accepted bands. These features guide construction; they are not a percentage of perceptual similarity. Completing the case unlocks the target, review and collection.

Accept a case, open the desk's **Synthesizer**, and use **Sound sources** to shape it. Each case starts with a rough sound and five relevant controls. These are stylized synthesized sounds; no bird or rain recording is played underneath.

In W04, drag the two points on the pitch curve up or down to shape the chirp. Drag the right point left or right to shorten or lengthen it. Knobs and number fields update with the curve.

The witness description is available immediately. **More help** gives three free layers: the largest difference, the control and direction to try, then a useful goal range. Help does not reduce progress. Submit whenever you want; edits and auditions do not count as attempts.

Each submission shows **construction progress**, with attribute results below. The score rewards moving toward accepted ranges for the sound's construction controls, rather than comparing audio waveforms. Multiple settings can pass. Reach **90 overall and at least 85 for every attribute** to reveal the reference and unlock A/B playback. This value is not a listening-similarity percentage.

**Analysis / versions** shows the measured spectrum and RMS envelope from your last audition. Open its **Versions** tab to restore one of your last 30 submissions. Gold is your sound; green is the revealed target. Play again after editing to update the plots. Reference settings appear here after completion. Extra Delay and Reverb are unused in these category cases.

**Export my WAV** saves the full 3.6-second stereo passage under **userdata/wordle/exports**. Export uses the same synthesized sound as auditioning and excludes your playback-volume setting. **Reset sound** resets controls while keeping attempts, clues and completion. Undo/redo works for these edits; progress is saved automatically.

### Difficulty, examples and continuous audition

The category cases offer **Beginner (2 controls)**, **Standard (4)** and **Advanced (5)** at the top of the workshop. New players start with Beginner. Other controls are already set for that task. Each difficulty keeps its own draft, attempts and first-clear review. Existing five-control saves continue under Advanced.

**Hear example** plays a neutral teaching sound twice, first with a lower setting and then a higher setting. Only that control changes. It does not reveal the hidden target, change your patch or add an attempt. Text clues also explain what the control does.

Enable **Loop mine · auto update** to repeat your sound. Pause editing briefly to generate and hear the latest version. This is a refreshed preview, rather than instantaneous continuous synthesis. Stop, changing difficulty, leaving the page and focus loss cancel the loop and pending updates. Target and A/B playback remain locked until completion.

### Submission feedback and equipment guidance

After each scored submission, the notebook compares it with your previous submission: for example, **76.0 → 84.0 (+8.0)**, followed by the component that improved most or had the largest setback. The first recorded submission establishes a baseline. Edits, listening and hints do not create submissions. Comparisons stay within the same rules and difficulty. Free composition remains ungraded.

When a diagnosis or requested clue suggests a control, a gold outline marks its knob, fader, number field or piano-roll inspector. The related device also lights up when you return to the desk. These outlines do not change values. Melody hints can select one of your existing notes so you can drag it; they never insert the answer. Timbre-case guidance still requires the diagnosis threshold. Editing clears an outdated timbre diagnosis; hidden-sound guidance updates with your requested clue.

Music-restoration submissions are compared within each device step, separately from the **Check** button. Restarting the investigation or reopening the application establishes a new baseline; earlier per-step comparisons are not reconstructed. The clearing submission's comparison is also shown in its first-clear review during the current run. Existing saved answers and scores remain unchanged.

### Your evidence cabinet

Use **Cabinet** at the top of the room or desk to browse collected synthetic first-clear answers. Replay their sounds, inspect the controls or export the saved answer to WAV. Category difficulties are collected separately; practice edits do not overwrite the first answer. Music recordings are not collected. Existing first-clear reviews with available audio are imported when the game opens.

The **Playtest log** tab under **Analysis / versions** is optional. Enable it to record local anonymous timings, edits, assistance and submissions, including unsuccessful attempts. Export the events as CSV when needed. It records neither names nor microphone audio, and does not upload anything. Each activation creates a new anonymous log.

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

### Close the case and review

Clearing a timbre or Sound Wordle case opens **Case review**. You can replay the starting sound, saved cleared answer and revealed target individually or in order. Tabs show component progress and reference controls. The review explains the biggest improvements and shows recorded submissions, clue tiers and time when available.

The first-clear snapshot is saved independently of later practice. You can reopen it using **Case review** at the top of the room or desk. Reviewing never adds an attempt. A quick edit immediately after submitting keeps you at the desk; the review remains available from the button.

An empty W02 starting melody has no starting audio. Older saves may lack a cleared answer or timing; unavailable information is shown explicitly. Music restoration keeps its full-song playback after completion; open its review manually to compare excerpts. Its graph shows available starting and completed estimates, without inventing intermediate scores.

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

目前遊戲包含 **9 個音色案件、1 個音樂修復案件、9 個隱藏聲音挑戰，以及自由創作**。

### 開始遊戲

如果你拿到的是 **SoundDetective-Public-Setup.exe** 或 **SoundDetective-Setup.exe**，執行它並選擇可寫入的空白資料夾。安裝包已包含遊戲需要的執行軟體，也可建立桌面捷徑；不會覆寫既有遊戲資料夾與存檔。

公開版不需要歌曲錄音即可啟動。缺少或無法使用 M01 的本機素材時，只有該案件暫不可玩；音色案件、聲音重建和自由創作仍可使用。

如果已經有完整遊戲資料夾，直接開啟 **SoundDetective.exe**。

1. 點選「**開始遊戲**」，進入房間。
2. 點擊牆上的「**案件板**」，選擇玩法與案件，再按「**接受案件**」。
3. 點擊「**工作桌或調音台**」，靠近桌上的設備。
4. 點擊一台設備，開啟它的控制介面。

桌子和案件板會有高亮描邊，方便辨認。按「返回桌面」可更換設備，點案件板可切換玩法。第一次遊玩建議從 **T01** 開始。

在「**設定**」中可以調整視窗大小、音量和語言。遊戲預設英文，選擇 **繁體中文** 即可切換介面。使用耳機會更容易聽出細微差異。

### 新手練習

全新玩家第一次按「**開始遊戲**」時，會進入五個獨立練習：試聽、縮短 Release、提高 H2、拖曳鳥鳴音高及長度、提交練習答案。調整後請先試聽自己的修改，再繼續；最後一步需要按「**提交練習**」。

可以隨時「**略過教程**」，之後在主選單的「**新手練習**」重開。已有案件進度的玩家不會被強制帶入教程。練習與正式案件、提示和提交記錄分開，完成後開啟案件板。

### 選擇玩法

| 玩法 | 你的任務 |
| --- | --- |
| **音色還原 · T01–T09** | 聆聽參照單音，調整設備來還原它。各關逐步介紹包絡、諧波、濾波、回聲與混響。 |
| **音樂工作室 · M01** | 分階段修復扭曲的錄音，順序為「**濾波 → 回聲 → 混響 → 音高**」。全部完成後，解鎖完整原曲播放。 |
| **聲音重建 · W01** | 根據證人口供製作隱藏的單音；三個階段都達標後，才可播放目標。 |
| **聲音重建 · W02** | 依序重建隱藏樂句的「**節奏 → 旋律 → 音色**」，完成後揭曉目標。 |
| **聲音重建 · W03–W06** | 選擇「自然聲音」「樂器聲音」或「噪聲與電子」，根據口供合成小雨、鳥鳴般的哨音、撥弦音或收音機雜音。 |
| **自由創作** | 在「音樂工作室」分類選擇此卡片。使用一小節、16 格的卷簾編寫旋律，調整音色與效果，並選擇 60–160 BPM 的速度；不評分。 |

隱藏聲音挑戰不限提交次數，提示免費。W01/W02 中遇到不熟悉的聲音特徵，可以按「**聽聽概念**」聆聽教學示例。

自由創作的音域為 C4–C5，一次演奏一個音。創作草稿與 W02 挑戰分開儲存，切換時會保留各自的內容。

### 新增夜間異常案件

- **T09 · 多出來的一聲**：在音色案件中選擇，再開啟回聲設備。用一次固定短敲擊重建逐漸變弱的重複聲。成因推理可自由選擇，不改參數、不加提交，也不影響分數；參數診斷沿用 75 分開放規則。三個 Delay 控制均開放。沒有遊戲提交次數上限，保留最近 30 次記錄及獨立的首次通關答案。
- **W07 · 會說話的門鈴**：位於 Sound Wordle → 信號與旋律。先建立兩音節奏，再上下拖動音符，完成先高而短、後低而長的門鈴。音色已設定；只通過節奏還不能播放目標。
- **W08 · 空白的一拍**：位於同一分類。四拍內做出三次短聲，第三拍保持安靜。音高與音色固定；若在指定休止區加音或把音延長進去，即使平均時間分數高也不能通關。

W07／W08 各自保存三層提示、草稿、提交歷史與目標解鎖。「聽聽概念」只播放一般示例。這些原創訊號不需要歌曲錄音；自由創作仍在音樂工作室。三個新案件均可復盤並收入收藏。

### 依類別製作聲音

在牆上案件板選擇「**聲音重建**」，再選聲音類別。原有 W01/W02 保留在「**信號與旋律**」。

| 案件 | 聲音 | 主要控制 |
| --- | --- | --- |
| **W03 · 自然聲音** | 窗邊小雨 | 雨點密度、明亮度、雨滴長度、背景雨幕、雨勢變化 |
| **W04 · 自然聲音** | 短促上滑的鳥鳴般哨音 | 中心音高、音高滑動、鳥鳴長度、間隔、諧波色彩 |
| **W05 · 樂器聲音** | 撥弦般的單音 | 音高、衰減、明亮度、琴身厚度、撥弦雜音 |
| **W06 · 噪聲與電子** | 未調準的收音機 | 噪聲頻寬、粉紅噪聲比例、顫動深度／速度、爆裂聲 |
| **W09 · 噪聲與電子** | 電線裡的幽靈：空心的遊戲機嗡聲 | H1–H5 諧波推桿；音高、包絡與效果固定 |

**W09** 接受多組諧波比例。製作比純哨音豐富、以奇數高次諧波為主、頻率重心適中的音色。入門開放 H2／H3，標準開放 H2–H5，進階開放 H1–H5。進度比較三項群組特徵：高次諧波的奇數能量比例、高次諧波能量、頻譜中心；整體調大所有振幅不會提高分數。靜音可作草稿儲存，但不能試聽或提交。二級幫助顯示目前模型特徵，三級加入可接受範圍。這些數值用來指引合成，不是人耳相似度百分比。完成後解鎖目標、復盤與收藏。

接受案件後，點桌上的「**合成器**」，使用「**聲源設備**」製作聲音。每關從一個粗略聲音開始，開放五個相關控制項。這些是具有相應特徵的合成聲音，沒有在底下播放真實鳥叫或雨聲錄音。

W04 的音高曲線可以直接操作：上下拖曳兩個端點改變音高，左右拖動右端點改變鳥鳴長度。旋鈕、數值框與曲線會同步更新。

一開始就能讀取口供。「**再給我一點幫助**」依序提供三層免費提示：主要差異、建議控制項及方向、可接受的目標範圍。提示不扣進度分數。調整和試聽不計次，只有提交才記錄一次嘗試。

每次提交顯示「**合成進度**」及分項結果。分數依合成控制所代表的聲音特徵與可接受範圍計算，允許不同設定通關，沒有直接比較音訊波形。達到**總分 90，各項至少 85**後，解鎖目標試聽與 A/B。此分數不是聽覺相似度百分比。

「**分析與版本**」顯示上次試聽的實測頻譜和 RMS 包絡；切換至「**版本記錄**」頁籤可恢復最近 30 次提交中的控制值。金色是你的聲音，綠色是通關後揭曉的目標；修改後請重新試聽以更新圖表。通關後此處也會顯示參考設定。這四關不使用額外的 Delay 或 Reverb。

「**匯出我的 WAV**」將完整 3.6 秒雙聲道片段存到 **userdata/wordle/exports**，與試聽使用相同合成結果，不套用播放音量。「**重設聲音**」只重設控制，保留提交、提示及通關記錄；可以撤銷／重做修改，進度會自動儲存。

### 難度、示例與循環試聽

分類案件的工作台上方可選 **入門（2 個控制）**、**標準（4 個）**、**進階（5 個）**。新玩家先從入門開始，其餘控制已代為設定。各難度的草稿、提交和首次復盤獨立保存；原有五控制存檔保留在進階。

「**聽控制示例**」用中性教學聲音先播放較低設定，再播放較高設定，只有一項控制不同。不揭露隱藏答案、不改草稿，也不增加提交。文字提示也會解釋控制影響什麼。

啟用「**循環我的聲音 · 自動更新**」後會重複自己的聲音。暫停調參片刻後，程式生成並播放最新版；這是更新預覽，並非瞬間連續合成。停止、切換難度、離開頁面及失焦均會取消循環和待更新請求。目標和 A/B 仍要通關才開放。

### 提交回饋與設備引導

每次提交後，筆記會與上一次提交比較，例如 **76.0 → 84.0（+8.0 分）**，並指出改善最多或退步最大的分項。第一次記錄作為比較起點；調參、試聽、領提示不算提交。只比較相同規則與難度，自由創作仍不評分。

當診斷或已領取的提示建議某個控制時，旋鈕、推桿、數字框或卷簾操作區會出現金色描邊；返回桌面時，相應設備也會亮起。描邊不改參數；旋律提示可以選中玩家已有的音符，方便直接拖動，不會加入答案音符。音色案件仍需達到原本的診斷分數門檻；修改後會清除過期診斷，高亮不會繞過門檻。隱藏聲音的引導則隨已領取的提示更新。

歌曲修復按目前設備步驟比較提交，與「檢查」按鈕分開。重開調查或重新啟動程式後建立新的比較起點，不補造以前未保存的逐步提交資料。當次遊玩中首次通關的復盤也會顯示最後一次提交的變化；既有首次答案和成績保持不變。

### 聲音證物收藏櫃

點房間或工作桌頂部的「**收藏櫃**」，即可瀏覽首次通關的合成作品，試聽、查看設定或匯出 WAV。分類案件各難度分開收藏，後續練習不覆蓋首次作品。音樂錄音不收入收藏。原有首次復盤若保留了答案音訊設定，開啟遊戲時會匯入。

「分析與版本」中的「**試玩記錄**」可自行啟用本機匿名操作、時間、提示、示例和所有提交記錄，未通過的嘗試也保留，並可匯出 CSV。不記錄姓名或麥克風聲音，也不會上傳。每次啟用會建立新的匿名記錄。

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

### 結案復盤

音色案件或聲音重建通關後，會開啟「**結案復盤**」。可分別或依序試聽起點、已保存的通關答案與揭曉的目標；頁籤包含分項進度和參考設定，也會解釋主要改進，顯示已記錄的提交、提示層級及可用的用時。

首次結案快照與之後的練習分開保存。在房間或桌面上方按「**結案復盤**」即可重開，不會增加提交。提交後若立即繼續修改，會留在設備頁；之後仍可主動開啟復盤。

W02 的空白起始旋律沒有起點音訊；舊存檔可能缺少歷史答案或用時，會明確顯示無法提供。音樂修復成功後仍會播放完整原曲，復盤由你主動打開，並比較音樂片段。音樂圖表只呈現可取得的起點與結案估計，不補造中途分數。

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
