"""Build a relocatable offline Windows installer from the verified local runtime.

No network downloads. No user progress, caches or development tests are packaged.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def game_files(*, public=False):
    """One allow-list used by full builds and environment-reusing refreshes."""
    result = []
    for name in ('sound_detective', 'assets', 'content', 'source', 'supercollider', 'docs'):
        for path in (ROOT/name).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            relative = path.relative_to(ROOT).as_posix()
            if public and (relative.startswith('source/') and relative != 'source/README.md'
                           or relative == 'content/music_cases/assets/M01-evidence.wav'):
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError('Unexpected linked game asset: '+relative)
            result.append(path)
    result += [ROOT/name for name in ('SoundDetective.exe', 'README.md', 'requirements-lock.txt')]
    return sorted(result)


def refresh(output, *, base_installer=None, public=False):
    """Reuse a previously built environment payload while updating game files."""
    output = Path(output).resolve()
    base_installer = Path(base_installer or output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    compiler = Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    build_root = ROOT/'.runtime/package-build'
    build_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='refresh-', dir=build_root) as temporary:
        stage = Path(temporary).resolve()
        if not stage.is_relative_to(build_root.resolve()):
            raise ValueError('Build path escaped workspace')
        stub, archive = stage/'Setup.exe', stage/'payload.zip'
        subprocess.run([str(compiler), '/nologo', '/target:winexe', '/optimize+', '/codepage:65001',
            '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll',
            '/reference:System.IO.Compression.dll', '/reference:System.IO.Compression.FileSystem.dll',
            '/reference:System.Web.Extensions.dll', '/out:'+str(stub), str(ROOT/'launcher/Installer.cs')], check=True)
        files = {}
        with zipfile.ZipFile(base_installer) as original, zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=5) as bundle:
            previous = json.loads(original.read('release-manifest.json'))
            for entry in original.infolist():
                if not entry.filename.startswith(('runtime/', 'engine/')):
                    continue
                hasher = hashlib.sha256()
                with original.open(entry) as source, bundle.open(entry.filename, 'w', force_zip64=True) as target:
                    while data := source.read(1024*1024):
                        hasher.update(data)
                        target.write(data)
                expected = previous['files'][entry.filename]
                if hasher.hexdigest() != expected['sha256']:
                    raise ValueError('Original environment payload is damaged: '+entry.filename)
                files[entry.filename] = expected
            live = game_files(public=public)
            for p in sorted(live):
                name = p.relative_to(ROOT).as_posix()
                bundle.write(p, name)
                files[name] = {'size': p.stat().st_size, 'sha256': digest(p)}
            previous['files'] = files
            previous.update(version='0.7.1', public_build=public, recorded_music_included=not public)
            bundle.writestr('release-manifest.json', json.dumps(previous, ensure_ascii=False, indent=2))
        replacement = stage/'SoundDetective-Setup.exe'
        with replacement.open('wb') as stream:
            for p in (stub, archive):
                with p.open('rb') as source:
                    shutil.copyfileobj(source, stream)
            stream.write(struct.pack('<q', archive.stat().st_size)+b'SDPACKV1')
        report = {'installer': str(output), 'bytes': replacement.stat().st_size,
                  'sha256': digest(replacement), 'files': len(files), 'refreshed_game_files': True,
                  'public_build': public, 'recorded_music_included': not public}
        replacement.replace(output)
        output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False), flush=True)


def build(output, sc_dir, *, public=False):
    if os.name != 'nt' or sys.version_info[:2] != (3, 11):
        raise RuntimeError('Build using the verified Windows Python 3.11 environment')
    sc_dir, output = Path(sc_dir).resolve(), Path(output).resolve()
    if not all((sc_dir/name).is_file() for name in ('sclang.exe', 'scsynth.exe', 'COPYING')):
        raise FileNotFoundError('Choose a complete SuperCollider installation')
    output.parent.mkdir(parents=True, exist_ok=True)
    build_root = ROOT/'.runtime/package-build'
    build_root.mkdir(parents=True, exist_ok=True)
    # TemporaryDirectory's cleanup is restricted to its validated build workspace.
    with tempfile.TemporaryDirectory(prefix='release-', dir=build_root) as temporary:
        stage = Path(temporary).resolve()
        if not stage.is_relative_to(build_root.resolve()):
            raise ValueError('Build path escaped workspace')
        payload = stage/'game'
        payload.mkdir()
        for path in game_files(public=public):
            destination = payload/path.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        python_home = Path(sys.base_prefix)
        shutil.copytree(python_home, payload/'runtime', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        site = ROOT/'.venv/Lib/site-packages'
        shutil.copytree(site, payload/'runtime/Lib/site-packages', dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(sc_dir, payload/'engine/SuperCollider', ignore=shutil.ignore_patterns('Uninstall.exe'))
        (payload/'userdata').mkdir()
        compiler = Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        stub = stage/'Setup.exe'
        subprocess.run([str(compiler), '/nologo', '/target:winexe', '/optimize+', '/codepage:65001',
            '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll',
            '/reference:System.IO.Compression.dll', '/reference:System.IO.Compression.FileSystem.dll',
            '/reference:System.Web.Extensions.dll', '/out:'+str(stub), str(ROOT/'launcher/Installer.cs')], check=True)
        files = sorted(p for p in payload.rglob('*') if p.is_file())
        manifest = {'version': '0.7.1', 'platform': 'windows-x86_64', 'python': sys.version.split()[0],
                    'public_build': public, 'recorded_music_included': not public,
                    'source_progress_included': False, 'files': {p.relative_to(payload).as_posix():
                    {'size': p.stat().st_size, 'sha256': digest(p)} for p in files}}
        manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)
        archive = stage/'payload.zip'
        print(f'Packing {len(files)} files; {sum(p.stat().st_size for p in files)/2**20:.1f} MiB uncompressed', flush=True)
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=5) as bundle:
            for p in files:
                bundle.write(p, p.relative_to(payload).as_posix())
            bundle.writestr('release-manifest.json', manifest_text)
        with output.open('wb') as stream:
            with stub.open('rb') as source:
                shutil.copyfileobj(source, stream)
            with archive.open('rb') as source:
                shutil.copyfileobj(source, stream)
            stream.write(struct.pack('<q', archive.stat().st_size)+b'SDPACKV1')
        report = {'installer': str(output), 'bytes': output.stat().st_size, 'sha256': digest(output),
                  'public_build': public, 'recorded_music_included': not public,
                  'files': len(files), 'bundled_python': str(python_home), 'bundled_engine': str(sc_dir),
                  'verification': 'Run installer and relocated EXE checks before distribution'}
        output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'release/SoundDetective-Setup.exe')
    parser.add_argument('--sc-dir', type=Path, required=True)
    parser.add_argument('--refresh', action='store_true', help='Reuse bundled environment; update current game files')
    parser.add_argument('--base-installer', type=Path, help='Existing verified installer supplying the runtime for --refresh')
    parser.add_argument('--public', action='store_true', help='Exclude local song recordings and M01 evidence')
    args = parser.parse_args()
    refresh(args.output, base_installer=args.base_installer, public=args.public) if args.refresh else build(args.output, args.sc_dir, public=args.public)
