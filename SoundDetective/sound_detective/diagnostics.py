"""Independent startup checks with actionable, bilingual results."""

from datetime import datetime, timezone
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def collect_diagnostics(*, root=None, probe_audio=True):
    root = Path(root or ROOT)
    checks = []

    def check(code, operation, en, zh, fix_en='', fix_zh='', *, warning=False):
        try:
            details = operation()
            status = 'ok'
        except Exception as error:
            status, details = ('warning' if warning else 'error'), str(error)
        checks.append(dict(code=code, status=status, en=en, zh=zh, details=details,
                           fix_en=fix_en, fix_zh=fix_zh))

    for module, distribution in (('numpy', 'numpy'), ('scipy', 'scipy'), ('soundfile', 'soundfile'),
            ('librosa', 'librosa'), ('pythonosc', 'python-osc'), ('PySide6.QtMultimedia', 'PySide6')):
        def dependency(module=module, distribution=distribution):
            importlib.import_module(module)
            return metadata.version(distribution)
        check(f'dependency:{module}', dependency, f'Dependency: {module}', f'依賴：{module}',
              'Reinstall the packaged game, or recreate .venv using requirements-lock.txt.',
              '重新安裝遊戲，或依 requirements-lock.txt 重建 .venv。')

    def engine():
        from .audio.sc_client import find_executable, supercollider_executable_names
        return {name: str(find_executable(name)) for name in supercollider_executable_names()}
    check('engine', engine, 'SuperCollider audio engine', 'SuperCollider 音訊引擎',
          'Keep engine/SuperCollider with the packaged game, or set SOUND_DETECTIVE_SC_DIR.',
          '保留安裝包的 engine/SuperCollider，或設定 SOUND_DETECTIVE_SC_DIR。')

    def assets():
        from .game.cases import load_campaign
        from .ui.studio_scenes import SCENES
        files = [root/'assets/ui'/name for scene in SCENES.values() for name in (scene.room_art, scene.desk_art)]
        files += [root/'assets/audio/ui-click.wav'] + [root/'supercollider'/name for name in
            ('synth.scd', 'engine.scd', 'music_example_player.scd')]
        missing = [str(p.relative_to(root)) for p in files if not p.is_file()]
        if missing:
            raise FileNotFoundError(', '.join(missing))
        cases = load_campaign(root/'content/cases')
        from .game.sound_categories import load_source_cases
        sources = load_source_cases(root/'content/sound_cases')
        from .game.melody import load_melody_cases
        melodies=load_melody_cases(root/'content/melody_cases')
        return {'timbre_cases': len(cases), 'category_cases': len(sources), 'melody_cases':len(melodies), 'assets_verified': True}
    check('content', assets, 'Levels, scene art and audio files', '關卡、場景與音源',
          'Reinstall the game files, scene art and synthesized case definitions.',
          '重新安裝遊戲程式、場景圖片與合成案件設定。')

    def optional_music():
        from .game.availability import music_availability
        result = music_availability(root=root)
        if not result.available:
            raise ValueError('M01 unavailable; all synthesized cases and free composition remain playable. / '
                             'M01 暫不可玩；合成案件與自由創作仍可使用。 '+result.reason)
        return result.to_dict()
    check('optional_music', optional_music, 'Optional recorded-music case', '可選的錄音歌曲案件',
          'Continue playing the other modes. Supply the configured local M01 assets only if needed.',
          '可繼續其他玩法；需要 M01 時才提供對應的本機音源。', warning=True)

    for name in ('userdata', '.runtime'):
        def writable(name=name):
            directory = root/name
            directory.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=directory) as stream:
                stream.write(b'Sound Detective write check')
            return str(directory)
        check(f'writable:{name}', writable, f'Writable folder: {name}', f'可寫入資料夾：{name}',
              'Install in a folder you can write to, such as your user folder.', '請安裝在可寫入的位置，例如使用者資料夾。')

    def staging():
        directory = Path(os.environ.get('SOUND_DETECTIVE_TEMP', tempfile.gettempdir()))
        if not str(directory).isascii():
            raise ValueError(str(directory))
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=directory):
            pass
        return str(directory)
    check('audio_temp', staging, 'Audio engine temporary folder', '音訊引擎暫存資料夾',
          'Set SOUND_DETECTIVE_TEMP to a writable ASCII-only folder.',
          '將 SOUND_DETECTIVE_TEMP 設為可寫入、路徑只有英文字元的資料夾。')

    if probe_audio:
        def audio():
            from PySide6.QtMultimedia import QMediaDevices
            devices = QMediaDevices.audioOutputs()
            if not devices:
                raise RuntimeError('No audio output / 沒有音訊輸出裝置')
            return [d.description() for d in devices]
        check('audio_device', audio, 'Audio output devices', '音訊輸出裝置',
              'Connect headphones or speakers and select an audio output device.',
              '連接耳機或喇叭，並選擇音訊輸出裝置。', warning=True)
    return {'schema_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
            'project': str(root), 'python': sys.version.split()[0], 'executable': sys.executable,
            'platform': platform.platform(), 'checks': checks,
            'ok': not any(c['status'] == 'error' for c in checks)}


def format_report(report, language='en'):
    zh = language == 'zh-Hant'
    lines = ['Sound Detective · ' + ('啟動診斷' if zh else 'Startup diagnostics'),
             report['created_utc'], report['project'], f"Python {report['python']}", '']
    for item in report['checks']:
        lines += [f"[{item['status'].upper()}] {item['zh' if zh else 'en']}", str(item['details'])]
        if item['status'] != 'ok':
            lines += [item['fix_zh' if zh else 'fix_en']]
        lines += ['']
    return '\n'.join(lines)


def save_report(report, path):
    Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
