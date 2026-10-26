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
