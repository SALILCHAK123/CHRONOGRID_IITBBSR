"""Focused audit of the user's fourteen-rule checklist, with isolated fixtures."""
import copy
import pytest
from backend.constraints import validate, placement_errors, enriched, booking_errors
from backend.solver import solve, domain_issues


def fixture():
    rooms=[dict(id=rid,name=rid,type=kind,capacity=cap,accessible=access,unavailable=[])
           for rid,kind,cap,access in [('R1','classroom',100,False),('R2','classroom',100,True),('L1','computer_lab',100,True)]]
    sessions=[dict(id=sid,course=sid,faculty=[fid],groups=[gid],size=40,duration=1,kind='lecture',room_type='classroom',accessible=False,department='CSE',basket=None,fixed=dict(day=0,start_period=p,room=rid))
              for sid,fid,gid,p,rid in [('A','F1','G1',1,'R1'),('B','F2','G2',2,'R2')]]
    data=dict(rooms=rooms,faculty=[dict(id=f,name=f,department='CSE',daily_limit=4,unavailable=[],avoid=[]) for f in ['F1','F2']],groups=[dict(id=g,name=g,size=40,department='CSE') for g in ['G1','G2']],sessions=sessions,exams=[],bookings=[],priorities=['exam','class','institute','guest','department','club'])
    schedule=dict(sessions=[dict(id=s['id'],**s['fixed']) for s in sessions],exams=[],bookings=[])
    assert validate(data,schedule)['valid']
    return data,schedule


@pytest.mark.parametrize('rule',range(1,15),ids=lambda n:f'H{n:02}')
def test_each_hard_constraint_is_enforced(rule):
    d,s=fixture();a,b=d['sessions'];aa,bb=s['sessions'];impossible=True
    if rule==1:
        s['sessions']=[aa,aa.copy()];expected='expected exactly one assignment';impossible=False
    elif rule==2:
        b['faculty']=a['faculty'].copy();b['fixed']['start_period']=bb['start_period']=1;expected='Faculty clash'
    elif rule==3:
        # The second constituent group of a combined lecture must also be protected.
        a['groups']=['G1','G2'];b['fixed']['start_period']=bb['start_period']=1;expected='Group clash'
    elif rule==4:
        b['fixed'].update(start_period=1,room='R1');bb.update(b['fixed']);expected='Room clash'
    elif rule==5:
        a['size']=101;expected='Insufficient room capacity'
    elif rule==6:
        a['room_type']='computer_lab';expected='Room type mismatch'
    elif rule==7:
        d['faculty'][0]['unavailable']=[dict(day=0,start_period=1,duration=1)];expected='Faculty F1 unavailable'
    elif rule==8:
        d['rooms'][0]['unavailable']=[dict(day=0,start_period=1,duration=1)];expected='Room unavailable'
    elif rule==9:
        a.update(kind='lab',duration=3,room_type='computer_lab');a['fixed']['room']=aa['room']='L1';expected='Three-hour lab must start'
    elif rule==10:
        a['accessible']=True;expected='Accessible room required'
    elif rule==11:
        a['basket']=b['basket']='ELECTIVE';expected='not synchronised'
    elif rule==12:
        a.update(kind='lab',duration=3,room_type='computer_lab');a['fixed'].update(start_period=2,room='L1');aa.update(a['fixed'])
        b.update(duration=2,faculty=['F1']);b['fixed']['start_period']=bb['start_period']=6;expected='daily limit exceeded'
    elif rule==13:
        reservation=dict(id='BOOK',title='Approved event',day=0,start_period=1,room='R1',duration=1,size=20,category='club',groups=[],status='approved',reason='Audit fixture')
        s['bookings']=[reservation];expected='Room occupied'
    else:
        aa['start_period']=3;expected='Fixed slot changed';impossible=False
        assert 'Fixed slot changed' in domain_issues(d,a,aa,False)
    errors=validate(d,s)['errors']
    assert any(expected in error for error in errors),(rule,errors)
    result=solve(d,reservations=s['bookings'] if rule==13 else None,seconds=1)
    if impossible:
        assert result['status']=='INFEASIBLE' and not result['assignments'],(rule,result)
    else:
        # Solver output restores exactly-once and fixed placements even when supplied rows were forged.
        assert len(result['assignments'])==2 and {x['id'] for x in result['assignments']}=={'A','B'}
        assert validate(d,dict(sessions=result['assignments'],exams=[],bookings=[]))['valid']


def test_elective_group_exception_and_combined_groups():
    d,s=fixture();a,b=d['sessions'];b['fixed']['start_period']=s['sessions'][1]['start_period']=1
    a['groups']=['G1','G2'];b['groups']=['G2'];a['basket']=b['basket']='ELECTIVE'
    assert validate(d,s)['valid']
    result=solve(d,seconds=1)
    assert result['assignments'] and validate(d,dict(sessions=result['assignments'],exams=[],bookings=[]))['valid']
    # The elective exception only waives a student-group collision.
    s['sessions'][1]['room']='R1';b['fixed']['room']='R1';b['faculty']=['F1']
    errors=validate(d,s)['errors']
    assert any('Room clash' in e for e in errors) and any('Faculty clash' in e for e in errors)


@pytest.mark.parametrize('start,duration,crosses',[(4,2,False),(5,1,False),(6,1,False),(5,2,True),(4,3,True)])
def test_lunch_boundaries(start,duration,crosses):
    d,_=fixture();session=d['sessions'][0];session.update(duration=duration,fixed=None)
    row=dict(day=0,start_period=start,room='R1')
    assert ('Session crosses lunch' in placement_errors(d,session,row))==crosses
    assert ('Session crosses lunch' in domain_issues(d,session,row,False))==crosses


@pytest.mark.parametrize('start',range(1,8))
def test_three_hour_lab_start_windows(start):
    d,_=fixture();session=d['sessions'][0];session.update(kind='lab',duration=3,room_type='computer_lab',fixed=None)
    row=dict(day=0,start_period=start,room='L1')
    assert (not placement_errors(d,session,row))==(start in [2,6])
    assert (not domain_issues(d,session,row,False))==(start in [2,6])


@pytest.mark.parametrize('size,valid',[(50,True),(51,False),(100,False)])
def test_exam_capacity_is_halved_and_rounded_down(size,valid):
    d,_=fixture();d['rooms'][0]['capacity']=101
    exam=copy.deepcopy(d['sessions'][0]);exam.update(id='EXAM',kind='exam',size=size)
    d['exams']=[exam];row=dict(id='EXAM',day=0,start_period=1,room='R1')
    assert (not placement_errors(d,exam,row,True))==valid
    assert (not domain_issues(d,exam,row,True))==valid
    result=solve(d,'exams',seconds=1)
    assert bool(result['assignments'])==valid


@pytest.mark.parametrize('conflict',['session_room','session_mandatory_group','booking_room','booking_mandatory_group'])
def test_approved_booking_conflicts_are_rejected(conflict):
    d,s=fixture()
    event=dict(id='EVENT',title='Event',day=0,start_period=1,room='R1',duration=1,size=20,category='club',groups=[])
    other={**event,'id':'OTHER'}
    if 'mandatory_group' in conflict:event.update(room='R2',groups=['G1']);other['groups']=['G1']
    errors=booking_errors(d,event,enriched(d,s['sessions']) if conflict.startswith('session') else [],[other] if conflict.startswith('booking') else [])
    assert any(('Mandatory group occupied' if 'mandatory_group' in conflict else 'Room occupied') in e for e in errors),errors


def test_read_only_audit_checks_recurring_null_week_closures():
    from scripts.audit_hard_constraints import audit
    d,s=fixture()
    d['rooms'][0]['unavailable']=[dict(week=None,day=0,start_period=1,duration=1)]
    result=audit(dict(data=d,schedule=s,revision=0))
    assert not result['passed']
    assert next(r for r in result['rules'] if r['id']=='H08')['findings']==['A']
