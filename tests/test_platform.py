import copy,json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.constraints import validate,placement_errors,booking_errors,enriched
from backend.solver import solve
from backend.bookings import decide
from backend.assistant import parse_request
from backend.models import check_dataset
import backend.main as service

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='session')
def data():return json.loads((ROOT/'data'/'cit_synthetic.json').read_text())

@pytest.fixture(scope='session')
def baseline(data):
    result=solve(data,seconds=12);assert result['assignments'],result
    exams=solve(data,'exams',seconds=5);assert exams['assignments'],exams
    schedule=dict(meta={},sessions=result['assignments'],exams=exams['assignments'],bookings=decide(data,result['assignments']))
    schedule['report']=validate(data,schedule);assert schedule['report']['valid'],schedule['report']
    return schedule

def test_scope_and_solver(data,baseline):
    check_dataset(data)
    assert [len(data[k]) for k in ['rooms','faculty','groups','courses','sessions','bookings','exams']]==[27,40,14,62,189,25,41]
    assert sum(s['duration'] for s in data['sessions'])==243
    assert validate(data,baseline)['hard_violations']==0

@pytest.mark.parametrize('kind',['missing','duplicate','room','faculty','group','basket','fixed'])
def test_global_hard_constraints(data,baseline,kind):
    d=copy.deepcopy(data);s=copy.deepcopy(baseline)
    if kind=='missing':s['sessions'].pop()
    elif kind=='duplicate':s['sessions'].append(s['sessions'][0].copy())
    elif kind in ['room','faculty','group']:
        # Two compatible lectures forced to overlap; isolate each resource constraint.
        a=next(x for x in s['sessions'] if x['id']=='S040');b=next(x for x in s['sessions'] if x['id']=='S041')
        b.update(day=a['day'],start_period=a['start_period'])
        sa=next(x for x in d['sessions'] if x['id']==a['id']);sb=next(x for x in d['sessions'] if x['id']==b['id'])
        if kind=='room':b['room']=a['room']
        if kind=='faculty':sb['faculty']=sa['faculty'].copy()
        if kind=='group':sb['groups']=sa['groups'].copy()
    elif kind=='basket':
        a=next(x for x in s['sessions'] if x['id']=='S031');a['day']=(a['day']+1)%5
    else:
        next(x for x in s['sessions'] if x['id']=='S029')['day']=1
    assert not validate(d,s)['valid']

@pytest.mark.parametrize('kind',['capacity','type','faculty_leave','maintenance','lunch','lab','accessibility','daily_limit','exam_capacity'])
def test_local_hard_constraints(data,baseline,kind):
    d=copy.deepcopy(data);s=copy.deepcopy(baseline)
    if kind=='exam_capacity':
        a=s['exams'][0];session=next(x for x in d['exams'] if x['id']==a['id']);a['room']='CR-101'
        assert any('half exam capacity' in e for e in placement_errors(d,session,a,True));return
    a=s['sessions'][0];session=next(x for x in d['sessions'] if x['id']==a['id']);r=next(x for x in d['rooms'] if x['id']==a['room'])
    if kind=='capacity':r['capacity']=1
    elif kind=='type':r['type']='wrong_type'
    elif kind=='faculty_leave':next(f for f in d['faculty'] if f['id']==session['faculty'][0])['unavailable']=[dict(day=a['day'],start_period=a['start_period'],duration=3)]
    elif kind=='maintenance':r['unavailable']=[dict(day=a['day'],start_period=a['start_period'],duration=3)]
    elif kind=='lunch':a['start_period']=4
    elif kind=='lab':a['start_period']=1
    elif kind=='accessibility':session['accessible']=True;r['accessible']=False
    else:next(f for f in d['faculty'] if f['id']==session['faculty'][0])['daily_limit']=1
    assert not validate(d,s)['valid']

def test_booking_collisions_and_mandatory_groups(data,baseline):
    sessions=enriched(data,baseline['sessions']);a=sessions[0]
    b=dict(id='TEST',title='Test',day=a['day'],start_period=a['start_period'],duration=1,room=a['room'],size=1,category='club',groups=[])
    assert any('Room occupied' in e for e in booking_errors(data,b,sessions,[]))
    b['room']='AUD';b['groups']=a['groups']
    assert any('Mandatory group' in e for e in booking_errors(data,b,sessions,[]))
    b.update(day=0,start_period=10,room='AUD',groups=[])
    other={**b,'id':'OTHER'}
    assert any('Room occupied' in e for e in booking_errors(data,b,[],[other]))


def test_availability_alternatives_recheck_without_mutating_schedule(client):
    sign_in(client,'club')
    before=copy.deepcopy(service.STATE)
    occupied=next(b for b in before['schedule']['bookings'] if b['status']=='approved')
    draft=dict(title='Availability check only',room=occupied['room'],day=occupied['day'],start_period=occupied['start_period'],duration=1,size=1,category='club')
    response=client.post('/api/bookings/check',json=draft)
    assert response.status_code==200
    result=response.json()
    assert not result['valid'] and result['errors'] and result['alternatives']
    assert result['checks'] and result['revision']==before['revision']
    for offer in result['alternatives']:
        checked=client.post('/api/bookings/check',json={**draft,**offer})
        assert checked.status_code==200 and checked.json()['valid'],checked.text
    unavailable=client.post('/api/bookings/check',json={**draft,'size':10000}).json()
    assert not unavailable['valid'] and unavailable['alternatives']==[]
    assert service.STATE==before  # Checking or choosing an offer reserves nothing.


def test_room_discovery_returns_same_time_capacities_without_booking_authority(client):
    sign_in(client,'faculty')
    before=copy.deepcopy(service.STATE)
    query=dict(day=0,start_period=13,duration=1,size=30,room_type='classroom',accessible=True,groups=[])
    response=client.post('/api/venues/availability',json=query)
    assert response.status_code==200,response.text
    rooms=response.json()['available_rooms'];assert rooms
    known={r['id']:r for r in before['data']['rooms']}
    for room in rooms:
        assert room['day']==0 and room['start_period']==13
        assert room['capacity']==known[room['room']]['capacity']>=30
        assert room['name']==known[room['room']]['name']
        assert room['accessible'] and room['room_type']=='classroom'
        assert room['spare_seats']==room['capacity']-30
    # Read-only discovery does not grant Faculty venue-booking authority.
    assert client.post('/api/bookings',json=dict(title='Not authorised',category='club',room=rooms[0]['room'],**query)).status_code==403
    assert service.STATE==before


def test_room_discovery_type_suggestions_are_explicit_and_groups_checked(client):
    sign_in(client,'club')
    query=dict(day=0,start_period=13,duration=1,size=30,room_type='not-a-room-type',groups=[])
    result=client.post('/api/venues/availability',json=query).json()
    assert result['available_rooms']==[] and result['other_times']==[]
    assert result['suggested_room_types']
    assert client.post('/api/venues/availability',json={**query,'groups':['UNKNOWN']}).status_code==422


def test_targeted_room_move_stages_and_requires_independent_approval(client,monkeypatch,tmp_path):
    sign_in(client,'admin');before=copy.deepcopy(service.STATE['schedule']);data=service.STATE['data']
    source={s['id']:s for s in data['sessions']};all_rows=enriched(data,before['sessions'])
    from backend.constraints import overlap
    target=None
    for row in all_rows:
        if source[row['id']].get('fixed'):continue
        for room in data['rooms']:
            candidate=dict(id=row['id'],day=row['day'],start_period=row['start_period'],room=room['id'])
            if room['id']==row['room'] or placement_errors(data,source[row['id']],candidate):continue
            if any(other['id']!=row['id'] and other['room']==room['id'] and overlap(row,other) for other in all_rows):continue
            if any(b['status']=='approved' and b['room']==room['id'] and overlap(row,b) for b in before['bookings']):continue
            target=candidate;break
        if target:break
    assert target
    move={**target,'session':target['id']};move.pop('id')
    response=client.post('/api/changes',json={'moves':[move]});assert response.status_code==200,response.text
    proposal=response.json();assert 'id' in proposal,proposal
    assert service.STATE['schedule']==before
    changed=next(row for row in proposal['diff'] if row['id']==target['id'])
    assert changed['after']==target and proposal['after_report']['hard_violations']==0
    assert client.post('/api/changes/'+proposal['id']+'/approve',json={}).status_code==403
    monkeypatch.setattr(service,'ROOT',tmp_path);(tmp_path/'exports').mkdir()
    sign_in(client,'admin2');assert client.post('/api/changes/'+proposal['id']+'/approve',json={}).status_code==200
    assert next(row for row in service.STATE['schedule']['sessions'] if row['id']==target['id'])==target
    assert validate(data,service.STATE['schedule'])['valid']

def test_cancellation_and_priority(data,baseline):
    assert next(b for b in baseline['bookings'] if b['id']=='B025')['status']=='cancelled'
    d=copy.deepcopy(data);d['bookings']=[dict(id=bid,title=bid,room='AUD',day=0,start_period=10,duration=1,size=80,category=cat,groups=[]) for bid,cat in [('club','club'),('main','institute')]]
    decisions={b['id']:b for b in decide(d,baseline['sessions'])}
    assert decisions['main']['status']=='approved';assert decisions['club']['status']!='approved';assert decisions['club']['reason']

def test_parser_is_only_a_draft(data,monkeypatch):
    monkeypatch.delenv('AI_API_KEY',raising=False)
    result=parse_request('Monday shaam 6 baje Seminar Hall 1 chahiye, 80 students, 1 hour club talk',data)
    assert result['draft']['start_period']==10;assert result['draft']['day']==0;assert result['draft']['room']=='SH-1';assert not result['missing']
    assert parse_request('Book a room sometime',data)['missing']
    assert parse_request('Anything',data,True)['source']=='unavailable'
    change=parse_request('Move S041 to Wednesday P5',data)
    assert change['intent']=='schedule_change';assert not change['missing'];assert change['draft']['moves'][0]['session']=='S041'
    leave=parse_request('I am on full-day leave Monday',data,actor={'faculty':'F01'})
    assert leave['draft']['faculty_leave'][0]['faculty']=='F01';assert leave['draft']['faculty_leave'][0]['duration']==9

@pytest.mark.parametrize('text',['Change S005 to Thursday P6 in LAB-2','Modify timetable session S005 to Thursday P6 in LAB-2','Edit class S005 to Thursday P6 in LAB-2'])
def test_timetable_edit_phrases_produce_change_drafts(data,monkeypatch,text):
    monkeypatch.delenv('AI_API_KEY',raising=False)
    result=parse_request(text,data)
    assert result['intent']=='schedule_change' and not result['missing']
    assert result['draft']['moves']==[dict(session='S005',day=3,start_period=6,room='LAB-2')]

@pytest.fixture
def client(data,baseline,monkeypatch):
    fresh=dict(data=copy.deepcopy(data),schedule=copy.deepcopy(baseline),proposals=[],requests=[],audit=[],revision=0)
    monkeypatch.setattr(service,'STATE',fresh)
    def fake_save(action,u):fresh['revision']+=1;fresh['audit'].append(dict(action=action,user=u['id'],time='2026-10-31T00:00:00Z'))
    monkeypatch.setattr(service,'save',fake_save)
    with TestClient(service.app) as c:
        yield c

def sign_in(client,name):
    assert client.post('/api/login',json=dict(username=name,password='ChronoGrid2026!')).status_code==200

def test_auth_roles_priority_and_manual_outage(client):
    assert client.get('/api/state').status_code==401
    sign_in(client,'club')
    assert client.post('/api/generate',json={}).status_code==403
    b=dict(title='Test',room='AUD',day=0,start_period=13,duration=1,size=50,category='institute')
    assert client.post('/api/bookings',json=b).status_code==403
    b['category']='club';r=client.post('/api/bookings',json=b);assert r.status_code==200,r.text
    bid=r.json()['id'];assert client.post(f'/api/bookings/{bid}/approve',json={}).status_code==403
    assert client.post('/api/assistant/parse',json=dict(message='Book something',outage=True)).json()['source']=='unavailable'
    sign_in(client,'admin');assert client.post(f'/api/bookings/{bid}/approve',json={}).status_code==200
    assert validate(service.STATE['data'],service.STATE['schedule'])['valid']
    sign_in(client,'club');assert client.post(f'/api/bookings/{bid}/cancel',json={}).status_code==200

def test_server_blocks_forged_fields_and_constraints(client):
    sign_in(client,'club')
    b=dict(title='Fake',room='AUD',day=0,start_period=13,duration=1,size=50,category='club',status='approved')
    assert client.post('/api/bookings',json=b).status_code==422
    b.pop('status');b['size']=10000;assert client.post('/api/bookings',json=b).status_code==422
    assert client.post('/api/changes',json={'faculty_leave':[dict(faculty='F01',day=0,start_period=1,duration=9)]}).status_code==403
    sign_in(client,'faculty')
    assert client.post('/api/changes',json={'faculty_leave':[dict(faculty='F02',day=0,start_period=1,duration=9)]}).status_code==403

def test_repair_staging_self_approval_and_commit(client,monkeypatch,tmp_path):
    sign_in(client,'admin');before=copy.deepcopy(service.STATE['schedule']);a=before['sessions'][0]
    change=dict(room_closures=[dict(room=a['room'],day=a['day'],start_period=a['start_period'],duration=3)])
    r=client.post('/api/changes',json=change);assert r.status_code==200,r.text
    p=r.json();assert 'id' in p,p;assert p['moved']>=1;assert service.STATE['schedule']==before
    assert client.post('/api/changes/'+p['id']+'/approve',json={}).status_code==403
    (tmp_path/'exports').mkdir();monkeypatch.setattr(service,'ROOT',tmp_path)
    sign_in(client,'admin2');r=client.post('/api/changes/'+p['id']+'/approve',json={});assert r.status_code==200,r.text
    assert validate(service.STATE['data'],service.STATE['schedule'])['valid']
    assert (tmp_path/'exports'/'schedule_after.json').exists()

def test_proven_impossible_fixed_slot(data,baseline):
    d=copy.deepcopy(data);s=next(s for s in d['sessions'] if s.get('fixed'));f=next(f for f in d['faculty'] if f['id']==s['faculty'][0]);f['unavailable']=[dict(day=s['fixed']['day'],start_period=1,duration=9)]
    result=solve(d,baseline=baseline['sessions'],seconds=1)
    assert result['status']=='INFEASIBLE';assert result['diagnostics'][0]['excluded_by']

def test_joint_infeasibility_diagnostics(data):
    d=copy.deepcopy(data)
    d['sessions']=d['sessions'][27:29]
    for s in d['sessions']:s.update(fixed=dict(day=0,start_period=1),faculty=['F01'],groups=['Y1-A'],room_type='classroom',size=70,duration=1)
    result=solve(d,seconds=2)
    assert result['status']=='INFEASIBLE',result
    assert result['diagnostics'][0]['sessions']

def test_stale_proposal_cannot_apply(client):
    sign_in(client,'admin2')
    service.STATE['proposals'].append(dict(id='STALE',status='pending',requester='admin',revision=-1))
    assert client.post('/api/changes/STALE/approve',json={}).status_code==409

def test_extra_session_scope(client):
    sign_in(client,'faculty')
    s=copy.deepcopy(service.STATE['data']['sessions'][40]);s.update(id='EXTRA-1',faculty=['F02'])
    assert client.post('/api/changes',json={'added_sessions':[s]}).status_code==403

def test_week_specific_closures_and_utilisation(data,baseline):
    d=copy.deepcopy(data);a=baseline['exams'][0];exam=next(s for s in d['exams'] if s['id']==a['id'])
    for r in d['rooms']:r['unavailable']=[]
    room=next(r for r in d['rooms'] if r['id']==a['room'])
    room['unavailable']=[dict(week=7,day=a['day'],start_period=a['start_period'],duration=exam['duration'])]
    assert 'Room unavailable' not in placement_errors(d,exam,a,True)
    room['unavailable'][0]['week']=8
    assert 'Room unavailable' in placement_errors(d,exam,a,True)
    from backend.constraints import utilisation_report
    u=utilisation_report(d,enriched(d,baseline['sessions']))
    assert u['available_hours']==22*45  # 15 classrooms plus 7 labs; Week 8 closure excluded.
    room['unavailable'][0]['week']=7;room['unavailable'].append(room['unavailable'][0].copy())
    assert utilisation_report(d,[])['available_hours']==22*45-exam['duration']

def test_concurrent_pending_booking_approval(client):
    sign_in(client,'club')
    b=dict(title='Competing booking',room='AUD',day=0,start_period=13,duration=1,size=50,category='club')
    ids=[client.post('/api/bookings',json=b).json()['id'] for _ in range(2)]
    sign_in(client,'admin')
    assert client.post('/api/bookings/'+ids[0]+'/approve',json={}).status_code==200
    assert client.post('/api/bookings/'+ids[1]+'/approve',json={}).status_code==422
    assert len([b for b in service.STATE['schedule']['bookings'] if b['id'] in ids])==1

def test_demo_mode_and_rejection(client,monkeypatch):
    monkeypatch.setenv('DEMO_MODE','false')
    assert client.post('/api/demo/login',json={'username':'admin'}).status_code==403
    monkeypatch.setenv('DEMO_MODE','true')
    assert client.post('/api/demo/login',json={'username':'admin','role':'admin'}).status_code==422
    assert client.post('/api/demo/login',json={'username':'admin'}).status_code==200
    service.STATE['proposals'].append(dict(id='REJECT',status='pending',requester='admin'))
    assert client.post('/api/changes/REJECT/reject',json={'reason':'Needs revision'}).status_code==403
    sign_in(client,'admin2')
    assert client.post('/api/changes/REJECT/reject',json={'reason':'Needs revision'}).status_code==200

def test_ambiguous_parser_and_timeout(data,monkeypatch):
    monkeypatch.delenv('AI_API_KEY',raising=False)
    r=parse_request('kal AUD chahiye 80 students P10',data)
    assert 'day' in r['missing'] and 'duration' in r['missing']
    result=solve(data,seconds=0)
    assert result['status']=='UNKNOWN' and not result['assignments']

def test_dataset_department_links(data):
    courses={c['id']:c for c in data['courses']};faculty={f['id']:f for f in data['faculty']}
    for s in data['sessions']+data['exams']:
        assert courses[s['course']]['department']==s['department']
        assert all(faculty[f]['department']==s['department'] for f in s['faculty'])

def test_validator_rejects_assignment_identity_overrides(data,baseline):
    forged=copy.deepcopy(baseline);forged['sessions'][0]['faculty']=[]
    assert not validate(data,forged)['valid']

def test_atomic_failure_rolls_back(client,monkeypatch):
    sign_in(client,'admin')
    previous=copy.deepcopy(service.STATE)
    def fail(*args):raise OSError('Simulated storage failure')
    monkeypatch.setattr(service,'save',fail)
    with pytest.raises(OSError):
        client.post('/api/priorities',json={'priorities':['exam','class','guest','institute','department','club']})
    assert service.STATE==previous

@pytest.mark.parametrize('failure',['timeout','quota','malformed'])
def test_configured_provider_failure_preserves_manual_form(client,monkeypatch,failure):
    import backend.assistant as assistant
    import httpx
    monkeypatch.setenv('AI_API_KEY','test-only-placeholder');monkeypatch.setenv('AI_MODEL','test-placeholder')
    def failed_provider(*args,**kwargs):
        if failure=='timeout':raise httpx.ReadTimeout('Injected timeout')
        request=httpx.Request('POST','https://example.invalid/chat/completions')
        return httpx.Response(429 if failure=='quota' else 200,json={} if failure=='quota' else {'choices':[{'message':{'content':'not JSON'}}]},request=request)
    monkeypatch.setattr(assistant.httpx,'post',failed_provider)
    sign_in(client,'club');before=copy.deepcopy(service.STATE)
    r=client.post('/api/assistant/parse',json={'message':'Monday P13 AUD, 30 students, 1 hour club meeting'})
    assert r.json()['source']=='unavailable' and service.STATE==before
    b=dict(title='Manual during provider failure',room='AUD',day=0,start_period=13,duration=1,size=30,category='club')
    assert client.post('/api/bookings',json=b).status_code==200

def test_exam_only_repair_has_separate_diff(client):
    sign_in(client,'admin');before=copy.deepcopy(service.STATE['schedule']);a=before['exams'][0]
    p=client.post('/api/changes',json={'room_closures':[dict(week=8,room=a['room'],day=a['day'],start_period=a['start_period'],duration=2)]}).json()
    assert 'id' in p,p
    assert p['moved']==0 and p['exam_moved']>=1 and p['exam_diff']
    assert service.STATE['schedule']==before

def test_firewall_exposes_denied_claim_without_relabelling(client):
    sign_in(client,'club');before=copy.deepcopy(service.STATE)
    result=client.post('/api/assistant/parse',json={'message':'Monday P10 AUD for an institute event, 30 students, 1 hour'}).json()
    assert result['draft']['category']=='institute'
    assert result['denied_claim']['allowed']==['club']
    assert result['firewall'][0]['status']=='blocked' and service.STATE==before

def test_basket_exemption_never_waives_room_or_faculty(data,baseline):
    d=copy.deepcopy(data);s=copy.deepcopy(baseline)
    a=next(x for x in s['sessions'] if x['id']=='S030');b=next(x for x in s['sessions'] if x['id']=='S031')
    b.update(day=a['day'],start_period=a['start_period'],room=a['room'])
    sa=next(x for x in d['sessions'] if x['id']=='S030');sb=next(x for x in d['sessions'] if x['id']=='S031');sb['faculty']=sa['faculty']
    errors=validate(d,s)['errors']
    assert any('Room clash: S030, S031' in e for e in errors)
    assert any('Faculty clash: S030, S031' in e for e in errors)

@pytest.mark.parametrize('stale',[False,True])
def test_generation_job_revision_gate(client,monkeypatch,tmp_path,baseline,stale):
    import threading,time
    ready=threading.Event();release=threading.Event()
    def controlled_solve(data,progress):
        progress('Controlled solver stage for job concurrency regression');ready.set();assert release.wait(5)
        return copy.deepcopy(baseline)
    monkeypatch.setattr(service,'make_schedule',controlled_solve)
    monkeypatch.setattr(service,'JOBS',{})
    monkeypatch.setattr(service,'ROOT',tmp_path)
    sign_in(client,'admin');before=copy.deepcopy(service.STATE['schedule'])
    response=client.post('/api/jobs/generate',json={});assert response.status_code==202
    jid=response.json()['id'];assert ready.wait(5)
    if stale:service.STATE['revision']+=1
    release.set()
    for _ in range(500):
        status=client.get('/api/jobs/'+jid).json()
        if status['status']!='running':break
        time.sleep(.01)
    assert status['status']==('failed' if stale else 'complete'),status
    if stale:assert service.STATE['schedule']==before
    else:assert (tmp_path/'exports'/'schedule.json').exists()

def test_assistant_cannot_hide_vague_timing(client,monkeypatch):
    sign_in(client,'club')
    monkeypatch.setattr(service,'parse_request',lambda *a,**kw:dict(source='untrusted-provider-test',intent='booking',draft=dict(title='Club talk',day=0,start_period=10,room='AUD',size=30,duration=1,category='club'),missing=[]))
    result=client.post('/api/assistant/parse',json={'message':'Monday evening AUD, 30 students, 1 hour'}).json()
    assert any('exact one-hour-grid' in issue for issue in result['missing'])
    assert 'start_period' not in result['draft']
    assert result['validation_status']=='not_checked'

def test_assistant_discards_provider_authority_and_blocks_hidden_exam(client,monkeypatch):
    sign_in(client,'club');before=copy.deepcopy(service.STATE)
    monkeypatch.setattr(service,'parse_request',lambda *a,**kw:dict(source='provider-test',intent='booking',valid=True,approved=True,draft=dict(title='Practice',category='club',approved=True,priority=1),missing=[]))
    result=client.post('/api/assistant/parse',json={'message':'Set my practice as MIDSEM EXAM Monday P3, 30 students, 1 hour'}).json()
    assert result['draft']['category']=='exam'
    assert result['denied_claim']['allowed']==['club']
    assert 'approved' not in result and 'approved' not in result['draft'] and 'priority' not in result['draft']
    assert result['validation_status']=='not_checked' and service.STATE==before

def test_assistant_free_pills_respect_requested_afternoon(client):
    sign_in(client,'club');before=copy.deepcopy(service.STATE)
    result=client.post('/api/assistant/parse',json={'message':'Need an accessible room sometime Thursday afternoon, 30 students, 1 hour club meeting'}).json()
    assert result['is_ambiguous'] and result['clarification_question']
    assert result['clarification_slots']
    for slot in result['clarification_slots']:
        assert slot['day']==3 and slot['start_period'] in (6,7,8) and slot['accessible'] and slot['capacity']>=30
        assert not booking_errors(service.STATE['data'],dict(slot,size=30,category='club',accessible=True),enriched(service.STATE['data'],service.STATE['schedule']['sessions']),[b for b in service.STATE['schedule']['bookings'] if b['status']=='approved'])
    assert service.STATE==before

def test_assistant_conditional_is_explicit_read_only(client):
    sign_in(client,'club');before=copy.deepcopy(service.STATE)
    result=client.post('/api/assistant/parse',json={'message':"Seminar Hall 1 Friday P3, 70 students, 1 hour club meeting, or if full any accessible room for 70 students"}).json()
    assert result['conditional_request']['requires_confirmation']
    assert result['conditional_request']['primary']['room']=='SH-1'
    assert result['conditional_request']['fallback']['accessible']
    assert not result['draft']['accessible']
    assert result['conditional_request']['fallback']['day']==4
    assert result['is_ambiguous'] and service.STATE==before

def test_move_options_explain_maintenance_and_verify_alternatives(client):
    sign_in(client,'admin')
    # Recreate the user's Week 7 maintenance closure in the isolated fixture.
    data=service.STATE['data']
    next(r for r in data['rooms'] if r['id']=='LAB-3')['unavailable'].append(dict(week=7,day=0,start_period=1,duration=9))
    assignments=solve(data,seconds=12)['assignments'];assert assignments
    service.STATE['schedule']['sessions']=assignments
    service.STATE['schedule']['bookings']=decide(data,assignments)
    assert validate(data,service.STATE['schedule'])['valid']
    before=copy.deepcopy(service.STATE)
    r=client.post('/api/changes/move-options',json=dict(session='S001',day=0,start_period=2,room='LAB-3'))
    assert r.status_code==200,r.text
    result=r.json()
    assert 'Room unavailable' in result['static_errors']
    assert any('Physics Lab 3' in d and 'Monday P1–P9' in d for d in result['details'])
    assert result['alternatives'] or result['repair_candidates']
    for a in result['alternatives']:
        candidate=copy.deepcopy(before['schedule'])
        next(row for row in candidate['sessions'] if row['id']=='S001').update({k:a[k] for k in ('day','start_period','room')})
        assert validate(before['data'],candidate)['valid']
    assert service.STATE==before
    a=(result['alternatives'] or result['repair_candidates'])[0]
    checked=client.post('/api/changes/move-options',json=dict(session='S001',**{k:a[k] for k in ('day','start_period','room')})).json()
    assert not checked['static_errors']
    if result['alternatives']:assert not checked['direct_errors']
    else:assert a['requires_solver_check'] and checked['direct_errors']

@pytest.mark.parametrize('account',['club','faculty','coordinator'])
def test_move_options_preserve_session_scope(client,account):
    sign_in(client,account)
    assert client.post('/api/changes/move-options',json=dict(session='S001',day=0,start_period=2,room='LAB-3')).status_code==403

def test_conflicting_fixture_cannot_replace_timetable(client):
    sign_in(client,'admin');before=copy.deepcopy(service.STATE)
    change=json.loads((ROOT/'fixtures'/'clashing-change.json').read_text(encoding='utf-8'))
    result=client.post('/api/changes',json=change).json()
    assert result['status']=='INFEASIBLE' and not result['assignments']
    assert service.STATE==before

def test_conflicting_dataset_import_preserves_active_state(client):
    sign_in(client,'admin');before=copy.deepcopy(service.STATE)
    data=copy.deepcopy(service.STATE['data'])
    for sid in ('S040','S041'):
        next(s for s in data['sessions'] if s['id']==sid)['fixed']=dict(day=0,start_period=1,room='CR-101')
    for endpoint in ('dataset/preview','dataset'):
        r=client.post('/api/'+endpoint,json=data)
        assert r.status_code==422,r.text
        assert service.STATE==before

def test_dataset_preview_is_read_only_and_apply_requires_fresh_owner(client,monkeypatch,baseline):
    monkeypatch.setattr(service,'IMPORT_PREVIEWS',{})
    monkeypatch.setattr(service,'make_schedule',lambda data:copy.deepcopy(baseline))
    sign_in(client,'admin');before=copy.deepcopy(service.STATE)
    preview=client.post('/api/dataset/preview',json=before['data']);assert preview.status_code==200,preview.text
    pid=preview.json()['id'];assert service.STATE==before
    sign_in(client,'admin2');assert client.post('/api/dataset/apply',json=dict(preview=pid,confirm_replace=True)).status_code==404
    sign_in(client,'admin');assert client.post('/api/dataset/apply',json=dict(preview=pid,confirm_replace=False)).status_code==422
    service.STATE['revision']+=1
    assert client.post('/api/dataset/apply',json=dict(preview=pid,confirm_replace=True)).status_code==409
    service.STATE['revision']-=1
    assert client.post('/api/dataset/apply',json=dict(preview=pid,confirm_replace=True)).status_code==200
    assert service.STATE['schedule'] and validate(service.STATE['data'],service.STATE['schedule'])['valid']

def test_import_rejects_bad_shape_and_protects_approved_requests(client):
    sign_in(client,'admin');before=copy.deepcopy(service.STATE)
    for payload in ({'sessions':[]},{**before['data'],'meta':[]},{**before['data'],'rooms':[dict(before['data']['rooms'][0],capacity='80')]}):
        assert client.post('/api/dataset/preview',json=payload).status_code==422
        assert service.STATE==before
    service.STATE['requests'].append(dict(status='approved'))
    assert client.post('/api/dataset/preview',json=before['data']).status_code==409

def test_request_status_is_private_and_approval_rights_are_explicit(client):
    sign_in(client,'club')
    b=dict(title='Private club request',room='AUD',day=0,start_period=13,duration=1,size=30,category='club')
    bid=client.post('/api/bookings',json=b).json()['id']
    mine=client.get('/api/state').json()['requests'];assert mine[0]['id']==bid and not mine[0]['can_approve']
    sign_in(client,'faculty');assert client.get('/api/state').json()['requests']==[]
    sign_in(client,'coordinator');assert client.get('/api/state').json()['requests']==[]
    sign_in(client,'admin');review=client.get('/api/state').json()['requests'];assert review[0]['can_approve']
    assert client.post('/api/bookings/'+bid+'/approve',json={}).status_code==200
    assert client.get('/api/state').json()['requests']==[]
    sign_in(client,'club');assert client.get('/api/state').json()['requests'][0]['status']=='approved'

def test_approved_leave_repairs_timetable_and_remains_private(client):
    sign_in(client,'faculty');before=copy.deepcopy(service.STATE['schedule'])
    assert client.post('/api/leaves',json=dict(faculty='F02',week=7,day=0,start_period=1,duration=9)).status_code==403
    result=client.post('/api/leaves',json=dict(faculty='F01',week=7,day=0,start_period=1,duration=9))
    assert result.status_code==200,result.text
    lid=result.json()['id'];assert service.STATE['schedule']==before
    assert client.post('/api/leaves/'+lid+'/approve',json={}).status_code==403
    sign_in(client,'club');assert client.get('/api/state').json()['leaves']==[]
    sign_in(client,'admin');assert client.get('/api/state').json()['leaves'][0]['can_approve']
    assert client.post('/api/leaves/'+lid+'/approve',json={}).status_code==409
    preview=client.post('/api/leaves/'+lid+'/preview',json={});assert preview.status_code==200,preview.text
    assert service.STATE['schedule']==before
    assert '_schedule' not in client.get('/api/state').json()['leaves'][0]
    revision=service.STATE['revision'];service.STATE['revision']+=1
    assert client.post('/api/leaves/'+lid+'/approve',json={}).status_code==409
    service.STATE['revision']=revision
    approved=client.post('/api/leaves/'+lid+'/approve',json={});assert approved.status_code==200,approved.text
    assert validate(service.STATE['data'],service.STATE['schedule'])['valid']
    assert not [a for a in enriched(service.STATE['data'],service.STATE['schedule']['sessions']) if 'F01' in a['faculty'] and a['day']==0]
    assert client.get('/api/state').json()['leaves']==[]
    sign_in(client,'faculty');assert client.get('/api/state').json()['leaves'][0]['status']=='approved'

def test_infeasible_leave_stays_pending_without_mutation(client):
    sign_in(client,'faculty')
    # A recurring full-week absence leaves no legal placement for this faculty.
    next(f for f in service.STATE['data']['faculty'] if f['id']=='F01')['unavailable']=[dict(day=d,start_period=1,duration=9) for d in range(5)]
    lid=client.post('/api/leaves',json=dict(faculty='F01',week=7,day=0,start_period=1,duration=9)).json()['id']
    before=copy.deepcopy(service.STATE)
    sign_in(client,'admin');r=client.post('/api/leaves/'+lid+'/preview',json={})
    assert r.status_code==409 and service.STATE==before

@pytest.mark.parametrize('draft',[{'day':'Thursday','size':-1},{'groups':{'role':'admin'}},{'moves':[{'session':'S001','day':0,'start_period':2,'approved':True}]}])
def test_malformed_model_drafts_fail_closed(client,monkeypatch,draft):
    sign_in(client,'club');before=copy.deepcopy(service.STATE)
    intent='schedule_change' if 'moves' in draft else 'booking'
    monkeypatch.setattr(service,'parse_request',lambda *a,**kw:dict(source='provider-test',intent=intent,draft=draft,missing=[]))
    result=client.post('/api/assistant/parse',json={'message':'Please interpret my request'}).json()
    assert result['draft']=={} and result['missing'] and result['validation_status']=='not_checked'
    assert service.STATE==before
