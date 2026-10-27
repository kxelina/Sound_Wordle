# 目前遊戲架構

此目錄已整理為目前遊戲的執行程式與必要資源；舊設計、開發測試及试听輸出已清理。素材與玩家存檔使用同一套來源，沒有建立另一份遊戲副本。

## 入口與介面

- `SoundDetective.exe` → `launcher.py` → `play.py` → `ui/studio.py`。
- `ui/studio_scenes.py` 管理偵探房間／錄音室的背景及對齊的點擊區。
- `ui/case_board.py` 提供音色案件、Music Studio 和 Sound Wordle。自由創作使用既有 W02 session 內的獨立 free 草稿。
- `ui/device_panel.py` 將現有案件控制器嵌入工作室；`ui/melody.py`、`ui/hidden_sound.py`、`ui/music_case.py` 處理各模式。
- `ui/audio_bench.py` 雖有舊開發名稱，仍是音色案件共用父類，因此保留其程式；獨立測試台入口已移除。

## 音訊

- `audio/sc_client.py` 呼叫系統 `sclang`、`scsynth`；`supercollider/` 三個腳本生成聲音。
- `audio/preview.py` 與 `audio/music_preview.py` 在背景生成、取消及快取；`audio/playback.py` 負責 Qt 播放、停止及音量。
- `audio/music_render.py` 和 `audio/music_source.py` 從舊示例工具整理出遊戲實際需要的渲染與解碼函式；函式行為保持原樣，現在不依賴示例檔案。
- `audio/matching.py`、`clue_features.py` 保留實際聲學分析；`game/progress.py` 提供方向明確的還原進度。

## 關卡與保存

- `content/cases/` 八個音色案件，`content/music_cases/` M01、證物和錄音校音圖。
- `game/hidden_sound.py`、`game/melody.py` 定義 W01／W02 與自由創作；`game/music_cases.py` 管理先效果後音高的修復步驟。
- `game/storage.py` 原子寫入與損壞檔備份；`userdata/` 的現有檔案全部保留。
- `game/edit_history.py` 與 `ui/edit_history.py` 統一管理有界編輯歷史、連續操作合併與嵌入場景快捷鍵；只記錄設定／旋律，不回滾遊戲進度。W02 與 free 分開持有歷史，音樂過關步驟是歷史邊界。
- 音樂試聽選區在 `MusicPreviewRenderer` 背景工作中裁切實際渲染的聆聽音檔；前後版本共用相同選區，排隊完成後 A/B，版本檢查／播放不增加提交。
- `diagnostics.py` 逐項收集雙語診斷；`ui/diagnostics.py` 背景檢查及報告匯出。離線安裝包由 `launcher/package_release.py`、`Installer.cs` 建置，入口兼容開發 `.venv` 與安裝 `runtime`。
- 圖像、聲音及預製證物不能由快取代替；`.runtime/` 可在下次執行時重新產生。

[遊戲說明](../README.md) · [清理紀錄](CLEANUP.md)

## 2026-10-21：分類聲源工作台

- `content/sound_cases/W03–W06.json`：自然（小雨、鳥鳴）、樂器（撥弦）、噪聲（收音機）四個案件；初始值、目標、雙語口供和可接受特徵範圍皆為資料。
- `audio/sound_sources.py`：驗證聲源控制、固定種子事件排程與實測頻譜／包絡。`synth.scd` 增加五個 SC SynthDef：連續雨幕、雨滴／爆裂、音高滑動哨音、Karplus–Strong 撥弦與白／粉紅噪聲混合。
- `SCEngine.render_source` 依 OSC NRT 排程產生 3.6 秒、44.1 kHz 雙聲道 WAV；沿用 ASCII 暫存、取消、音訊驗證與原子匯出。原有音符／旋律／音樂修復仍使用原本的三個定義。
- `audio/source_preview.py` 與原預覽器共用單工作執行緒、版本取消和過期結果丟棄機制。播放與匯出共用相同 SC 波形及近似電平匹配。
- `game/sound_categories.py` 使用公開的控制正規化方法，對可接受範圍外的距離作平方映射；噪聲截止頻率採對數尺度。這是**合成進度**，不宣稱聲學／人耳相似度。圖表則從實際輸出 WAV 測量；隨機聲音不作逐樣本匹配。
- `ui/sound_categories.py`：五個旋鈕／精確輸入、鳥鳴音高與長度拖曳、分項分數、三級免費提示、解鎖參照、實測圖表、版本恢復、WAV 匯出及編輯歷史。新存檔在 `userdata/wordle/W03–W06.json`，不改舊案件格式。
- 分類入口放在既有案件板，原 W01/W02 仍在信號與旋律類。Qt 繪圖沿用既有依賴，沒有新增套件或外部 API。

## 2026-10-26：公開啟動、教程與結案

- `game/availability.py` 將錄音歌曲素材／校音圖的可用性與合成遊戲分開；`diagnostics.py` 的必要內容檢查仍嚴格，M01 缺失或損壞只列警告。`launcher.py` 的原生 EXE 檢查與案件板使用相同結果。
- `ui/tutorial.py` 提供獨立的五步操作教程，沿用實際 SC 合成、旋鈕、推桿及曲線。每次編輯都使舊的「已試聽」狀態失效，實際播放目前修改後才能進入下一步；最後明確提交練習。教程不操作任何正式 Session。
- `game/player_journey.py` 在 `userdata/player-journey.json` 保存教程狀態、操作用時和首次結案快照；格式驗證、原子寫入與損壞備份沿用現有保存機制。舊案件原有 JSON 格式不變。
- `game/debrief.py` 從已完成 Session 建立唯讀快照，保存各種聲源／樂句的實際設定。缺失的歷史音訊或時間使用空值，不補造答案。`ui/debrief.py` 使用獨立的序列播放器及可取消背景渲染，比較起點／答案／目標，顯示分項與控制值。
- `studio.py` 整合首次教程、手動重播、結案頁及設備頁活動計時。快速修改會取消排隊的自動結案跳轉；首次快照仍保存。M01 保持完整原曲播放，復盤手動開啟。離開、失焦、切換語言／設定及退出會停止相關預覽。
- `launcher/package_release.py` 的 `--public` 排除錄音和 M01 證物；`--base-installer` 重用已驗證的執行環境而更新遊戲程式。

## 分類學習工具與聲音收藏

- `game/source_learning.py` 從同一關卡建立 2／4／5 個開放控制的變體，其餘控制固定在答案。進階仍使用原存檔路徑；其他難度及各自首次復盤存於 `userdata/wordle/levels/`。schema-1 來源存檔升級前保留逐位元備份。
- 評分只計開放控制，禁止改動鎖定控制；音高曲線也遵守同一限制。原有目標範圍與評分尺度不變。可接受解、逐項改善和提示方向由受控測試審查，尚無人耳感知校準結果。
- 教學對比聲音使用獨立固定種子和中性參數，僅一個控制低／高不同，完全不讀目標參數。範例沿用 SC 預覽器、取消機制及音量匹配，不增加提交。
- 循環更新採 400 ms 停止調參後合成，僅保留最新請求。更新時停止舊片段，再播放新片段；不是實時 OSC 合成或無縫串流。離開／失焦／切換難度／停止均取消計時器、渲染與循環。
- `game/evidence.py` 只保存通關合成聲音的已驗證設定快照，不保存任意檔案路徑或原曲。`ui/evidence.py` 重用唯讀復盤管線重新合成、播放和匯出；以案件與難度識別首次作品。
- `game/playtest.py` 及分析頁的記錄分頁提供預設關閉的本機匿名 JSONL／CSV。記錄不代替受控實驗；未通過的提交保留，無姓名、麥克風輸入或網路傳輸。

## 2026-10-27：夜間異常首批案件

- `game/catalog.py` 集中註冊 T01–T09、W01–W08 與 M01，供載入、偏好和復盤驗證共用。啟動診斷亦驗證兩個新增旋律 JSON。
- T09 使用一次 MIDI 45 短音及現有 Delay；成因問題來自案件資料，不參與計分。它使用 schema-4 的最近 30 次記錄、連續提交計數與獨立首次答案，避免存滿歷史後停止遊戲。重開／練習仍保留首次答案；舊 T01–T08 schema-3 行為保持。
- `content/melody_cases/W07.json` 與 `W08.json` 提供原創門鈴／休止節奏、固定音色、階段、雙語口供、四級文本（初始及三級提示）和結案語。前者為節奏→音高，後者只考節奏。
- `MelodySession` 及評分接收案件，W02 預設與序列化欄位保持相容。新增案件的存檔驗證 ID 與資料指紋，不能互換或用 W02 的隱藏答案通關。非使用者任務的分項不計入總分、不顯示假進度。
- W08 的休止格 8–11 是獨立結構約束，不能靠其餘音符的高平均分掩蓋。所有聲音仍由相同 SC 管線生成；沒有新增錄音、模型或依賴。
- 新旋律關鎖住音色、隱藏自由創作入口，僅 W02 保留其獨立自由草稿。復盤／收藏展示新案件的音符起點、時長與必要音高，而非大量鎖住的音色參數。
- 新長口供置於可捲動筆記中，播放與停止固定可見。短音域樂句在空間足夠時自動保持全部音符可見，跨度過大時仍以目前選取音符為中心。


## 2026-10-27：W09 群組諧波規則

- `content/sound_cases/W09.json` 與 `game/harmonic_rules.py`：五個諧波、三項能量／頻譜群組特徵，多解範圍計分；採正規化振幅平方的解析特徵，不是人耳相似度。分數對極大外部距離先截斷再平方，避免誤差增加後分數反升。
- `audio/sound_sources.py` 的 harmonic 配方重用既有 `soundDetective` SynthDef，音高、包絡和效果固定，沒有新 DSP 或依賴。`ui/sound_categories.py` 為它顯示垂直推桿和群組特徵讀值。
- `SourceCase.scoring` 預設 control_bands，舊案例維持原保存版本及計分。W09 使用 harmonic-groups-v1，另保存案件指紋以隔離規則與難度。靜音草稿合法，提交／試聽會攔截。
- 共同案件目錄包含 W09；分類入口、控制鎖定、難度、復盤、收藏、連續試聽及匯出沿用共用流程。


## 2026-10-27：提交回饋與提示描邊

`game/submission_feedback.py` 只讀取相鄰提交的分數快照，不接觸目標參數；跨規則／非連續版本不比較，音色診斷門檻以下只顯示總分差。`ui/investigation_feedback.py` 提供小字摘要和不接收滑鼠的金色覆蓋層，供各計分模式共用；場景設備以獨立 guided 狀態保留引導，不與 hover 混用。

音色及 Wordle 的差值由驗證過的保留記錄重算，不改保存格式。M01 只保留本次視窗內的同階段提交快照，與檢查按鈕獨立；重啟建立新起點，不補造歷史。當次首次結案摘要由獨立 payload 傳至復盤，後續練習不覆蓋；舊存檔缺少該摘要時不補造。

提示描邊遵守開放控制與分數／提示門檻。異步音訊比較恢復控制後才更新描邊，修改後清除過期診斷。卷簾提示只選取既有玩家音符；長單行說明不參與水平最小尺寸，避免把數字框及新增／刪除推到畫面外。
