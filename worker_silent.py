"""Windows detached worker with durable logs."""
from pathlib import Path
import sys
from worker import main

log_path = Path(__file__).resolve().parent / 'data' / 'worker.log'
log_path.parent.mkdir(parents=True, exist_ok=True)
with log_path.open('a', encoding='utf-8', buffering=1) as log:
    sys.stdout = log
    sys.stderr = log
    main()
