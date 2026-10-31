"""Disposable local workflow QA server; production runtime/state.json is untouched."""
import copy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import backend.main as service
import uvicorn
import os

if __name__=='__main__':
    os.environ['AUTH_COOKIE_NAME']='chronogrid_preview_session'
    service.STATE=copy.deepcopy(service.STATE)
    service.STATE.update(requests=[],proposals=[],leaves=[],audit=[])
    service.RUNTIME=ROOT/'evidence'/'workflow-preview-runtime'
    service.RUNTIME.mkdir(parents=True,exist_ok=True)
    uvicorn.run(service.app,host='127.0.0.1',port=8004)
