# Sound Detective Player Guide

[English](#english) · [繁體中文](#繁體中文)

## English

Sound Detective is a sound-making game. Listen to a sound, change the controls, and
try to recreate it.

The game focuses on two activities:

- **Timbre Cases (T01–T09):** recreate a sound by adjusting the synthesizer.
- **Sound Wordle (W01–W09):** use clues to build a hidden sound and improve your answer.

### Start a case

1. Select **Start Game**.
2. Click the board on the wall.
3. Choose **Timbre Cases** or **Sound Wordle**, select a case, and click **Accept case**.
4. Click the desk, then open the **Synthesizer**.
5. Listen to the reference, adjust controls, and preview your sound.
6. Click **Submit** to get feedback.

New players can choose **Learn to play** for a short tutorial. You can reopen it from
the main menu.

### Sound Wordle cases

| Case | Sound to recreate |
| --- | --- |
| W01 | A signal tone |
| W02 | A short melody |
| W03 | Rain |
| W04 | A bird-like whistle |
| W05 | A plucked string sound |
| W06 | Radio static |
| W07 | A two-note doorbell |
| W08 | Three sounds with one silent beat |
| W09 | A hollow electronic tone |

Read the witness clues, make a guess, and submit it. **Help / guidance** gives a free
hint about what to try next. Hints do not change your answer.

After you submit, colors show how each part of your answer compares:

- **Green:** correct or within the target range.
- **Amber:** close; adjust it a little.
- **Gray:** needs more work.

For **W02**, note colors apply to the rhythm and melody stages, not the timbre stage.
W07 gives note feedback for rhythm and pitch; W08 gives note feedback for rhythm.
Other Wordle cases show colored feature tiles.

Feedback describes your **last submitted answer**. Editing does not update the colors;
submit again to see new feedback. Notes added after a submission have no color until
you submit them.

### Timbre cases

Listen to the reference, then adjust the controls shown for that case. The controls
may include harmonics, the sound's volume shape (ADSR), filters, echoes (Delay), or
room effects (Reverb). Preview often and submit when you are ready.

### How scores work

- **Timbre Cases:** compare your sound's frequency balance and volume shape; the
  displayed score combines those measurements.
- **Sound Wordle:** scores how closely your settings or notes match the target.
  Each case checks its own sound features or notes.

In both, **100 means a close match to what that case measures**.

### Useful controls

- **Undo / Redo:** reverse or restore an edit.
- **Restart case:** start the case again.
- **Stop:** stop audio; **Esc** also works.
- Hover over a control to read what it does.

Your progress and drafts are saved automatically in the `userdata` folder. Keep that
folder if you want to keep your progress.

### If something goes wrong

- If you hear no sound, check the game and computer volume, then try **Stop** and play
  again.
- If a control is locked, check the current clue or stage.
- If the score or colors have not changed after editing, submit again.
- For more help, open **Settings → Startup diagnostics**.

For installation and test instructions, see the [project README](../../README.md).

## 繁體中文

Sound Detective 是一款聲音合成遊戲。聆聽聲音、調整控制項，再試著重現它。

遊戲主要有兩種玩法：

- **音色案件（T01–T09）：**調整合成器，重現指定的聲音。
- **Sound Wordle（W01–W09）：**根據線索製作隱藏聲音，再逐步改進答案。

### 開始案件

1. 選擇「**開始遊戲**」。
2. 點擊牆上的案件板。
3. 選擇「**音色案件**」或「**Sound Wordle**」，挑選案件後按「**接受案件**」。
4. 點擊工作桌，再開啟「**合成器**」。
5. 聆聽參照聲音、調整控制項，並試聽自己的聲音。
6. 按「**提交**」查看回饋。

新玩家可以從主選單選擇「**新手練習**」開始短版教程。

### Sound Wordle 案件

| 案件 | 要重現的聲音 |
| --- | --- |
| W01 | 訊號音 |
| W02 | 短旋律 |
| W03 | 下雨聲 |
| W04 | 鳥鳴般的哨音 |
| W05 | 撥弦聲 |
| W06 | 收音機雜音 |
| W07 | 兩個音的門鈴 |
| W08 | 三個聲音，中間有一拍安靜 |
| W09 | 空心的電子音 |

閱讀證人口供，製作答案並提交。「**幫助／設備引導**」會提供免費提示，告訴你
可以嘗試什麼。提示不會改變你的答案。

提交後，顏色會顯示答案各部分的狀態：

- **綠色：**正確或符合目標範圍。
- **琥珀色：**接近目標，可以微調。
- **灰色：**還需要調整。

**W02** 只在節奏與旋律階段顯示音符顏色，音色階段不顯示。W07 在節奏與音高階段
顯示音符回饋；W08 只在節奏階段顯示。其他 Wordle 案件顯示特徵色塊。

顏色代表「**上次提交的答案**」。編輯時顏色不會更新；再次提交才會看到新回饋。
提交後新增的音符，在提交前不會有顏色。

### 音色案件

先聆聽參照聲音，再調整案件提供的控制項。控制項可能包括諧波、音量變化
（ADSR）、濾波、回聲（Delay）或空間效果（Reverb）。多試聽，準備好後再提交。

### 分數如何計算

- **音色案件：**比較聲音的頻率分布與音量變化，顯示的分數會綜合這些測量結果。
- **Sound Wordle：**計算你的設定或音符與目標的接近程度；每個案件檢查不同的聲音特徵或音符。

兩種玩法中，**100 分代表符合該案件所測量的內容**。

### 常用控制項

- **復原／重做：**取消或恢復一次編輯。
- **重新挑戰：**重新開始案件。
- **停止：**停止聲音；也可以按 **Esc**。
- 將滑鼠停在控制項上，可以查看用途說明。

進度與草稿會自動儲存在 `userdata` 資料夾。若要保留進度，請保留這個資料夾。

### 遇到問題

- 沒有聲音時，檢查遊戲與電腦音量，再按「停止」並重新播放。
- 控制項被鎖定時，查看目前的線索或階段。
- 編輯後分數或顏色沒有更新時，請再次提交。
- 需要更多協助時，開啟「**設定 → 啟動診斷**」。

安裝與測試說明請見[專案 README](../../README.md)。
