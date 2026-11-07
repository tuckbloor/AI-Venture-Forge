"""End-to-end source/upgrade tests; no network or real user files are touched."""
from __future__ import annotations
from pathlib import Path
import json
import runpy
import shutil
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'framework'/'engine'))
import forge_install as i
import forge
from ai_app_server.ui import Context,set_context,reset_context


def fake_installed_server(path):
    i.install_server(path,copy_only=True)
    py=i.python_for(path)
    py.parent.mkdir(parents=True,exist_ok=True)
    py.write_bytes(b'test interpreter marker')
    app=path/'app/app.py'
    app.parent.mkdir(parents=True)
    app.write_text('import ai_app_server as ui\nui.title("My App")',encoding='utf-8')
    return path


def test_source_contains_only_two_bat_files_and_no_legacy_readmes():
    assert sorted(x.name for x in ROOT.rglob('*.bat'))==['INSTALL.bat','START.bat']
    assert (ROOT/'README.md').is_file()
    assert not (ROOT/'USER-GUIDE.md').exists()
    i.validate_source()
    assert i.server_version(i.BUNDLE)==(1,0,5)


def test_server_first_then_forge_independent_paths(tmp_path):
    server=tmp_path/'server installed';studio=tmp_path/'forge installed'
    i.run_pipeline(server=server,forge=studio,install_new_server=True,copy_only=True)
    assert i.valid_server_source(server)
    assert not i.installed_server(server) # Copy-only is not a real install
    assert i.recognized_forge(studio)
    assert (studio/'engine/ai_app_server/server.py').is_file()
    assert (studio/'app/app.py').is_file()
    assert not (studio/'data').exists()
    assert not (studio/'framework').exists()


def test_existing_server_stays_unchanged(tmp_path):
    server=fake_installed_server(tmp_path/'AI-App-Server')
    private=server/'data'/'server.sqlite3';private.parent.mkdir();private.write_bytes(b'UNTOUCHED')
    target=tmp_path/'AI-Venture-Forge'
    i.run_pipeline(server=server,forge=target,install_new_server=False,copy_only=True)
    assert private.read_bytes()==b'UNTOUCHED'
    assert not (server/'forge.py').exists()


def test_existing_requires_confirmation_and_preserves_database(tmp_path):
    target=tmp_path/'forge'
    i.install_forge(target,copy_only=True)
    db=target/'data/agentforge.sqlite3';db.parent.mkdir();db.write_bytes(b'PRIVATE DATABASE')
    custom=target/'app/my_plugin.py';custom.write_text('KEEP = True',encoding='utf-8')
    old_file=target/'forge.py';old_file.write_text('# old controlled code',encoding='utf-8')
    with pytest.raises(i.InstallError,match='Confirm update'):
        i.install_forge(target,copy_only=True)
    assert old_file.read_text()=='# old controlled code'
    i.install_forge(target,copy_only=True,allow_update=True)
    assert old_file.read_text().startswith('"""AgentForge')
    assert db.read_bytes()==b'PRIVATE DATABASE'
    assert custom.read_text()=='KEEP = True'
    backups=list((target/'backups').glob('pre-*'))
    assert len(backups)==1
    assert (backups[0]/'forge.py').read_text()=='# old controlled code'


def test_refuse_unrelated_and_nested_paths(tmp_path):
    target=tmp_path/'other';target.mkdir();(target/'important.txt').write_text('KEEP')
    with pytest.raises(i.InstallError,match='Unrelated'):
        i.install_forge(target,copy_only=True,allow_update=True)
    assert (target/'important.txt').read_text()=='KEEP'
    with pytest.raises(i.InstallError,match='non-nested'):
        i.validate_paths(tmp_path/'server',tmp_path/'server'/'forge')


def test_upgrade_rolls_back_managed_files_on_failure(tmp_path,monkeypatch):
    target=tmp_path/'forge'
    i.install_forge(target,copy_only=True)
    before=target/'forge.py';before.write_text('#old',encoding='utf-8')
    private=target/'data/file.sqlite3';private.parent.mkdir();private.write_bytes(b'SAFE')
    def fail(*a,**k):raise i.InstallError('simulated pip failure')
    monkeypatch.setattr(i,'run',fail)
    with pytest.raises(i.InstallError,match='simulated'):
        i.install_forge(target,allow_update=True,copy_only=False)
    assert before.read_text()=='#old'
    assert private.read_bytes()==b'SAFE'


def test_legacy_streamlit_install_can_be_confirmed_and_migrated(tmp_path):
    legacy=tmp_path/'04-agentforge';legacy.mkdir()
    for rel in ('forge.py','worker.py'):
        shutil.copy2(ROOT/rel,legacy/rel)
    (legacy/'app.py').write_text('legacy dashboard',encoding='utf-8')
    (legacy/'START-BUSINESS.bat').write_text('@echo off',encoding='utf-8')
    private=legacy/'data/agentforge.sqlite3';private.parent.mkdir();private.write_bytes(b'LEGACY_DB')
    assert i.recognized_forge(legacy)
    i.install_forge(legacy,copy_only=True,allow_update=True)
    assert (legacy/'app/app.py').exists()
    assert not (legacy/'START-BUSINESS.bat').exists()
    assert not (legacy/'app.py').exists()
    assert private.read_bytes()==b'LEGACY_DB'
    assert list((legacy/'backups').glob('pre-*/app.py'))


def test_ui_all_sections_render_without_ollama(tmp_path,monkeypatch):
    db_path=tmp_path/'forge.sqlite3'
    original=forge.connect
    monkeypatch.setattr(forge,'connect',lambda: original(db_path))
    monkeypatch.setattr(forge,'ollama_models',lambda:([], 'Ollama not running'))
    for section in ('Overview','Live team','Agents','Workflows','Approvals','History','Worker'):
        ctx=Context(values={'vf_section':section});token=set_context(ctx)
        try:
            runpy.run_path(str(ROOT/'app/app.py'),run_name='__main__')
        finally:reset_context(token)
        assert len(ctx.components)>5,section


def test_ui_create_agent_action(tmp_path,monkeypatch):
    db_path=tmp_path/'forge.sqlite3';original=forge.connect
    monkeypatch.setattr(forge,'connect',lambda: original(db_path))
    monkeypatch.setattr(forge,'ollama_models',lambda:(['llama3.2:3b'],None))
    ctx=Context(values={'vf_section':'Agents','vf_new_name':'Safety Tester',
        'vf_new_role':'Testing','vf_new_instructions':'Test safely',
        'vf_new_model':'llama3.2:3b','vf_create_agent':True})
    token=set_context(ctx)
    try:runpy.run_path(str(ROOT/'app/app.py'),run_name='__main__')
    finally:reset_context(token)
    with original(db_path) as db:
        assert any(a['name']=='Safety Tester' for a in forge.list_agents(db))


def test_source_launcher_remembers_installed_path(tmp_path,monkeypatch):
    target=tmp_path/'Forge App';i.install_forge(target,copy_only=True)
    exe=i.python_for(target);exe.parent.mkdir(parents=True,exist_ok=True)
    exe.write_bytes(b'test')
    state=tmp_path/'user-local-installation.json'
    monkeypatch.setenv('VENTURE_FORGE_STATE_FILE',str(state))
    i.remember_install(target)
    assert i.installed_folder_from_state()==target.resolve()
    called=[]
    monkeypatch.setattr(i,'run',lambda command,cwd:called.append((command,cwd)))
    assert i.launch_installed('status')==0
    assert called[0][0][1].endswith('forge_launcher.py')
    assert called[0][0][-1]=='status'
    assert called[0][1]==target.resolve()


def test_rejected_unrelated_server_folder_is_not_modified(tmp_path):
    dest=tmp_path/'my photos';dest.mkdir();file=dest/'2020.jpg';file.write_bytes(b'PHOTO')
    with pytest.raises(i.InstallError,match='not empty'):
        i.install_server(dest,copy_only=True)
    assert file.read_bytes()==b'PHOTO'


def test_dashboard_active_run_prevents_duplicate_start(tmp_path, monkeypatch):
    db_path = tmp_path / 'safe.sqlite3'
    original = forge.connect
    with original(db_path) as db:
        forge.setup(db)
        forge.bootstrap_business(db)
        founder = next(w for w in forge.list_workflows(db) if w['name'] == 'Autonomous Online Business Founder')
        assert forge.request_run(db, founder['id'])
        assert forge.request_run(db, founder['id']) is None
    monkeypatch.setattr(forge, 'connect', lambda: original(db_path))
    context = Context(values={'vf_section': 'Overview', 'vf_start_founder': True})
    token = set_context(context)
    try:
        runpy.run_path(str(ROOT / 'app/app.py'), run_name='__main__')
    finally:
        reset_context(token)
    assert not any(c.get('id') == 'vf_start_founder' for c in context.components)
    assert any(c.get('type') == 'info_card' and c.get('status') == 'Queued for the AI worker'
               for c in context.components)
    with original(db_path) as db:
        assert len(forge.recent_runs(db, 20)) == 1


def test_forge_brand_static_assets_and_grid():
    root = ROOT / 'framework' / 'engine' / 'ai_app_server' / 'static'
    html = (root / 'app.html').read_text(encoding='utf-8')
    js = (root / 'app.js').read_text(encoding='utf-8')
    css = (root / 'app.css').read_text(encoding='utf-8')
    assert 'AI Venture Forge' in html
    assert 'forge-hero' in js
    assert 'forge-nav' in js
    assert '.forge-hero' in css
    assert '.cols' in css
    assert 'v0.8.0-rc2' in (ROOT/'README.md').read_text(encoding='utf-8')
