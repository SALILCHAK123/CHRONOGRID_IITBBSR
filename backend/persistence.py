"""Atomic JSON snapshots; deployment deliberately uses a single process."""
import json
import os
from pathlib import Path

def atomic_json(path:Path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
