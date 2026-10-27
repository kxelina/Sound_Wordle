"""Verify the public installer in a disposable Unicode path, then relocate it."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time,zipfile

root=Path.cwd().resolve();dev=root.parent/'SoundDetectiveDevelopment'
installer=root/'release/SoundDetective-Public-Setup.exe'
spec=importlib.util.spec_from_file_location('bundle',root/'launcher/package_release.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with zipfile.ZipFile(installer) as archive:
    manifest=json.loads(archive.read('release-manifest.json'))
    assert manifest['version']=='0.9.0' and manifest['public_build'] and not manifest['recorded_music_included']
    assert not any(name.lower().endswith('.mp3') or name.startswith('userdata/') for name in archive.namelist())
    assert 'content/music_cases/assets/M01-evidence.wav' not in archive.namelist()
    count=0
    for source in module.game_files(public=True):
        name=source.relative_to(root).as_posix();content=archive.read(name)
        assert content==source.read_bytes() and hashlib.sha256(content).hexdigest()==manifest['files'][name]['sha256'],name
        count+=1
base=(root/'.runtime/pub9').resolve();base.mkdir(parents=True,exist_ok=True)
installed=(base/'公開 試玩').resolve();moved=(base/'移動後 公開版').resolve()
assert installed.is_relative_to(base) and moved.is_relative_to(base) and base.is_relative_to(root/'.runtime')
assert not moved.exists()
start=time.monotonic()
resumed=installed.exists()
if resumed:
    assert json.loads((installed/'release-manifest.json').read_text('utf-8'))==manifest
else:
    subprocess.run([str(installer),'--install-dir',str(installed)],check=True,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
print('COMPOSITION_STUDIO_INSTALL_OK',flush=True)
with installer.open('rb') as file:sha=hashlib.file_digest(file,'sha256').hexdigest()
report={'version':manifest['version'],'installer':str(installer),'sha256':sha,'game_files_verified':count,
    'installation_seconds':None if resumed else round(time.monotonic()-start,2),
    'resumed_verified_installation':resumed,'different_physical_machine_tested':False,'checks':[]}

def native(folder,option):
    logs=folder/'.runtime/launcher';before=set(logs.glob('startup-*.log'))
    env=os.environ.copy();env.update(PYTHONHOME='C:/invalid-public-python',PYTHONPATH='C:/invalid-public-path',SOUND_DETECTIVE_SC_DIR='C:/invalid-public-sc')
    subprocess.run([str(folder/'SoundDetective.exe'),option],cwd=folder,env=env,check=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
    files=set(logs.glob('startup-*.log'))-before;assert len(files)==1
    log=files.pop().read_text('utf-8');assert 'SOUND_DETECTIVE_LAUNCH_CHECK_OK' in log
    result=next(json.loads(line) for line in log.splitlines() if line.startswith('{"project"'))
    assert Path(result['python_executable']).is_relative_to(folder/'runtime')
    assert not result['optional_music']['available']
    assert all(Path(value).is_relative_to(folder/'engine') for value in result['supercollider'].values())
    report['checks'].append({'root':str(folder),'option':option,'result':result})
    print(option,'OK',flush=True)

native(installed,'--check');native(installed,'--smoke-test')
assert installed.resolve().is_relative_to(base) and moved.is_relative_to(base) and not moved.exists()
for attempt in range(30):
    try:
        installed.rename(moved);break
    except PermissionError:
        if attempt==29:raise
        time.sleep(.5)  # Native loader/antivirus may briefly retain the directory.
native(moved,'--check');native(moved,'--smoke-test')
env=os.environ.copy();env.update(SOUND_DETECTIVE_QA_GAME=str(moved),QT_QPA_PLATFORM='offscreen',SOUND_DETECTIVE_UI_AUDIO='0',PYTHONIOENCODING='utf-8')
for key in ('PYTHONHOME','PYTHONPATH','SOUND_DETECTIVE_SC_DIR'):env.pop(key,None)
subprocess.run([str(moved/'runtime/python.exe'),'-B',str(dev/'validate_composition_ui.py')],cwd=moved,env=env,check=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
result=json.loads((dev/'.runtime/composition-ui/result.json').read_text('utf-8'))
assert Path(result['game_root'])==moved and result['actual_scene_instrument_autoplay'] and not result['errors']
assert Path(result['python_executable']).is_relative_to(moved/'runtime')
assert Path(result['sclang']).is_relative_to(moved/'engine') and Path(result['scsynth']).is_relative_to(moved/'engine')
report['relocated_directory']=str(moved);report['bundled_runtime_workspace_ui']=result
(dev/'.runtime/composition-install-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print('COMPOSITION_STUDIO_BUNDLE_VERIFIED',flush=True)
