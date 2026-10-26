"""Shared bilingual, answer-free explanations for every interactive surface.

Bindings use semantic roles, never translated button captions or target data.
Native Qt tooltips work in standalone windows and the studio graphics proxy.
"""

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QGraphicsProxyWidget, QToolTip, QWidget


HELP = {
    "source_category": ("Filter the Sound Wordle case list by sound family. Accept a case to start; browsing keeps your progress.", "依聲音類別篩選 Sound Wordle 案件；接受案件後才開始，瀏覽不會清除進度。"),
    "source_workshop": ("Open this case's sound generators and shaping controls. Each case exposes only the controls it needs.", "開啟此案件的聲源與塑形控制，只顯示這個聲音需要的控制項。"),
    "source_analysis": ("Inspect the last audition's measured spectrum, amplitude envelope and submitted versions.", "查看上次試聽的實測頻譜、振幅包絡與提交版本。"),
    "source_submit": ("Record one attempt and show construction progress. Pass at 90 overall with every attribute at least 85; submissions are unlimited.", "記錄一次提交並顯示合成進度；總分 90、各項至少 85 即通關，提交不限次。"),
    "source_reset": ("Return the sound controls to their starting values. Attempts, clues and completed progress are kept; this edit can be undone.", "把聲音控制恢復初始值，保留提交、提示與通關記錄；可以復原此修改。"),
    "source_export": ("Export your current synthesized sound as a stereo WAV, including its full short passage. Playback volume is excluded.", "把目前合成的完整短片段匯出為雙聲道 WAV，不套用播放音量。"),
    "source_restore": ("Restore the selected submission's sound controls without undoing attempts, clues or completion.", "恢復選中提交的聲音控制，保留提交次數、提示與通關記錄。"),
    "source_graphs": ("These are measurements of generated audio. Gold shows your sound; green shows the target only after it is revealed.", "圖表來自實際合成音訊。金色為你的聲音，綠色為通關後揭曉的目標。"),
    "source_history": ("Select a submitted version, then Restore selected version to continue from its controls.", "選中提交記錄，再按「恢復選中版本」從當時的控制值繼續調整。"),
    "start": ("Enter your current workspace; use the wall board to choose a case and the desk to open equipment.", "進入目前案件的工作室；在牆上案件板選案，再點工作桌使用設備。"),
    "settings": ("Adjust window size, playback volume and interface language. Sound settings and scores are unaffected.", "調整視窗大小、播放音量及介面語言；不會改變音色設定或分數。"),
    "exit": ("Close the game, stop audio and save current progress.", "關閉遊戲、停止聲音並儲存目前進度。"),
    "back_settings": ("Return to the previous screen; changes to settings are already applied.", "返回上一個畫面；設定變更已即時套用。"),
    "back_room": ("Return to the office; your current case and settings are kept.", "返回偵探工作室，保留目前案件與設定。"),
    "back_desk": ("Return to the desk to choose another piece of equipment; current settings are kept.", "返回工作桌，選擇其他設備；保留目前設定。"),
    "back_menu": ("Return to the main menu and stop playback; current progress is kept.", "返回主選單並停止播放；保留目前進度。"),
    "size": ("Change the game window size while preserving the desktop layout. This does not affect sound quality or scores.", "變更遊戲視窗大小並保留橫版比例；不影響音質或分數。"),
    "language": ("Switch the interface and hover explanations between English and Traditional Chinese.", "切換英文／繁體中文介面，懸停說明也會一起切換。"),
    "volume": ("Change playback loudness only; your synthesizer settings and reconstruction scores stay the same.", "只改變播放音量，不影響合成器設定或還原分數。"),
    "board": ("Open the case board to choose a mode and case. Browsing does not switch your active case until you accept.", "開啟案件板，選擇模式與案件；按接受案件後才會正式切換。"),
    "desk": ("Zoom in on the workbench, then click a machine to use its controls.", "放大工作桌，再點擊設備進入其控制頁面。"),
    "music_board": ("Open the studio session board to choose a restoration case or switch game mode; only accepting a case changes your workspace.", "開啟錄音室案件板，選擇音樂修復案件或切換模式；接受案件後才會切換工作室。"),
    "music_desk": ("Move closer to the mixing console, recorder and effects rack, then click a device to restore the music.", "靠近調音台、磁帶機與效果機架，再點擊設備修復音樂。"),
    "composition_board": ("Choose free composition, a restoration case or another game mode; your draft is kept when you switch.", "選擇自由創作、音樂修復或其他玩法；切換時保留創作草稿。"),
    "composition_desk": ("Move closer to the console to write notes, shape your synthesizer and add Delay or Reverb.", "靠近調音台編寫音符、調整合成器，並添加 Delay 或 Reverb。"),
    "back_composition_room": ("Return to the music studio; your free-composition draft and sound settings are kept.", "返回音樂工作室，保留自由創作草稿與音色設定。"),
    "free_card": ("Select ungraded free composition in the music studio. Accept to open your independent melody and sound draft.", "選擇音樂工作室中的自由創作；接受後開啟獨立旋律與音色草稿，不評分。"),
    "back_music_room": ("Return to the music restoration studio; current repairs and case progress are kept.", "返回音樂修復工作室，保留目前修復設定與案件進度。"),
    "device_tape": ("Open the audition deck to listen to the available evidence or your current sound.", "開啟試聽機，聆聽目前可用的證物或自己的聲音。"),
    "device_synth": ("Open harmonic, ADSR and available filter controls to change tone colour and its shape over time.", "開啟諧波、ADSR 及已開放的濾波控制，調整音色與聲音隨時間的變化。"),
    "device_melody": ("Open the piano roll to write notes, or the synthesizer to change the sound playing them.", "開啟鋼琴卷簾編寫音符，或用合成器調整演奏這些音符的聲音。"),
    "device_music": ("Open pitch correction and frequency recovery; estimate the filter damage to restore missing frequency content.", "開啟音高校正與頻段修復；估計濾波損傷，恢復缺失的頻段。"),
    "device_music_delay": ("Open the echo canceller and estimate the original echo spacing, decay and amount; switching it off leaves the echoes intact.", "開啟回聲抵消器，估計原本的回聲間隔、衰減與比例；關閉工具會保留回聲。"),
    "device_music_reverb": ("Open room recovery and estimate the original room size, damping and reverberation amount to reduce the damage.", "開啟空間修復器，估計原本的空間、阻尼與混響比例，逐步減少損傷。"),
    "device_delay": ("Open Delay to add repeated echoes and adjust their spacing, decay and level.", "開啟 Delay，調整重複回聲的間隔、衰減及音量。"),
    "device_reverb": ("Open Reverb to add a sense of space and adjust the reverberant tail.", "開啟 Reverb，加入空間感並調整混響尾音。"),
    "device_filter": ("Open Filter to remove frequency regions or emphasise the cutoff area.", "開啟 Filter，削弱特定頻段，或突出截止頻率附近的聲音。"),
    "device_analyzer": ("Open analysis and submission history available for this case; locked clues remain locked.", "查看本案可用的分析與提交記錄；尚未開放的線索仍保持鎖定。"),
    "device_music_notes": ("Review your current restoration step, cleared devices and the next tuning direction; future devices stay locked.", "查看目前修復步驟、已完成設備與調整方向；後續設備仍保持鎖定。"),
    "mode_tone": ("Listen to a reference tone and reconstruct it with the controls available in each timbre case.", "聆聽參照單音，使用各音色案件開放的控制項還原聲音。"),
    "mode_music": ("Choose a music-restoration case or ungraded free composition in the music studio.", "在音樂工作室中選擇音樂修復案件，或進行不評分的自由創作。"),
    "mode_wordle": ("Build a hidden sound or melody from clues; submissions are unlimited and help is free.", "根據線索製作隱藏聲音或旋律；提交不限次，提示免費。"),
    "case_card": ("Select this case for inspection. Press Accept case to start or resume it.", "選中這個案件；按接受案件後開始或繼續調查。"),
    "accept": ("Start or resume the selected case, then return to the office to use the workbench.", "開始或繼續所選案件，然後回到工作室使用桌上設備。"),
    "play_target": ("Play the reference sound for listening; this does not submit your answer.", "播放參照聲音供聆聽，不會提交答案或增加次數。"),
    "play_current": ("Play your latest settings so you can hear their effect; playback does not count as a submission.", "播放目前設定的聲音，聽出調整效果；試聽不算提交。"),
    "play_ab": ("Play the reference followed by your current sound to hear their differences; this does not submit an answer.", "依序播放參照與目前答案，方便聽出差異；不會提交答案。"),
    "stop": ("Stop playback and cancel pending audio preparation; your notes and settings are kept.", "停止播放並取消待處理的音訊生成，保留音符與設定。"),
    "submit_tone": ("Record reconstruction progress for this version and add one attempt. A qualifying score unlocks this submission's diagnosis.", "記錄目前版本的還原進度並增加一次提交；達到門檻後開放本次診斷。"),
    "submit_bench": ("Compare the rendered sounds' spectrum, envelope and tail, then show audio-match results and diagnosis.", "比較實際生成聲音的頻譜、包絡與尾音，顯示音訊匹配結果和診斷。"),
    "restart_tone": ("Return this case to its starting settings for another attempt; the first clear remains recorded.", "將本案恢復起始設定，重新嘗試；首次通關記錄仍會保留。"),
    "review": ("After clearing the case, compare the target controls with your submitted answer.", "通關後對照目標控制項與本次提交的答案，查看差異。"),
    "close_review": ("Close this review and return to the case without changing your sound.", "關閉復盤並返回案件，不會修改聲音設定。"),
    "next_case": ("After solving this case, open the next timbre case; saved progress is kept.", "完成本案後進入下一個音色案件，保留已儲存進度。"),
    "case_selector": ("Switch to another timbre case and restore its saved settings and progress.", "切換音色案件，恢復該案件已儲存的設定與進度。"),
    "open_music": ("Open staged music restoration: effects first, then pitch, with a full-song reward after completion.", "開啟分階段音樂修復：先效果、後音高，完成後播放整首原曲。"),
    "evidence": ("Listen to the distorted music evidence; your repair controls do not change this evidence copy.", "播放被扭曲的音樂證物；修復控制不會修改這份證物。"),
    "music_current": ("Preview the damage remaining after your current repair calibration; disabled repair devices leave their damage intact.", "試聽依目前校準設定修復後仍留下的失真；關閉修復設備會保留該類損傷。"),
    "check_repair": ("Check the current step's score and tuning direction without using a submission; checks do not unlock stages.", "查看目前步驟的分數與調整方向，不增加提交次數；檢查本身不會解鎖下一步。"),
    "submit_music_stage": ("Submit this restoration step; a passing result locks its repair and opens the next device. Completing all steps plays the original song.", "提交目前修復步驟；達標後保持已完成修復並開放下一台設備，全部完成後播放原曲。"),
    "music_goto": ("Open the device for the current step; later devices remain unavailable until the preceding step passes.", "前往目前步驟的設備；前一步提交達標後，才會開放後續設備。"),
    "music_region": ("Choose a marked pitch region to edit one note at a time; this selection does not change your corrections.", "選擇標記的音高片段，一次調整一段；切換片段不會改動音高校正值。"),
    "music_region_previous": ("Move to the previous pitch region, keeping all your corrections.", "移到上一個音高片段，保留已調整的校正值。"),
    "music_region_next": ("Move to the next pitch region, keeping all your corrections.", "移到下一個音高片段，保留已調整的校正值。"),
    "music_monitor": ("Hear only the selected region with its current pitch correction; effects are isolated in this monitor and remain in the full evidence.", "只試聽所選片段及目前音高校正；監聽會隔離效果，完整證物仍保留效果損傷。"),
    "music_pitch_roll": ("Drag a green note vertically to change pitch; Shift-drag tunes finely and double-click auditions it. Timing is fixed; grey notes are context.", "上下拖曳綠色音塊改變音高；Shift 拖曳可細調，雙擊試聽。時間與長度固定；灰色音塊是上下文參照。"),
    "music_pitch_fine": ("Fine-tune the selected recording region in semitones; 0 returns to its distorted starting pitch, and +1 raises it by 100 cents.", "以半音精調所選錄音片段；0 是原本的偏音設定，+1 提高 100 cents。"),
    "music_pitch_estimate": ("Shows the selected region's current estimated dominant pitch. Mixed audio can contain several notes; this is not a verified full score or an isolated instrument.", "顯示所選片段目前的估計主音高；混音可能同時含多個音，這不是已核對的完整樂譜或獨立樂器。"),
    "music_pitch_reset": ("Return only the selected note to its distorted starting pitch; other corrections are kept.", "只將所選音塊恢復至原本偏音，保留其他音塊的調整。"),
    "music_pitch_zoom_in": ("Enlarge the piano roll to separate nearby note blocks and read pitch labels; scroll to other times or pitches.", "放大卷簾，方便區分鄰近音塊及閱讀音名；可捲動查看其他時間或音高。"),
    "music_pitch_zoom_out": ("Zoom out to see more of the recording without changing any notes.", "縮小卷簾以查看較多錄音內容，不會修改音符。"),
    "music_pitch_fit": ("Fit the whole marked phrase into the piano-roll view; pitch corrections stay unchanged.", "在卷簾中全覽標記樂句，保留所有音高校正。"),
    "repair_tab": ("Estimate how the evidence was damaged; closer calibration removes more damage on the next preview.", "估計證物受到的損傷設定；校準越接近，下次試聽時移除的損傷越多。"),
    "reveal_song": ("After solving the case, replay the full song on repeat; Stop or Escape ends playback.", "完成案件後再次循環播放完整歌曲；按停止或 Escape 可結束播放。"),
    "restart_music": ("Reset the current investigation and repair controls, and stop the song reveal; the first-clear record is retained.", "重設本輪調查與修復控制，並停止歌曲揭曉播放；保留首次通關記錄。"),
    "pitch_correction": ("Shift only this recorded region's pitch; +1 semitone raises it by 100 cents while timing stays fixed.", "只改變這個錄音片段的音高；+1 半音提高 100 cents，時間位置不變。"),
    "hidden_target": ("Play the hidden reference after the challenge has been solved; it is unavailable before success.", "完成挑戰後播放隱藏參照；通關前不可播放。"),
    "hidden_ab": ("After success, play the revealed target and your answer in sequence to compare them.", "通關後依序播放已揭曉的目標與自己的答案，對照聲音差異。"),
    "submit_hidden": ("Record this version's requirement progress and unlock the next stage when it passes; attempts are unlimited.", "記錄目前版本的要求達成進度，達標後開放下一階段；提交不限次。"),
    "submit_melody": ("Record rhythm, melody and timbre progress; all three must pass to reveal the target. Free composition is not graded.", "記錄節奏、旋律與音色進度；三部分均達標才揭曉目標，自由創作不評分。"),
    "hint": ("Request the next layer of help for the current difficulty; it does not add an attempt or reduce your score.", "領取針對目前困難的下一層提示，不會增加提交次數或降低分數。"),
    "lesson": ("Hear a generic teaching comparison illustrating the current concept; it is not the hidden target.", "聆聽一般教學對比，了解目前的聲音概念；範例不是隱藏目標。"),
    "suggested": ("Open the device associated with the current main difficulty; your settings are kept.", "前往目前主要問題對應的設備，保留目前設定。"),
    "history": ("View recent submitted versions and their scores; editing alone does not create a submission.", "查看最近提交的版本及分數；單純調整設定不會新增提交。"),
    "restore": ("Restore the selected submission's settings for further editing; this does not add an attempt.", "恢復所選提交版本的設定，繼續修改；不增加提交次數。"),
    "hear_history": ("Play the selected submitted version without replacing your current draft.", "試聽所選的歷史提交版本，不會覆蓋目前草稿。"),
    "restart_hidden": ("Reset the current attempt, hints and history; an already revealed target stays revealed.", "重設本輪嘗試、提示與記錄；已揭曉的目標仍保持揭曉。"),
    "reset_draft": ("Clear the active draft and reset its controls; the other mode's draft is kept. Previously revealed targets stay revealed.", "清空目前模式的草稿並重設控制，另一模式的草稿保留；已揭曉目標仍保持揭曉。"),
    "challenge": ("Return to W02's saved challenge draft and stage rules; your free composition is kept separately.", "返回 W02 已儲存的挑戰草稿及階段規則；自由創作另外保留。"),
    "free": ("Open your independent free draft with all notes, sound controls and tempo available; no scores or attempts are recorded.", "開啟獨立自由草稿，所有音符、音色及速度控制立即可用；不評分、不計次。"),
    "tempo": ("Set beats per minute to speed up or slow down the whole melody; note pitches stay the same. Editable in free composition.", "以 BPM 加快或放慢整段旋律，音高不變；自由創作中可調整。"),
    "piano_roll": ("Drag a note up/down for pitch or left/right for time; pull either bright edge to shorten or lengthen it. Click an empty cell to add; right-click deletes.", "上下拖音塊調音高、左右拖移動位置；拉動左右亮色邊緣可縮短或拉長。點空格加音，右鍵刪除。"),
    "piano_pitch_scroll": ("Scroll to reach higher or lower pitch rows; your notes stay unchanged.", "捲動以查看更高或更低的音高位置，不會修改音符。"),
    "piano_time_scroll": ("Scroll through the visible timeline without moving any notes.", "捲動可見的時間軸，不會移動音符。"),
    "note_add": ("Add a one-cell note in the first free grid position; select it to adjust pitch, start and length.", "在第一個空格加入一格長的音符，選中後可調音高、起點與長度。"),
    "note_delete": ("Remove the selected note, leaving a rest in its place; other notes do not move.", "刪除選中的音符並留下休止，其他音符不會移動。"),
    "note_pitch": ("Change the selected note's pitch without changing its time; type a note such as C4/C#4 or a MIDI value from 60–72.", "修改所選音符的音高而不改時間，可輸入 C4／C#4 等音名，或 MIDI 60–72。"),
    "note_start": ("Move the selected note's start along cells 0–15; each cell is a sixteenth note and overlap is rejected.", "移動所選音符的起始格（0–15），每格為十六分音符；不能與其他音符重疊。"),
    "note_length": ("Change how many grid cells the selected key is held; ADSR Release and effect tails may continue after it ends.", "調整所選音符按鍵持續的格數；結束後仍可能有 Release 與音效尾音。"),
    "preset": ("Load a starting timbre for experimentation; preview it to hear the new harmonic colour.", "載入一個起始音色供實驗，試聽即可聽到新的諧波色彩。"),
    "source": ("Choose the reference sound used by the audio test bench; this is a development comparison tool.", "選擇聲音測試台使用的參照音；這是開發用的聲音比較工具。"),
    "tab_harmonics": ("Adjust the relative levels of the fundamental and its overtones to change timbre.", "調整基音與各次諧波的相對強度，改變音色。"),
    "tab_envelope": ("Shape the start, decay, held level and release of each note with ADSR.", "用 ADSR 塑造每個音符的起音、衰減、持續音量與尾音。"),
    "tab_piano": ("Write note pitches and rhythm here; the current synthesizer plays the resulting melody.", "在這裡編寫音高與節奏，由目前的合成器演奏旋律。"),
    "tab_sound": ("Choose the tone colour and effects used to play your notes; note positions are kept.", "調整演奏音符時使用的音色與效果，音符位置保持不變。"),
    "tab_pitch_correction": ("Adjust the pitch of marked recording regions; this does not rewrite the song's rhythm.", "調整指定錄音片段的音高，不會重寫歌曲節奏。"),
}

PARAMETER_HELP = {
    "attack": ("Set how long each note takes to rise to full level; shorter Attack gives a sharper start.", "設定每個音符上升到最高音量所需的時間；Attack 越短，起音越俐落。"),
    "decay": ("Set how long the peak falls to Sustain; shorter Decay makes that initial drop quicker.", "設定最高音量降到 Sustain 的時間；Decay 越短，最初的衰減越快。"),
    "sustain": ("Sustain sets the held note's level after Decay; this is an amplitude level, not a time.", "設定 Decay 後按住音符時的音量；Sustain 是強度，不是時間。"),
    "release": ("Set how long the sound fades after key release; longer Release leaves a longer dry tail.", "設定放開音符後聲音淡出的時間；Release 越長，乾聲尾音越長。"),
    "filter_enabled": ("Enable or bypass the filter, which removes frequency regions according to its type and cutoff.", "開啟或略過濾波器，按類型與截止頻率削弱特定頻段。"),
    "filter_mode": ("Low-pass reduces frequencies above the cutoff; high-pass reduces frequencies below it.", "低通削弱截止頻率以上的聲音；高通削弱截止頻率以下的聲音。"),
    "cutoff_hz": ("Set the filter's dividing frequency in Hz; low-pass removes higher frequencies and high-pass removes lower ones.", "設定濾波器的分界頻率（Hz）；低通削弱其上方頻段，高通削弱其下方頻段。"),
    "resonance": ("Emphasise frequencies near the cutoff; increasing resonance can make the filter sound more pronounced or ringing.", "突出截止頻率附近的聲音；共振越高，濾波特徵或鳴響越明顯。"),
    "delay_enabled": ("Enable repeated echoes after the original sound; turn it off to hear the signal without Delay.", "開啟原聲後的重複回聲；關閉後可聽到不含 Delay 的聲音。"),
    "delay_time": ("Set the time between echoes; a larger value spaces the repeats farther apart.", "設定相鄰回聲的時間間隔；數值越大，重複聲相隔越遠。"),
    "delay_decay": ("Set how long the repeated echoes take to fade; this changes their persistence, not their spacing.", "設定重複回聲衰減的時間，影響回聲持續多久，而不是回聲間隔。"),
    "delay_mix": ("Blend the delayed sound with the dry signal; increasing Wet mix makes echoes more prominent.", "混合回聲與乾聲；提高濕聲比例會讓回聲更突出。"),
    "reverb_enabled": ("Enable room-like reflections and a reverberant tail around the sound.", "開啟類似房間反射的空間感與混響尾音。"),
    "reverb_room": ("Change the simulated room size; larger values generally give a more spacious, longer reverberant tail.", "改變模擬空間大小；數值越大，通常空間感越明顯、混響尾音越長。"),
    "reverb_damping": ("Reduce high frequencies in the reverberant tail; higher damping makes the reflections darker.", "削弱混響尾音中的高頻；阻尼越高，反射聲越暗。"),
    "reverb_mix": ("Blend the reverberant sound with the dry signal; increasing Wet mix makes the space more noticeable.", "混合混響與乾聲；提高濕聲比例會讓空間感更明顯。"),
}
PARAMETER_HELP["h1"] = ("Set the fundamental's relative strength, changing the body's balance against the overtones without changing the note pitch.",
                         "設定基音的相對強度，改變它與高次諧波的平衡，不會改變音符音高。")
for harmonic in range(2, 9):
    PARAMETER_HELP[f"h{harmonic}"] = (
        f"Set harmonic {harmonic}'s relative strength at {harmonic} times the note frequency; stronger upper harmonics can make the timbre brighter or richer.",
        f"設定第 {harmonic} 次諧波的相對強度，頻率為基音的 {harmonic} 倍；提高高次諧波可使音色更明亮或豐富。")

HELP.update({f"parameter_{key}": value for key, value in PARAMETER_HELP.items()})

# Same physical controls, different meaning in music repair. Never overwrite
# the ordinary synthesis help used by tone/hidden/melody modes.
REPAIR_LABELS = {
    "filter_enabled": ("Enable filter recovery", "啟用頻段修復"),
    "filter_mode": ("Estimated damage type", "估計濾波損傷類型"),
    "cutoff_hz": ("Estimated cutoff (Hz)", "估計截止頻率（Hz）"),
    "resonance": ("Estimated resonance", "估計共振"),
    "delay_enabled": ("Enable echo cancellation", "啟用回聲抵消"),
    "delay_time": ("Estimated spacing (s)", "估計回聲間隔（秒）"),
    "delay_decay": ("Estimated decay (s)", "估計回聲衰減（秒）"),
    "delay_mix": ("Estimated echo amount", "估計回聲比例"),
    "reverb_enabled": ("Enable room recovery", "啟用空間修復"),
    "reverb_room": ("Estimated room size", "估計空間大小"),
    "reverb_damping": ("Estimated damping", "估計阻尼"),
    "reverb_mix": ("Estimated reverb amount", "估計混響比例"),
}
REPAIR_HELP = {
    "filter_enabled": ("Enable frequency recovery; switching this repair tool off keeps the original filter damage.", "啟用頻段修復；關閉這台修復工具會保留原本的濾波損傷。"),
    "filter_mode": ("Estimate whether low-pass or high-pass filtering damaged the recording; this is not a new filter applied to the evidence.", "估計錄音受到低通還是高通損傷；不是對證物再添加一個濾波器。"),
    "cutoff_hz": ("Estimate the damaging filter's cutoff; closer calibration restores more of the missing frequency content.", "估計造成損傷的截止頻率；校準越接近，恢復的頻段越多。"),
    "resonance": ("Estimate the original filter resonance; matching it helps restore the frequency balance.", "估計原本的濾波共振；校準相符可進一步恢復頻段平衡。"),
    "delay_enabled": ("Enable the echo canceller; switching this tool off leaves the original echoes in the recording.", "啟用回聲抵消器；關閉工具會保留錄音原本的回聲。"),
    "delay_time": ("Estimate the original gap between echoes; both values that are too short and too long reduce repair quality.", "估計原本的回聲間隔；估得太短或太長，都會降低修復效果。"),
    "delay_decay": ("Estimate how long the original echoes persist; this calibrates removal, rather than adding new echoes.", "估計原本回聲的持續衰減時間，用來校準移除，而不是添加新回聲。"),
    "delay_mix": ("Estimate the amount of echo damage; zero is not a bypass and maximum is not automatic repair.", "估計原本的回聲比例；歸零不是略過，調到最大也不會自動修好。"),
    "reverb_enabled": ("Enable room recovery; switching this tool off keeps the original reverberation.", "啟用空間修復；關閉工具會保留原本的混響。"),
    "reverb_room": ("Estimate the room size that coloured the recording; a closer estimate reduces the remaining reverberation.", "估計影響錄音的空間大小；越接近原本設定，殘留混響越少。"),
    "reverb_damping": ("Estimate how dark the original reflections sound; calibrating damping helps recover the dry recording.", "估計原本反射聲的高頻阻尼；校準相符有助於恢復乾淨錄音。"),
    "reverb_mix": ("Estimate the original reverberation amount; higher values do not necessarily remove more reverb.", "估計原本的混響比例；數值越高不代表移除越多。"),
}
HELP.update({f"repair_{key}": value for key, value in REPAIR_HELP.items()})

COMMON = {"language": "language", "volume": "volume", "stop_button": "stop"}
HELP.update({
    "diagnostic_export": ("Save the checks and troubleshooting details as a local JSON report.", "將檢查結果與排錯資訊儲存為本機 JSON 報告。"),
    "diagnostic_close": ("Close diagnostics and return to the game.", "關閉診斷並返回遊戲。"),
    "undo_edit": ("Undo the last edit. Submissions, unlocked stages and hints are retained.", "復原上一次編輯；提交、已開放步驟與提示紀錄會保留。"),
    "redo_edit": ("Reapply an undone edit. A new edit replaces the redo branch.", "重新套用已復原的編輯；新增編輯會取代原本的重做分支。"),
    "music_loop": ("Repeat the selected time range in the current repair. Edits stop playback; preview again to hear them.", "循環播放目前修復的選定時間範圍；修改會停止播放，再試聽可聽到新設定。"),
    "music_range": ("Choose a time range in seconds for evidence, repair and before/after previews. This does not alter the recording.", "以秒選擇證物、修復與前後比較的試聽範圍，不會裁剪原始錄音。"),
    "music_pin": ("Keep your current settings as the before version for comparison during this step.", "將目前設定記為這一步的對比基準，供前後比較。"),
    "music_ab": ("Hear your saved before version, then your current repair, using the same time range. The clean answer stays hidden.", "以相同時間範圍依次聆聽已記下的版本與目前修復；不會播放隱藏的乾淨答案。"),
    "music_restore": ("Restore your comparison version's controls. This edit can be undone and does not remove submissions.", "恢復對比版本的控制項；可以復原此操作，提交紀錄不受影響。"),
    "music_note_range": ("Use the selected note and a little surrounding context as the audition range.", "將選中的音符及前後少許上下文設為試聽範圍。"),
    "diagnostics": ("Check dependencies, audio devices, engine and required files; export a diagnostic report if needed.", "檢查依賴、音訊裝置、引擎與必要檔案；需要時可匯出診斷報告。"),
})
WINDOWS = {
    "bench": {"play_a": "play_target", "play_b": "play_current", "play_ab": "play_ab", "compare_button": "submit_bench",
              "source": "source", "preset": "preset", "release": "parameter_release", "cutoff": "parameter_cutoff_hz",
              "filter": "parameter_filter_enabled", "delay": "parameter_delay_enabled", "reverb": "parameter_reverb_enabled"},
    "tone": {"play_a": "play_target", "play_b": "play_current", "play_ab": "play_ab", "compare_button": "submit_tone",
             "restart_button": "restart_tone", "review_button": "review"},
    "campaign": {"case_selector": "case_selector", "next_button": "next_case", "music_button": "open_music"},
    "music": {"play_evidence": "evidence", "play_current": "music_current", "submit_button": "submit_music_stage",
              "reveal_button": "reveal_song", "restart_button": "restart_music", "deck_stop": "stop", "check_repair_button": "check_repair",
              "goto_button": "music_goto", "play_region_button": "music_monitor"},
    "hidden": {"play_reference": "hidden_target", "play_current": "play_current", "play_ab": "hidden_ab", "submit_button": "submit_hidden",
               "hint_button": "hint", "lesson_button": "lesson", "goto_button": "suggested", "history_button": "history",
               "restore_button": "restore", "history_play": "hear_history", "reset_button": "restart_hidden"},
    "melody": {"play_reference": "hidden_target", "play_current": "play_current", "play_ab": "hidden_ab", "submit_button": "submit_melody",
               "hint_button": "hint", "lesson_button": "lesson", "goto_button": "suggested", "history_button": "history",
               "restore_button": "restore", "history_play": "hear_history", "reset_button": "reset_draft", "tempo": "tempo"},
}


def help_text(key, language):
    return HELP[key][language == "zh-Hant"]


def set_help(widget, key, language, *, suffix=""):
    """Apply the same explanatory text to tooltip and screen-reader description."""
    style_tooltips()
    text = help_text(key, language) + suffix
    widget.setToolTip("<qt>" + escape(text) + "</qt>")
    if isinstance(widget, QWidget):
        widget.setProperty("hoverHelpKey", key)
        widget.setProperty("hoverHelpLanguage", language)
        widget.setAccessibleDescription(text)
        widget.setToolTipDuration(10000)
        widget.window().setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
        from ..audio.ui_sounds import bind_button_click
        bind_button_click(widget)
    return text


def apply_window_help(owner, mode, language):
    from ..audio.ui_sounds import bind_volume, bind_tab_clicks
    bind_volume(owner)
    if hasattr(owner, 'edit_bar'):
        owner.edit_bar.translate(language)
    for attribute, key in (COMMON | WINDOWS[mode]).items():
        widget = getattr(owner, attribute, None)
        if isinstance(widget, QWidget):
            set_help(widget, key, language)
    for device, button in getattr(owner, "device_buttons", {}).items():
        set_help(button, "device_melody" if mode == "melody" and device == "synth" else f"device_{device}", language)
    if mode == "melody":
        bind_tab_clicks(owner.work_tabs)
        for key, button in owner.mode_buttons.items():
            set_help(button, key, language)
        owner.work_tabs.setTabToolTip(0, help_text("tab_piano", language))
        owner.work_tabs.setTabToolTip(1, help_text("tab_sound", language))
    if mode == "music":
        bind_tab_clicks(owner.tabs)
        owner.tabs.setTabToolTip(0, help_text("tab_pitch_correction", language))
        owner.tabs.setTabToolTip(1, help_text("repair_tab", language))
        owner.tabs.setTabToolTip(2, help_text("check_repair", language))


def set_parameter_help(editor, language):
    for key, control in editor.controls.items():
        gesture = ""
        if key in editor.knobs:
            gesture = " 上下拖曳旋鈕（Shift 精細調整），或在下方輸入數值。" if language == "zh-Hant" else " Drag the knob up/down (Shift for fine control), or type the value below."
        elif key in editor.sliders:
            gesture = " 拖曳推桿，或在數值框輸入精確強度。" if language == "zh-Hant" else " Drag the fader or type an exact strength in the numeric field."
        for widget in (control, editor.labels[key], editor.sliders.get(key), editor.knobs.get(key)):
            if widget is not None:
                set_help(widget, f"parameter_{key}", language, suffix=gesture)
        if key == "filter_mode" and hasattr(control, "buttons"):
            for button in control.buttons:
                set_help(button, f"parameter_{key}", language)
    if editor.tabs:
        from ..audio.ui_sounds import bind_tab_clicks
        bind_tab_clicks(editor.tabs)
        for index, group in enumerate(editor._tab_groups):
            key = f"tab_{group}" if group in ("harmonics", "envelope") else f"device_{group}"
            editor.tabs.setTabToolTip(index, help_text(key, language))


def style_tooltips():
    """One readable tooltip style for all windows in this application."""
    app = QApplication.instance()
    if app is not None and not app.property("soundDetectiveHoverStyle"):
        app.setStyleSheet(app.styleSheet() + "\nQToolTip { color: #f4e8cd; background-color: #242a24; border: 1px solid #b59a65; padding: 7px; font-size: 13px; }")
        app.setProperty("soundDetectiveHoverStyle", True)


def show_scene_help(view, event):
    """Route help through scaled scene proxies, including disabled controls.

    Qt's normal widget tooltip handling is not dependable when widgets have
    been reparented into a fixed graphics proxy. Hit-test the existing scene;
    this never clicks a control or changes its state.
    """
    position = view.mapToScene(event.pos())
    for item in view.scene().items(position):
        if isinstance(item, QGraphicsProxyWidget):
            root = item.widget()
            if root is None:
                continue
            local = item.mapFromScene(position).toPoint()
            widget = root.childAt(local) or root
            while widget is not None:
                if widget.toolTip():
                    QToolTip.showText(event.globalPos(), widget.toolTip(), view.viewport())
                    event.accept()
                    return True
                if widget is root:
                    break
                widget = widget.parentWidget()
        elif item.toolTip():
            QToolTip.showText(event.globalPos(), item.toolTip(), view.viewport())
            event.accept()
            return True
    return False
