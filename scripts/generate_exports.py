"""Generate reviewable baseline and staged-change exports via the application API."""
import json,sys,copy,tempfile,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import backend.main as service
from backend.main import app,ROOT

def generate():
    with TestClient(app) as client:
        client.post('/api/login',json={'username':'admin','password':os.getenv('DEMO_PASSWORD','ChronoGrid2026!')}).raise_for_status()
        client.post('/api/reset',json={}).raise_for_status()
        baseline=client.get('/api/export');baseline.raise_for_status()
        (ROOT/'exports'/'schedule.json').write_text(json.dumps(baseline.json(),indent=2),encoding='utf-8')
        change=json.loads((ROOT/'data'/'sample_disruption.json').read_text())
        proposal=client.post('/api/changes',json=change);proposal.raise_for_status();p=proposal.json()
        if 'id' not in p:raise RuntimeError(p)
        assert client.post('/api/changes/'+p['id']+'/approve',json={}).status_code==403,'Self-approval must be blocked'
        (ROOT/'exports'/'repair_proposal.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
        client.post('/api/login',json={'username':'admin2','password':os.getenv('DEMO_PASSWORD','ChronoGrid2026!')}).raise_for_status()
        client.post('/api/changes/'+p['id']+'/approve',json={}).raise_for_status()
        after=client.get('/api/export');after.raise_for_status()
        (ROOT/'exports'/'dataset_after.json').write_text(json.dumps(service.STATE['data'],indent=2),encoding='utf-8')
        print(json.dumps({'baseline':baseline.json()['report'],'after':after.json()['report'],'moved':p['moved'],'exam_moved':p['exam_moved'],'added':p['added'],'minimum_moves_proven':p['minimum_moves_proven']},indent=2))

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='chronogrid-exports-') as directory:
        service.RUNTIME=Path(directory);service.STATE=service.initial();service.TOKENS={}
        generate()

