# 執行環境

目前使用本專案 `.python/` 的 CPython 3.11.15、`.venv/`、PySide6 6.8.3，以及系統安裝的 SuperCollider 3.14.1。沒有依賴舊 SoundAlchemy 專案。

完整離線安裝包會將 Python／依賴放在 `runtime/`，SuperCollider 放在 `engine/SuperCollider/`；引擎查找優先使用指定路徑及遊戲附帶版本，不依賴開發機器的系統安裝。[安裝與建置](EXE_LAUNCHER.md)。

一般使用直接雙擊 `SoundDetective.exe`。需要終端時：

```powershell
.venv/Scripts/python.exe -m sound_detective.play
.venv/Scripts/python.exe -m sound_detective.play --music-studio
```

音樂工作室裡可選 M01 或自由創作；預設主入口保留主選單。單獨的 `sound_detective.wordle`、`sound_detective.melody`、`sound_detective.music_case` 設備視窗仍保留。

若無法找到音頻引擎，設定 `SOUND_DETECTIVE_SC_DIR` 為含 `sclang.exe`、`scsynth.exe` 的 SuperCollider 安裝資料夾。不需要手動啟動 SC。

## 重建 Python 環境

`requirements.txt` 統一引用 `requirements-lock.txt`，後者是既有、已驗證環境的完整鎖定版本。清理沒有改動安裝的套件或移除執行環境。

搬動專案後建議重建 `.venv`；在新 Windows 機器上安裝 Python 3.11 和 SuperCollider，再執行：

```powershell
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

安裝需可取得對應套件；目前這台電腦的環境已完整保留，不需要重裝。`.python/` 和 `.venv/` 都不能當成測試垃圾刪除。

[EXE 啟動器](EXE_LAUNCHER.md) · [遊戲操作](../README.md)
