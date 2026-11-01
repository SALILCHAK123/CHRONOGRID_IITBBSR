import pytest
from fastapi.testclient import TestClient
import backend.main as service
from backend.approvals import CATEGORY_ENTITLEMENTS, can_approve_booking, can_approve_timetable_change
from backend.portals import PORTALS

@pytest.fixture
def portal_client(monkeypatch):
    monkeypatch.setattr(service,'TOKENS',{})
    monkeypatch.setenv('DEMO_PASSWORD','portal-test-password')
    with TestClient(service.app) as client:
        yield client

@pytest.mark.parametrize('slug',list(PORTALS))
def test_role_portal_binds_identity_and_guards_workspace(portal_client,slug):
    c=portal_client
    assert c.get('/workspace',follow_redirects=False).headers['location']=='/login'
    page=c.get('/login/'+slug)
    assert page.status_code==200
    assert page.headers['cache-control']=='no-store'
    username=PORTALS[slug]['account']
    assert c.post('/api/login/'+slug,json={'username':username,'password':'wrong'}).status_code==401
    assert c.post('/api/login/'+slug,json={'username':username,'password':'गलत पासवर्ड'}).status_code==401
    assert c.post('/api/login/'+slug,json={'password':'portal-test-password'}).status_code==422
    for wrong_user in ('not-a-user','admin2' if username=='admin' else 'admin'):
        assert c.post('/api/login/'+slug,json={'username':wrong_user,'password':'portal-test-password'}).status_code==401
    assert c.post('/api/login/'+slug,json={'username':username,'password':'portal-test-password','role':'admin'}).status_code==422
    result=c.post('/api/login/'+slug,json={'username':' '+username+' ','password':'portal-test-password'})
    assert result.status_code==200
    assert result.json()['user']==service.ACCOUNTS[PORTALS[slug]['account']]
    assert 'HttpOnly' in result.headers['set-cookie']
    assert c.get('/api/state').json()['user']==result.json()['user']
    assert c.get('/workspace').status_code==200
    assert c.post('/api/logout').status_code==200
    assert c.get('/workspace',follow_redirects=False).status_code==303

def test_portal_directory_and_unknown_portals(portal_client):
    c=portal_client
    assert c.get('/login').status_code==200
    assert {p['slug'] for p in c.get('/api/login-portals').json()['portals']}==set(PORTALS)
    assert c.get('/login/unknown').status_code==404
    assert c.post('/api/login/unknown',json={'username':'admin','password':'portal-test-password'}).status_code==404

def test_role_and_priority_policy_matches_submission_rules(portal_client):
    """The four role types follow the published booking authority matrix."""
    assert CATEGORY_ENTITLEMENTS=={
        'admin':('institute','guest','department','club'),
        'coordinator':('department',),
        'faculty':(),
        'club':('club',),
    }
    room=dict(id='LAB-1',department='CSE',type='physics_lab')
    booking=dict(requester='coordinator')
    assert can_approve_booking(service.ACCOUNTS['admin'],booking,room)
    assert not can_approve_booking(service.ACCOUNTS['admin2'],booking,room)
    assert can_approve_timetable_change(service.ACCOUNTS['admin'], 'club')
    assert not can_approve_timetable_change(service.ACCOUNTS['admin2'], 'club')
    assert can_approve_timetable_change(service.ACCOUNTS['admin2'], 'admin')
    assert can_approve_timetable_change(service.ACCOUNTS['admin'], 'admin2')
    assert can_approve_booking(service.ACCOUNTS['coordinator'],dict(requester='club'),room)
    assert not can_approve_booking(service.ACCOUNTS['coordinator'],booking,room)
    assert not can_approve_booking(service.ACCOUNTS['faculty'],booking,room)
    assert portal_client.post('/api/login/department-coordinator',json={'username':'coordinator','password':'portal-test-password'}).status_code==200
    forbidden=dict(title='Guest lecture',room='AUD',day=0,start_period=13,duration=1,size=20,category='guest')
    assert portal_client.post('/api/bookings',json=forbidden).status_code==403

def test_session_survives_memory_reset_but_expiry_and_logout_revoke(portal_client):
    import json
    c=portal_client
    assert c.post('/api/login/admin',json={'username':'admin','password':'portal-test-password'}).status_code==200
    service.TOKENS.clear()
    assert c.get('/workspace',follow_redirects=False).status_code==200
    assert c.post('/api/assistant/parse',json={'message':'Monday P13 CR-101, 30 students, 1 hour club talk'}).status_code==200
    path=service.RUNTIME/'sessions.json';records=json.loads(path.read_text())
    assert c.cookies.get('chronogrid_session') not in path.read_text()
    for record in records.values():record['expires']=0
    path.write_text(json.dumps(records))
    assert c.get('/api/state').status_code==401
    assert c.post('/api/login/admin',json={'username':'admin','password':'portal-test-password'}).status_code==200
    assert c.post('/api/logout').status_code==200
    assert c.get('/api/state').status_code==401
