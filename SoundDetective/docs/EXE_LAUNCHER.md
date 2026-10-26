# Windows EXE 入口

雙擊根目錄 `SoundDetective.exe` 進主選單，沒有命令列視窗。原生 .NET GUI 啟動器優先使用旁邊的 `runtime/pythonw.exe`；開發目錄則使用 `.venv/Scripts/pythonw.exe`。請與完整遊戲資料夾保留。

## 離線安裝包

`release/SoundDetective-Setup.exe` 是完整安裝包，附帶 Python 3.11、目前依賴、SuperCollider、遊戲素材和本機音源；不包含玩家存檔、暫存、測試與開發工具。不需要在目標電腦另外安裝 Python 或 SuperCollider。

安裝器以一般使用者權限執行，選擇可寫入的空白資料夾，解壓後逐檔校驗 SHA-256，再執行已安裝遊戲的依賴檢查；可選擇建立桌面捷徑。既有遊戲／存檔不會被覆寫，更新請另選空白資料夾。需要保留進度時，關閉遊戲後自行將舊版 `userdata` 複製至新版。安裝中斷會留下 `.installation-incomplete` 標記，不會顯示安裝成功。

執行環境與引擎保留原有授權及套件 metadata。這是本機功能驗證用安裝包；換電腦仍需實測 Windows 音訊裝置和驅動。沒有自動更新或系統登錄安裝。

重建：

```powershell
./launcher/build.ps1
.venv/Scripts/python.exe -B launcher/package_release.py --sc-dir 'C:/Program Files/SuperCollider-3.14.1'
```

安裝器原始碼為 `launcher/Installer.cs`；封裝清單和雜湊由 `launcher/package_release.py` 產生。安裝後只需完整資料夾，無需開發機器上的路徑。

```powershell
.\SoundDetective.exe --music-studio
```

此參數直接繼續 M01；自由創作位於主遊戲案件板的 Music Studio 分類。啟動器不依賴外部工作目錄，中文及空格路徑可用。

啟動失敗時會彈錯誤訊息，UTF-8 日誌位於 `.runtime/launcher/startup-*.log`。沒有另開一套玩家存檔。

## 重建與檢查

來源為 `launcher/SoundDetectiveLauncher.cs`；在根目錄以 PowerShell 執行 `./launcher/build.ps1`，使用 Windows .NET Framework C# 編譯器重建。沒有 PyInstaller 依賴。

```powershell
.\SoundDetective.exe --check
.\SoundDetective.exe --smoke-test
.\SoundDetective.exe --smoke-test --music-studio
.\SoundDetective.exe --diagnose
.\SoundDetective.exe --diagnostics
```

開發檢查會驗證依賴及素材；smoke test 建立實際 Qt 視窗，使用 offscreen、靜音和暫存進度，自動關閉，不改寫玩家存檔。這些檢查不需要已刪除的 tests 資料夾。

`--diagnose` 將各項成功／失敗及處理方法寫入 `.runtime/diagnostics-latest.json`，失敗回傳非零。`--diagnostics` 開啟可讀、可匯出的診斷視窗。主選單 Settings 也有相同入口；正常啟動檢查到缺少必要檔案或引擎會顯示診斷。缺少音訊輸出屬警告，不會破壞存檔。

[環境](ENVIRONMENT.md) · [主說明](../README.md)
