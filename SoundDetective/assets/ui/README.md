# 遊戲場景素材

- `office-depth-v1.png`：偵探房間；`desk-closeup-v1.png`：設備桌近景。
- `music-studio-room-v1.png`：音樂錄音室；`music-studio-console-v1.png`：調音台近景。

四張圖皆由內建 image_gen 透過 imagegen skill 生成，原檔保留在此供遊戲使用。偵探房間參考使用者提供的透視室內圖片；音樂工作室的桌面圖參照新房間生成。

完整提示保留於 `office-room-prompt.txt`、`office-desk-prompt.txt` 及 [music-studio-prompts.json](music-studio-prompts.json)。後者包含圖像尺寸、SHA-256 與生成記錄。圖像沒有因本次清理改動。

Qt 另外繪製文字、描邊及互動控件，畫中的電表和波形是美術。音色案件及 W01/W02 挑戰使用偵探房間；M01 與自由創作使用錄音室。語言共用同一套圖片。

[遊戲操作](../../README.md) · [AI 使用記錄](../../docs/AI_ASSISTANCE.md)
