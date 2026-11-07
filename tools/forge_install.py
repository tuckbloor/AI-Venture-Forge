"""AI Venture Forge v0.8.0-rc2 portable, two-stage Windows installer.

Checks for a compatible AI App Server installation, offers to install a
standalone prerequisite, and creates a separate isolated Forge instance.
Existing installations are backed up before managed application files update;
private databases and settings are never overwritten by the installer.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'framework'
VERSION = '0.8.0-rc2'
SUPPORTED_SERVER_VERSIONS = {(1, 0, 4), (1, 0, 5)}
PRODUCT_MARKER = '.venture-forge-install.json'
SERVER_MARKER = '.venture-forge-server-install.json'
MANAGED_FILES = ('START.bat', 'forge.py', 'worker.py', 'seed_demo.py',
                 'README.md', 'LICENSE', 'requirements.txt')
MANAGED_DIRS = ('engine', 'starter', 'tools')
LEGACY_FILES = ('app.py', 'START-BUSINESS.bat', 'START-HERE.bat', 'START-WORKER.bat',
                'create-demo-team.bat','ensure-env.bat','run-app.bat','run-tests.bat',
                'setup.bat','worker_silent.py','USER-GUIDE.md','Dockerfile','compose.yaml')

class InstallError(RuntimeError):
    pass


def base() -> Path:
    return Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'Programs'


def default_server() -> Path:
    return base() / 'AI-App-Server'


def default_forge() -> Path:
    return base() / 'AI-Venture-Forge'


def python_for(root: Path) -> Path:
    return root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def server_version(root: Path):
    try:
        text = (root / 'engine/ai_app_server/version.py').read_text(encoding='utf-8')
    except OSError:
        return None
    m = re.search(r"__version__\s*=\s*['\"](\d+)\.(\d+)\.(\d+)['\"]", text)
    return tuple(map(int, m.groups())) if m else None


def valid_server_source(path: Path) -> bool:
    return (server_version(path) in SUPPORTED_SERVER_VERSIONS
            and all((path / p).is_file() for p in (
                'engine/pyproject.toml', 'engine/ai_app_server/server.py',
                'engine/ai_app_server/desktop_launcher.py', 'starter/app.py')))


def installed_server(path: Path) -> bool:
    # A downloaded source tree without a runtime isn't an installed server.
    return (valid_server_source(path) and (path / 'app/app.py').is_file()
            and python_for(path).is_file())


def discover_server() -> Path | None:
    candidates = []
    if os.environ.get('AI_APP_SERVER_HOME'):
        candidates.append(Path(os.environ['AI_APP_SERVER_HOME']))
    candidates += [default_server(), Path.home() / 'AI-App-Server']
    if os.name == 'nt':
        try:
            from ctypes import windll
            mask = windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if mask & (1 << i):
                    d = Path(f'{chr(65+i)}:/')
                    candidates.extend((d / 'AI-App-Server', d / 'ai-app-server'))
        except (OSError, AttributeError):
            pass
    for p in candidates:
        try:
            p = p.expanduser().resolve()
            if installed_server(p):
                return p
        except OSError:
            continue
    return None


def validate_source():
    if not valid_server_source(BUNDLE) or server_version(BUNDLE) != (1, 0, 5):
        raise InstallError('Bundled AI App Server v1.0.5 is incomplete. Extract the entire ZIP.')
    if not all((ROOT / item).is_file() for item in (
            'app/app.py', 'forge.py', 'worker.py', 'START.bat', 'INSTALL.bat',
            'tools/forge_launcher.py', 'framework/server-start.template')):
        raise InstallError('AI Venture Forge source is incomplete. Extract the entire ZIP.')


def same_or_nested(a: Path, b: Path):
    a, b = a.resolve(), b.resolve()
    return a == b or a in b.parents or b in a.parents


def validate_paths(server: Path, forge: Path):
    if same_or_nested(server, forge):
        raise InstallError('Server and Forge must use different, non-nested directories.')
    if same_or_nested(forge, ROOT) or same_or_nested(server, ROOT):
        raise InstallError('Choose installation folders separate from your downloaded source.')


def safe_folder(path: Path):
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise InstallError('Destination must be an ordinary local directory.')
    # Refuse symbolic links inside managed destination on update.
    if path.is_dir() and any(p.is_symlink() for p in path.iterdir()):
        raise InstallError('Destination contains symbolic links. Refusing unsafe update.')


def recognized_forge(dest: Path) -> bool:
    try:
        marker = json.loads((dest / PRODUCT_MARKER).read_text(encoding='utf-8'))
        if (marker.get('product') == 'AI-Venture-Forge'
                and (dest / 'forge.py').is_file() and (dest / 'app/app.py').is_file()
                and (dest / 'START.bat').is_file()):
            return True
    except (OSError, ValueError, TypeError):
        pass
    # Recognise original v0.7 Streamlit installation for an explicit migration,
    # not an arbitrary folder with only one matching filename.
    return (all((dest / p).is_file() for p in (
        'forge.py','app.py','worker.py','START-BUSINESS.bat'))
        and ((dest / 'data/agentforge.sqlite3').is_file() or
             python_for(dest).is_file()))


def recoverable_server(dest: Path) -> bool:
    try:
        marker = json.loads((dest / SERVER_MARKER).read_text(encoding='utf-8'))
        return (marker == {'product':'AI-App-Server', 'created_by':'AI-Venture-Forge', 'version':'1.0.5'}
                and valid_server_source(dest) and (dest / 'START.bat').is_file())
    except (OSError, ValueError, TypeError):
        return False


def run(cmd, cwd, log=print, timeout=600):
    log('> ' + ' '.join(str(x) for x in cmd))
    # Stream output for the persistent GUI log rather than spawning invisible consoles.
    proc = subprocess.Popen([str(x) for x in cmd], cwd=str(cwd), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, errors='replace', bufsize=1)
    try:
        for line in proc.stdout:
            log(line.rstrip())
        rc = proc.wait(timeout=timeout)
    except Exception:
        proc.kill();proc.wait()
        raise
    if rc:
        raise InstallError(f'Command failed (exit {rc}): {cmd[0]}; details are in the installer log.')


def _copy(src: Path, dst: Path):
    if src.is_symlink():
        raise InstallError(f'Symbolic-link source is not permitted: {src}')
    if src.is_dir():
        for p in src.rglob('*'):
            if p.is_symlink():
                raise InstallError(f'Symbolic-link source is not permitted: {p}')
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info','.pytest_cache'))
    else:
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)


def install_server(dest: Path, *, copy_only=False, log=print):
    """Install a new *independent* AI App Server; never modify an existing one."""
    dest = dest.resolve();safe_folder(dest)
    recovering = dest.exists() and any(dest.iterdir()) and recoverable_server(dest)
    if dest.exists() and any(dest.iterdir()) and not recovering:
        raise InstallError('AI App Server destination is not empty. Select an existing compatible server or an empty directory.')
    if not recovering:
        dest.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.forge-server-stage-',dir=str(dest.parent)))
        try:
            for key in ('engine','starter'):_copy(BUNDLE/key,stage/key)
            _copy(BUNDLE/'tools/bootstrap.py',stage/'tools/bootstrap.py')
            _copy(BUNDLE/'server-start.template',stage/'START.bat')
            _copy(ROOT/'LICENSE',stage/'LICENSE')
            (stage/'README.md').write_text('# AI App Server 1.0.5\n\nIndependent AI App Server installation. Run START.bat.\n',encoding='utf-8')
            (stage/SERVER_MARKER).write_text(json.dumps({'product':'AI-App-Server','created_by':'AI-Venture-Forge','version':'1.0.5'}),encoding='utf-8')
            if dest.exists():dest.rmdir()
            stage.rename(dest)
        finally:
            if stage.exists():shutil.rmtree(stage)
    if copy_only:return dest
    exe=python_for(dest)
    if not exe.exists():run([sys.executable,'-m','venv',str(dest/'.venv')],dest,log)
    run([str(exe),str(dest/'tools/bootstrap.py')],dest,log)
    run([str(exe),'-m','pip','install','--disable-pip-version-check','-e',str(dest/'engine')],dest,log)
    if not installed_server(dest):
        raise InstallError('New AI App Server verification failed. Its files are preserved for recovery.')
    # Do not silently enable a second server at sign-in; user can start it separately.
    log('AI App Server installed at '+str(dest))
    return dest


def _write_product_marker(folder: Path):
    (folder/PRODUCT_MARKER).write_text(json.dumps({'product':'AI-Venture-Forge','version':VERSION},indent=2),encoding='utf-8')


def _install_fresh(dest: Path):
    dest.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.forge-stage-',dir=str(dest.parent)))
    try:
        for name in MANAGED_FILES:_copy(ROOT/name,stage/name)
        for name in ('app', 'tools'):_copy(ROOT/name,stage/name)
        for name in ('engine','starter'):_copy(BUNDLE/name,stage/name)
        _copy(BUNDLE/'tools/bootstrap.py',stage/'tools/bootstrap.py')
        _write_product_marker(stage)
        if dest.exists():dest.rmdir()
        stage.rename(dest)
    finally:
        if stage.exists():shutil.rmtree(stage)


def _install_update(dest: Path):
    """Back up existing files, then atomically replace managed files; private data untouched."""
    backup=dest/'backups'/('pre-'+VERSION+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
    backup.mkdir(parents=True,exist_ok=False)
    # Back up everything managed that will be replaced, including the user-owned
    # app.py if customized, without copying or modifying private runtime data.
    replace=[*MANAGED_FILES,'app/app.py','tools/forge_launcher.py','tools/forge_install.py',
             'tools/bootstrap.py','engine','starter',PRODUCT_MARKER,*LEGACY_FILES]
    previous=[];written=[]
    try:
        for rel in replace:
            target=dest/rel
            if target.exists():
                _copy(target,backup/rel)
                previous.append(rel)
        for rel in replace:
            source=(BUNDLE/rel if rel.startswith(('engine','starter')) else
                    BUNDLE/'tools/bootstrap.py' if rel=='tools/bootstrap.py' else ROOT/rel)
            target=dest/rel
            if rel==PRODUCT_MARKER:
                _write_product_marker(dest);written.append(rel);continue
            if rel in LEGACY_FILES:
                if target.is_file():target.unlink();written.append(rel)
                continue
            if not source.exists():continue
            if target.is_dir():shutil.rmtree(target)
            elif target.exists():target.unlink()
            _copy(source,target)
            written.append(rel)
        return backup,previous,written
    except Exception:
        rollback(dest,backup,previous,written)
        raise


def rollback(dest: Path, backup: Path, previous: list[str], written: list[str]):
    for rel in reversed(written):
        target=dest/rel
        if target.is_dir():shutil.rmtree(target)
        elif target.exists():target.unlink()
    for rel in previous:
        restored=backup/rel
        if restored.exists():_copy(restored,dest/rel)


def install_forge(dest: Path, *, copy_only=False, allow_update=False, autostart=False, log=print):
    dest=dest.resolve();safe_folder(dest)
    nonempty=dest.exists() and any(dest.iterdir())
    if nonempty and not recognized_forge(dest):
        raise InstallError('Unrelated non-empty destination. Nothing was overwritten. Choose a different folder.')
    if nonempty and not allow_update:
        raise InstallError('Existing AI Venture Forge installation detected. Confirm update in installer (or use --accept-update).')
    old=None
    if nonempty:
        old=_install_update(dest)
        log('Backup of old application files: '+str(old[0]))
    else:
        _install_fresh(dest)
    try:
        if not copy_only:
            exe=python_for(dest)
            if not exe.is_file():run([sys.executable,'-m','venv',str(dest/'.venv')],dest,log)
            run([str(exe),'-m','pip','install','--disable-pip-version-check','-e',str(dest/'engine')],dest,log)
            run([str(exe),'-m','pip','install','--disable-pip-version-check','-r',str(dest/'requirements.txt')],dest,log)
            # Runtime data is initialized by bootstrap+Forge on first server request.
            run([str(exe),str(dest/'tools/bootstrap.py')],dest,log)
            if autostart:
                run([str(exe),str(dest/'tools/forge_launcher.py'),'install'],dest,log,timeout=120)
    except Exception:
        if old:
            log('Install failed. Restoring previous application code from backup.')
            rollback(dest,old[0],old[1],old[2])
        raise
    if not copy_only:remember_install(dest)
    log('AI Venture Forge installed at '+str(dest))
    return dest


def install_state() -> Path:
    """A user-local pointer, separate from Git and installed databases."""
    override=os.environ.get('VENTURE_FORGE_STATE_FILE')
    if override:return Path(override).expanduser().resolve()
    return Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'AI-Venture-Forge' / 'installation.json'


def remember_install(path: Path):
    target=install_state()
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps({'schema':1,'product':'AI-Venture-Forge',
                                'folder':str(path.resolve())}),encoding='utf-8')
    temp.replace(target)


def installed_folder_from_state() -> Path | None:
    try:
        data=json.loads(install_state().read_text(encoding='utf-8'))
        dest=Path(data['folder']).expanduser().resolve()
        if data.get('schema')==1 and data.get('product')=='AI-Venture-Forge' and recognized_forge(dest) and python_for(dest).is_file():
            return dest
    except (OSError,KeyError,ValueError,TypeError):
        pass
    return None


def launch_installed(action='start') -> int:
    path=installed_folder_from_state()
    if path is None:
        from_default=default_forge()
        if recognized_forge(from_default) and python_for(from_default).is_file():
            path=from_default
        else:
            try:
                import tkinter as tk
                from tkinter import filedialog
                root=tk.Tk();root.withdraw()
                selected=filedialog.askdirectory(parent=root,title='Select the INSTALLED AI Venture Forge folder')
                root.destroy()
                if not selected:return 1
                path=Path(selected).expanduser().resolve()
            except Exception:
                print('Installed folder not found. Run INSTALL.bat or specify its installed START.bat.',file=sys.stderr)
                return 1
            if not recognized_forge(path) or not python_for(path).is_file():
                print('Selected directory is not a completed Venture Forge installation.',file=sys.stderr)
                return 1
    run([str(python_for(path)),str(path/'tools/forge_launcher.py'),action],path)
    return 0


def installation_log() -> Path:
    base_path=Path(os.environ.get('LOCALAPPDATA') or Path.home())/'AI-Venture-Forge'
    base_path.mkdir(parents=True,exist_ok=True)
    return base_path/'installer.log'


def run_pipeline(*, server: Path, forge: Path, install_new_server: bool,
                 accept_update=False, copy_only=False, autostart=False, log=print):
    validate_source()
    server=Path(server).expanduser().resolve();forge=Path(forge).expanduser().resolve()
    validate_paths(server,forge)
    log('AI Venture Forge '+VERSION)
    log('AI App Server: '+str(server))
    log('Venture Forge: '+str(forge))
    if install_new_server:
        if installed_server(server):
            raise InstallError('A compatible server already exists there. Choose Use Existing Server instead.')
        install_server(server,copy_only=copy_only,log=log)
        # Copy-only is used exclusively for testing; no venv exists yet.
    elif not installed_server(server):
        raise InstallError('AI App Server is not installed or is incompatible at '+str(server)+'. Select Install Server First.')
    return install_forge(forge,copy_only=copy_only,allow_update=accept_update,autostart=autostart,log=log)


def gui():
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    window=tk.Tk()
    window.title('Install AI Venture Forge '+VERSION)
    window.geometry('810x640')
    window.minsize(730,580)
    window.resizable(True,True)
    found=discover_server()
    mode=tk.StringVar(value='existing' if found else 'new')
    server=tk.StringVar(value=str(found or default_server()))
    forge=tk.StringVar(value=str(default_forge()))
    autostart=tk.BooleanVar(value=False)
    top=ttk.Frame(window,padding=16);top.pack(fill='x')
    ttk.Label(top,text='AI Venture Forge',font=('Segoe UI',20,'bold')).pack(anchor='w')
    ttk.Label(top,text='Step 1: AI App Server prerequisite  •  Step 2: independent Venture Forge',font=('Segoe UI',10)).pack(anchor='w',pady=(4,10))
    ttk.Radiobutton(top,text='Use an existing AI App Server (read-only)',variable=mode,value='existing').pack(anchor='w')
    ttk.Radiobutton(top,text='Install AI App Server first',variable=mode,value='new').pack(anchor='w')
    def entry(label,value):
        ttk.Label(top,text=label).pack(anchor='w',pady=(10,2))
        row=ttk.Frame(top);row.pack(fill='x')
        ttk.Entry(row,textvariable=value).pack(side='left',fill='x',expand=True)
        def browse():
            start=Path(value.get()).expanduser()
            while not start.exists() and start!=start.parent:start=start.parent
            result=filedialog.askdirectory(parent=window,initialdir=str(start),title=label)
            if result:value.set(result)
        ttk.Button(row,text='Browse...',command=browse).pack(side='left',padx=(8,0))
    entry('AI App Server directory (existing or new)',server)
    entry('AI Venture Forge installation directory',forge)
    ttk.Checkbutton(top,text='Start Forge now and enable automatic startup at Windows sign-in',variable=autostart).pack(anchor='w',pady=(12,0))
    ttk.Label(top,text='Existing Forge installation: Yes updates app files after a backup; No cancels. Data is preserved.').pack(anchor='w',pady=(5,0))
    ttk.Separator(window).pack(fill='x',pady=8)
    ttk.Label(window,text='Installation progress and errors',font=('Segoe UI',11,'bold')).pack(anchor='w',padx=16)
    import tkinter.scrolledtext
    logbox=tkinter.scrolledtext.ScrolledText(window,height=12,state='disabled',font=('Consolas',9))
    logbox.pack(fill='both',expand=True,padx=16,pady=8)
    buttons=ttk.Frame(window,padding=(16,0,16,12));buttons.pack(fill='x')
    status=tk.StringVar(value='Ready')
    ttk.Label(buttons,textvariable=status).pack(side='left')
    install_button=ttk.Button(buttons,text='Install / Update');install_button.pack(side='right')
    close_button=ttk.Button(buttons,text='Close',command=window.destroy);close_button.pack(side='right',padx=8)
    messages=queue.Queue();busy=[False]
    def add_line(msg):messages.put(str(msg))
    def poll():
        try:
            while True:
                obj=messages.get_nowait()
                if isinstance(obj,tuple):
                    busy[0]=False;install_button.configure(state='normal');close_button.configure(state='normal')
                    status.set('Installed successfully' if obj[0]=='ok' else 'Installation stopped: read the error above')
                    continue
                logbox.configure(state='normal');logbox.insert('end',obj+'\n');logbox.see('end');logbox.configure(state='disabled')
        except queue.Empty:pass
        window.after(100,poll)
    def begin():
        sp=Path(server.get().strip().strip('"')).expanduser().resolve()
        fp=Path(forge.get().strip().strip('"')).expanduser().resolve()
        try:
            validate_source();validate_paths(sp,fp)
            if mode.get()=='existing' and not installed_server(sp):
                raise InstallError('No compatible installed AI App Server found in selected folder. Choose Install Server First.')
            if fp.exists() and any(fp.iterdir()):
                if not recognized_forge(fp):
                    raise InstallError('Selected Forge folder contains another project. Choose a new directory.')
                if not messagebox.askyesno('Existing AI Venture Forge project',
                    'An existing AI Venture Forge installation was found.\n\n'
                    'Do you want to overwrite its application files with this version?\n\n'
                    'A backup will be created. Databases, users, settings and agents will not be overwritten.',parent=window):
                    add_line('Update cancelled. Nothing was changed.');return
                accept=True
            else:accept=False
            if mode.get()=='new' and sp.exists() and any(sp.iterdir()) and not recoverable_server(sp):
                raise InstallError('AI App Server destination is not empty. Choose Use Existing or select an empty folder.')
        except (InstallError,OSError) as exc:
            add_line('ERROR: '+str(exc));status.set('Please correct the installation paths');return
        mode_value=mode.get()
        autostart_value=autostart.get()
        busy[0]=True;status.set('Installing — see log below');install_button.configure(state='disabled');close_button.configure(state='disabled')
        def job():
            try:
                path=installation_log()
                with path.open('a',encoding='utf-8') as logfile:
                    def out(line):
                        logfile.write(str(line)+'\n');logfile.flush();add_line(line)
                    run_pipeline(server=sp,forge=fp,install_new_server=mode_value=='new',
                                 accept_update=accept,autostart=autostart_value,log=out)
                    out('SUCCESS. Forge installed. Open '+str(fp/'START.bat'))
                messages.put(('ok',None))
            except Exception as exc:
                add_line('INSTALL FAILED: '+str(exc))
                messages.put(('fail',None))
        threading.Thread(target=job,daemon=True).start()
    install_button.configure(command=begin)
    def onclose():
        if busy[0]:messagebox.showinfo('Installation running','The installer is working. Keep this window open until it finishes.',parent=window)
        else:window.destroy()
    window.protocol('WM_DELETE_WINDOW',onclose)
    window.after(100,poll);window.mainloop()


def main(argv=None):
    parser=argparse.ArgumentParser(description='AI Venture Forge portable installer')
    parser.add_argument('--server',type=Path,help='Location of existing AI App Server')
    parser.add_argument('--install-server',type=Path,help='Install new AI App Server at this destination')
    parser.add_argument('--forge',type=Path,help='Venture Forge install destination')
    parser.add_argument('--copy-only',action='store_true',help='Stage source files, skip Python dependencies and starting')
    parser.add_argument('--accept-update',action='store_true',help='Confirm an existing Forge app update (with backups)')
    parser.add_argument('--start',action='store_true',help='Start Forge and configure sign-in autostart')
    parser.add_argument('--launch-installed',action='store_true',help='Launch installed Forge from downloaded source folder')
    parser.add_argument('--action',choices=['start','stop','status','remove-startup'],default='start')
    args=parser.parse_args(argv)
    if args.launch_installed:
        try:return launch_installed(args.action)
        except Exception as exc:
            print('Launch failed:',exc,file=sys.stderr);return 1
    if args.server and args.install_server:
        parser.error('Select an existing server OR --install-server, not both')
    if not (args.server or args.install_server or args.forge or args.copy_only):
        try:gui();return 0
        except Exception as exc:
            print('Installer window unavailable: '+str(exc),file=sys.stderr)
            print('Use: INSTALL.bat --server PATH --forge PATH',file=sys.stderr)
            return 1
    try:
        if not args.forge:raise InstallError('--forge is required in command-line mode')
        if not args.server and not args.install_server:raise InstallError('Select --server or --install-server')
        run_pipeline(server=args.server or args.install_server,forge=args.forge,
                     install_new_server=bool(args.install_server),accept_update=args.accept_update,
                     copy_only=args.copy_only,autostart=args.start)
        return 0
    except (InstallError, OSError, subprocess.SubprocessError) as exc:
        print('INSTALL FAILED: '+str(exc),file=sys.stderr)
        print('Existing files and databases were not intentionally removed.',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
