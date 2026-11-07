"""Starts one local AI App Server instance and one Venture Forge worker.

Uses each application's own .venv and database. Does not modify an existing
AI App Server installation. Supports start/stop/status/sign-in startup.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def runtime():
    return ROOT / 'data'

def _worker_record():
    return runtime() / 'worker-process.json'

def _command(pid: int) -> str:
    if sys.platform == 'win32':
        proc=subprocess.run(['powershell.exe','-NoProfile','-Command',
                             f'(Get-CimInstance Win32_Process -Filter "ProcessId = {pid}").CommandLine'],
                            capture_output=True,text=True,timeout=12)
        return proc.stdout.casefold() if proc.returncode==0 else ''
    try:
        return (Path('/proc')/str(pid)/'cmdline').read_bytes().replace(b'\0',b' ').decode('utf-8',errors='ignore').casefold()
    except OSError:
        return ''

def worker_is_ours(pid:int) -> bool:
    s=_command(pid)
    return 'worker.py' in s and str(ROOT).casefold() in s

def worker_alive() -> bool:
    try:
        record=json.loads(_worker_record().read_text(encoding='utf-8'))
        return worker_is_ours(int(record['pid'])) and record['root']==str(ROOT)
    except (OSError,TypeError,ValueError,KeyError):
        return False

def start_worker():
    if worker_alive():
        print('Forge worker is already running.',flush=True);return
    data=runtime();logs=data/'logs';logs.mkdir(parents=True,exist_ok=True)
    python=Path(sys.executable)
    if sys.platform=='win32':
        windowless=python.with_name('pythonw.exe')
        if windowless.is_file():python=windowless
    flags=(getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)) if sys.platform=='win32' else 0
    kwargs={} if sys.platform=='win32' else {'start_new_session':True}
    with (logs/'forge-worker.log').open('a',encoding='utf-8') as file:
        file.write('\n--- Starting Forge worker ---\n');file.flush()
        proc=subprocess.Popen([str(python),str(ROOT/'worker.py'),'--poll-seconds','20'],
            cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=file,stderr=subprocess.STDOUT,
            creationflags=flags,**kwargs)
    _worker_record().write_text(json.dumps({'pid':proc.pid,'root':str(ROOT)}),encoding='utf-8')
    print('Started Forge worker PID:',proc.pid,flush=True)

def stop_worker():
    marker=_worker_record()
    if not marker.is_file():
        print('No worker process recorded.');return
    try:
        obj=json.loads(marker.read_text(encoding='utf-8'))
        pid=int(obj['pid'])
        if obj.get('root')!=str(ROOT) or not worker_is_ours(pid):
            print('Worker no longer running or belongs to another process; will not terminate it.')
            marker.unlink(missing_ok=True)
            return
        if sys.platform=='win32':
            result=subprocess.run(['taskkill.exe','/PID',str(pid),'/F'],capture_output=True,text=True)
            if result.returncode:raise RuntimeError(result.stderr.strip() or 'Worker could not be stopped')
        else:os.kill(pid,signal.SIGTERM)
        marker.unlink(missing_ok=True)
        print('Forge worker stopped.',flush=True)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise RuntimeError(f'Cannot safely stop worker: {exc}') from exc

def framework(action,background=False):
    cmd=[sys.executable,'-m','ai_app_server.desktop_launcher',action,'--project',str(ROOT)]
    if background:cmd.append('--no-browser')
    r=subprocess.run(cmd,cwd=str(ROOT))
    if r.returncode:raise RuntimeError('AI App Server '+action+' failed; see data/logs/server.log')

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['start','install','stop','status','remove-startup'])
    parser.add_argument('--background',action='store_true')
    args=parser.parse_args(argv)
    try:
        if not (ROOT/'app/app.py').is_file():
            raise RuntimeError('Forge application not installed in this folder. Run INSTALL.bat from the downloaded source.')
        if args.action in ('start','install'):
            # Start the app first; a failed server must not spawn orphaned workers.
            framework('start',background=args.background)
            start_worker()
            if args.action=='install' and sys.platform=='win32':
                from ai_app_server.desktop_launcher import enable_startup
                enable_startup(ROOT)
        elif args.action=='stop':
            stop_worker();framework('stop',background=True)
        elif args.action=='remove-startup':framework('remove-startup',background=True)
        else:
            framework('status',background=True)
            print('Forge worker:', 'running' if worker_alive() else 'not responding')
        return 0
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr,flush=True)
        return 1

if __name__=='__main__':raise SystemExit(main())
