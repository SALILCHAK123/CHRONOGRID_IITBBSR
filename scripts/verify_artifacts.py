"""Record hashes, contracts and independently checked app-generated artifacts."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.constraints import validate
from backend.models import check_dataset
from backend.main import app
from scripts.create_dataset import create

ROOT=Path(__file__).resolve().parents[1]

def read(relative):return json.loads((ROOT/relative).read_text(encoding='utf-8-sig'))
def digest(relative):return hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()

if __name__=='__main__':
    evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
    data=read('data/cit_synthetic.json');check_dataset(data)
    assert create()==data,'Generator output differs from consumed input'
    after=read('exports/dataset_after.json');check_dataset(after)
    reports={}
    for label,source,file in [('baseline',data,'exports/schedule.json'),('after',after,'exports/schedule_after.json')]:
        schedule=read(file);report=validate(source,schedule)
        assert report['valid'],report
        reports[label]=dict(source_dataset='data/cit_synthetic.json' if label=='baseline' else 'exports/dataset_after.json',file=file,sha256=digest(file),teaching_sessions=len(schedule['sessions']),teaching_hours=sum(s['duration'] for s in source['sessions']),exams=len(schedule['exams']),bookings=len(schedule['bookings']),solver=schedule['solver'],report=report)
        (evidence/(label+'-validation.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    paths=['Problem statement.pdf','data/cit_synthetic.json','data/sample_disruption.json','exports/dataset_after.json','exports/schedule.json','exports/schedule_after.json','exports/repair_proposal.json']
    result=dict(date='2026-10-31',timezone='Asia/Calcutta',synthetic=True,official_validator_checked=False,source_hashes={p:digest(p) for p in paths},counts={k:len(data[k]) for k in ['rooms','faculty','groups','courses','sessions','bookings','exams']},students=sum(g['size'] for g in data['groups']),reports=reports,repair=read('exports/repair_proposal.json'))
    (evidence/'artifact-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (evidence/'openapi.json').write_text(json.dumps(app.openapi(),indent=2),encoding='utf-8')
    for name in ['test-results.txt','job-test-results.txt']:
        (evidence/name).write_text((ROOT/'runtime'/name).read_text(encoding='utf-8-sig'),encoding='utf-8')
    print(json.dumps({k:dict(sessions=v['teaching_sessions'],hard=v['report']['hard_violations'],soft=v['report']['soft_penalty'],solver=v['solver']) for k,v in reports.items()},indent=2))
