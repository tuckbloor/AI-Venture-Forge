"""Background AgentForge scheduler (run in separate supervised process)."""
import argparse
import time
import os
from pathlib import Path


def single_worker_lock():
    """Prevent two schedulers from processing the same application's queue."""
    lockfile=Path(__file__).resolve().parent/'data'/'worker.lock'
    lockfile.parent.mkdir(parents=True,exist_ok=True)
    handle=open(lockfile,'a+b')
    handle.seek(0)
    handle.write(b'0')
    handle.flush()
    handle.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise RuntimeError('A Venture Forge worker is already running for this project.')
    return handle
from forge import connect, setup, process_due, worker_heartbeat, recover_stale_runs, bootstrap_business


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--once',action='store_true',help='Check one due or approved job then stop')
    p.add_argument('--poll-seconds',type=int,default=20)
    args=p.parse_args()
    instance_lock=single_worker_lock()
    db=connect();setup(db);bootstrap_business(db)
    try:
        print('AgentForge worker started — Ctrl+C to stop',flush=True)
        worker_heartbeat(db,'starting')
        count=recover_stale_runs(db)
        if count: print('Marked stale runs as failed:',count,flush=True)
        while True:
            worker_heartbeat(db)
            rid=process_due(db,on_step=lambda s:print(s,flush=True))
            if rid:
                row=db.execute('SELECT status,error FROM runs WHERE id=?',(rid,)).fetchone()
                print(f'Run {rid[:12]}: {row["status"]} {row["error"]}',flush=True)
            if args.once: break
            time.sleep(max(5,args.poll_seconds))
    except KeyboardInterrupt:
        print('Worker stopped',flush=True)
    finally:
        db.close()
        instance_lock.close()

if __name__=='__main__': main()
