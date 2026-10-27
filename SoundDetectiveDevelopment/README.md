# Sound Detective 開發驗證

這裡保留目前新增功能的維護測試；不屬於玩家遊戲目錄，也不會被打進安裝包。

- `test_features.py`：編輯歷史、全部音色關、W01／W02／自由創作、音樂版本對比、選區 WAV、診斷及場景生命週期。
- `test_note_dragging.py`：上下拖音高、左右把手拉長／縮短、重疊與邊界、取消手勢、階段鎖定及撤銷／試聽資料整合。
- `test_sound_categories.py`：分類篩選、四種程序聲源、可接受答案／方向提示、損壞進度恢復、實際 SC 決定性渲染、舊音色回歸、背景快取／取消／匯出／A/B 與鳥鳴拖曳。
- `test_player_journey.py`：公開版可選歌曲素材、教程操作門檻與隔離、首次復盤快照、舊歷史缺失處理、快速修改不彈窗、雙語布局與音樂通關繼續完整原曲。音樂專項在沒有 M01 錄音時跳過。
- `.runtime/`：本機測試報告、暫存安裝、擷取圖片與隔離進度。正式遊戲進度仍在 `../SoundDetective/userdata/`。
- `VALIDATION.md`：本次驗證結果及未驗證範圍。
- `test_learning_tools.py`：難度隔離、舊檔升級、鎖定曲線、循環更新／取消、教學聲音、收藏重播／匯出，以及匿名试玩記錄。
- `PLAYTEST_GUIDE.md`：可由同學實際執行的觀察流程與結果記錄要求；不是已完成的研究結果。
- `test_after_hours.py`：T09／W07／W08 的註冊、雙語、階段隔離、指定休止、實際音訊、千次以上提交／存檔與復盤收藏。
- `validate_after_hours_ui.py`：以場景指標操作音符長度／音高、移除多餘音符，使用真實引擎、靜音完成三關及收藏匯出。

從此資料夾執行：

```powershell
New-Item -ItemType Directory -Path .runtime -Force | Out-Null
$testRun = Join-Path (Get-Location) ('.runtime/test-' + [guid]::NewGuid().ToString('N'))
../SoundDetective/.venv/Scripts/python.exe -B -m pytest test_features.py -q -p no:cacheprovider --basetemp $testRun
```

測試使用獨立進度，Qt 介面檢查採 offscreen，關閉 UI 點擊音；不會播放到使用者喇叭。

- `test_wire_ghost.py`：W09 群組特徵、多解、音量縮放、方向提示、靜音、存檔指紋、難度、推桿、收藏，以及實際頻譜核對。既有逐控制測試只參數化舊規則，W09 以獨立群組規則檢查；共用流程仍包含 W09。
- `validate_wire_ghost_ui.py`：實際場景座標拖推桿，真實引擎、靜音完成示例／試聽／A/B、雙語、通關與收藏 WAV 匯出；可用 SOUND_DETECTIVE_QA_GAME 指定安裝目錄。

- `test_submission_guidance.py`：相鄰提交、診斷門檻、規則隔離、透明高亮、異步鎖定、旋律選取、雙語布局、首次結案與歌曲步驟比較。
- `validate_submission_guidance_ui.py`：真實音訊、場景旋鈕／音符指標拖動、分數差、雙語描邊、固定試聽機與當次首次復盤。

- `test_knock_volume.py`：T09 專用播放電平、所有試聽入口、復盤／收藏導出、背景快取隔離、峰值上限及實際音訊／評分不變。
