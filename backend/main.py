import copy, json, os, secrets, threading, uuid, re
import time
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from .models import Booking, AvailabilityQuery, Disruption, Login, PortalLogin, Parse, Move, LeaveRequest, FacultyLeave, check_dataset
from .constraints import validate, booking_errors, enriched, placement_errors
from .solver import solve
from .bookings import decide, alternatives, venue_availability
from .assistant import parse_request, parse_local, guard_interpretation
from .persistence import atomic_json
from .approvals import CATEGORY_ENTITLEMENTS, can_approve_booking
from .errors import booking_findings
from .portals import PORTALS
from . import sessions

ROOT=Path(__file__).resolve().parents[1]
# Vercel functions mount application files read-only; use their writable temporary
# storage while retaining the persistent local runtime directory during development.
RUNTIME=Path('/tmp/chronogrid') if os.getenv('VERCEL') else ROOT/'runtime'
RUNTIME.mkdir(parents=True, exist_ok=True)
DATA=ROOT/'data'/'cit_synthetic.json'; LOCK=threading.RLock(); TOKENS={}; JOBS={}
IMPORT_PREVIEWS={}
ACCOUNTS={
    'admin':dict(id='admin',role='admin',name='Dean · Admin',department='CSE'),
    'admin2':dict(id='admin2',role='admin',name='Deputy Dean · Admin',department='CSE'),
    'coordinator':dict(id='coordinator',role='coordinator',name='CSE Coordinator',department='CSE'),
    'faculty':dict(id='faculty',role='faculty',name='Dr. Mohanty',department='CSE',faculty='F01'),
    'club':dict(id='club',role='club',name='Robotics Club',department='CSE')}

def initial():
    return dict(data=json.loads(DATA.read_text(encoding='utf-8')),schedule=None,proposals=[],requests=[],leaves=[],audit=[],revision=0)

STATE=json.loads((RUNTIME/'state.json').read_text(encoding='utf-8')) if (RUNTIME/'state.json').exists() else initial()
app=FastAPI(title='CIT ChronoGrid',version='0.1.0')

@app.middleware('http')
async def frontend_cache_policy(request,call_next):
    response=await call_next(request)
    if request.url.path=='/' or request.url.path=='/workspace' or request.url.path.startswith(('/static/','/login')):
        response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(HTTPException)
async def application_error(request,exc):
    reason=exc.detail if isinstance(exc.detail,str) else exc.detail.get('message',exc.detail.get('reason','Request blocked')) if isinstance(exc.detail,dict) else 'Invalid request'
    return JSONResponse(status_code=exc.status_code,content=dict(detail=exc.detail,error=dict(code={401:'AUTH_REQUIRED',403:'PERMISSION_DENIED',404:'NOT_FOUND',409:'STATE_CONFLICT',422:'VALIDATION_FAILED'}.get(exc.status_code,'REQUEST_FAILED'),rule_id='AUTHORITY' if exc.status_code in (401,403) else 'REVISION' if exc.status_code==409 else 'INPUT_OR_CONSTRAINT',resource_ids=dict(request.path_params),week=None,day=None,start_period=None,reason=reason)))

def save(action,user):
    STATE['revision']+=1
    STATE['audit'].append(dict(action=action,user=user['id'],time=datetime.now(timezone.utc).isoformat()))
    atomic_json(RUNTIME/'state.json',STATE)

@contextmanager
def transaction():
    with LOCK:
        previous=copy.deepcopy(STATE)
        try:yield
        except Exception:
            STATE.clear();STATE.update(previous)
            raise

def user(request:Request):
    account=session_account(request)
    if not account: raise HTTPException(401,'Sign in to continue')
    return ACCOUNTS[account]

def cookie_name():return os.getenv('AUTH_COOKIE_NAME','chronogrid_session')

def serverless_session_secret():
    return os.getenv('AUTH_SIGNING_SECRET') if os.getenv('VERCEL') else None

def session_account(request):
    token=request.cookies.get(cookie_name()); secret=serverless_session_secret()
    account=sessions.resolve_signed(token,secret) if secret else sessions.resolve(RUNTIME/'sessions.json',token)
    return account if isinstance(account,str) and account in ACCOUNTS else None

def issue_session(account,response):
    secret=serverless_session_secret(); token=sessions.issue_signed(account,secret) if secret else secrets.token_urlsafe(32)
    if not secret:
        with LOCK:sessions.issue(RUNTIME/'sessions.json',token,account)
        TOKENS[token]=account
    response.set_cookie(cookie_name(),token,httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE','false')=='true',max_age=86400)

def admin(u):
    if u['role']!='admin': raise HTTPException(403,'Admin role required')

def active():
    if not STATE['schedule']: raise HTTPException(409,'Generate the timetable first')
    return STATE['schedule']

def validated(data,schedule):
    report=validate(data,schedule)
    if not report['valid']: raise HTTPException(422,dict(message='Deterministic validation blocked this change',report=report))
    return report

def make_schedule(data,progress=lambda stage:None):
    progress('Solving Week 7 teaching constraints')
    sessions=solve(data,seconds=15)
    if not sessions['assignments']: raise HTTPException(422,sessions)
    progress('Solving Week 8 half-capacity exams')
    exams=solve(data,'exams',seconds=5)
    if not exams['assignments']: raise HTTPException(422,exams)
    schedule=dict(meta=dict(synthetic=data.get('meta',{}).get('synthetic',False),schema_version=1,solver='OR-Tools CP-SAT',official_validator_checked=False),sessions=sessions['assignments'],exams=exams['assignments'],bookings=decide(data,sessions['assignments']),solver=dict(sessions={k:v for k,v in sessions.items() if k!='assignments'},exams={k:v for k,v in exams.items() if k!='assignments'}))
    progress('Independently validating classes, exams and booking decisions')
    schedule['report']=validated(data,schedule); return schedule

@app.post('/api/jobs/generate',status_code=202)
def start_generation(u=Depends(user)):
    admin(u)
    with LOCK:
        if any(j['status']=='running' for j in JOBS.values()):raise HTTPException(409,'A generation job is already running')
        if any(r['status']=='approved' for r in STATE['requests']):raise HTTPException(409,'Approved manual bookings are protected. Reset before regeneration.')
        data=copy.deepcopy(STATE['data']);revision=STATE['revision'];jid='J-'+uuid.uuid4().hex[:8]
        JOBS[jid]=dict(id=jid,status='running',stage='Preparing dataset',requester=u['id'])
    def run():
        try:
            schedule=make_schedule(data,lambda stage:JOBS[jid].update(stage=stage))
            with transaction():
                if STATE['revision']!=revision:raise HTTPException(409,'Campus state changed during generation. Run generation again.')
                JOBS[jid]['stage']='Persisting independently validated timetable'
                atomic_json(ROOT/'exports'/'schedule.json',schedule)
                STATE['schedule']=schedule;STATE['proposals']=[];save('generate-job',u)
            JOBS[jid].update(status='complete',stage='Complete',report=schedule['report'])
        except Exception as exc:
            JOBS[jid].update(status='failed',stage='Stopped; active timetable protected',error=exc.detail if isinstance(exc,HTTPException) else 'Generation failed; inspect server logs')
    threading.Thread(target=run,daemon=True).start()
    return dict(id=jid,status='running')

@app.get('/api/jobs/{jid}')
def generation_status(jid:str,u=Depends(user)):
    job=JOBS.get(jid)
    if not job:raise HTTPException(404,'Job not found; jobs expire on server restart')
    if u['role']!='admin' and job['requester']!=u['id']:raise HTTPException(403,'This job belongs to another account')
    return copy.deepcopy(job)

@app.get('/api/health')
def health(): return dict(status='ok',solver='OR-Tools CP-SAT')

@app.get('/api/overview')
def overview():
    with transaction():
        d=STATE['data']
        return dict(synthetic=d.get('meta',{}).get('synthetic',False),rooms=len(d['rooms']),faculty=len(d['faculty']),groups=len(d['groups']),students=sum(g['size'] for g in d['groups']),sessions=len(d['sessions']),hours=sum(s['duration'] for s in d['sessions']),exams=len(d['exams']))

@app.post('/api/demo/login')
def demo_login(body:dict,response:Response):
    if os.getenv('DEMO_MODE','false').lower()!='true':raise HTTPException(403,'One-click role switching is disabled. Sign in with your account.')
    if set(body)!={'username'} or body['username'] not in ACCOUNTS:raise HTTPException(422,'Select a known demo account')
    issue_session(body['username'],response)
    return ACCOUNTS[body['username']]

@app.post('/api/login')
def login(body:Login,response:Response):
    if body.username not in ACCOUNTS or not secrets.compare_digest(body.password,os.getenv('DEMO_PASSWORD','ChronoGrid2026!')): raise HTTPException(401,'Invalid credentials')
    issue_session(body.username,response)
    return ACCOUNTS[body.username]

@app.get('/api/login-portals')
def login_portals():
    return dict(portals=[dict(slug=slug,**portal) for slug,portal in PORTALS.items()],demo_mode=os.getenv('DEMO_MODE','false').lower()=='true')

@app.post('/api/login/{portal}')
def portal_login(portal:str,body:PortalLogin,response:Response):
    config=PORTALS.get(portal)
    if not config:raise HTTPException(404,'Sign-in portal not found')
    account=body.username.strip()
    username_ok=secrets.compare_digest(account.encode(),config['account'].encode()) and account in ACCOUNTS
    password_ok=secrets.compare_digest(body.password.encode(),os.getenv('DEMO_PASSWORD','ChronoGrid2026!').encode())
    if not username_ok or not password_ok:raise HTTPException(401,'Invalid username or password for this role portal')
    issue_session(account,response)
    return dict(user=ACCOUNTS[account],redirect='/workspace')

@app.post('/api/logout')
def logout(request:Request,response:Response):
    token=request.cookies.get(cookie_name())
    if not serverless_session_secret():
        with LOCK:sessions.revoke(RUNTIME/'sessions.json',token)
        TOKENS.pop(token,None)
    response.delete_cookie(cookie_name()); return dict(ok=True)

@app.get('/api/state')
def state(u=Depends(user)):
    with transaction():
        schedule=copy.deepcopy(STATE['schedule'])
        if schedule: schedule['report']=validate(STATE['data'],schedule)
        def booking_right(b):
            room=next((r for r in STATE['data']['rooms'] if r['id']==b['room']),{})
            return b['status']=='pending' and can_approve_booking(u,b,room)
        requests=[{**b,'can_approve':booking_right(b)} for b in STATE['requests'] if b['requester']==u['id'] or booking_right(b)]
        proposals=[{**{k:v for k,v in p.items() if k not in ['data','schedule']},'can_approve':p['status']=='pending' and u['role']=='admin' and p['requester']!=u['id']} for p in STATE['proposals'] if p['requester']==u['id'] or (p['status']=='pending' and u['role']=='admin')]
        leaves=[{**{k:v for k,v in p.items() if not k.startswith('_')},'can_approve':p['status']=='pending' and u['role']=='admin' and p['requester']!=u['id']} for p in STATE.get('leaves',[]) if p['requester']==u['id'] or (p['status']=='pending' and u['role']=='admin')]
        public_data=copy.deepcopy(STATE['data'])
        public_data['bookings']=[b for b in public_data['bookings'] if b.get('requester')==u['id'] or b.get('id') in {x['id'] for x in (schedule or {}).get('bookings',[]) if x['status']=='approved'}]
        if schedule:schedule['bookings']=[b for b in schedule['bookings'] if b['status']=='approved' or b.get('requester')==u['id']]
        return dict(user=u,data=public_data,schedule=schedule,proposals=proposals,requests=requests,leaves=leaves,revision=STATE['revision'],audit=[a for a in STATE['audit'][-30:] if a['user']==u['id']],demo_mode=os.getenv('DEMO_MODE','false').lower()=='true',ai_configured=bool(os.getenv('AI_API_KEY') and os.getenv('AI_MODEL')))

@app.post('/api/generate')
def generate(u=Depends(user)):
    admin(u)
    with transaction():
        if any(r['status']=='approved' for r in STATE['requests']): raise HTTPException(409,'Reset first: regeneration would replace approved manual bookings')
        schedule=make_schedule(STATE['data']); STATE['schedule']=schedule; STATE['proposals']=[]; save('generate',u)
        (ROOT/'exports').mkdir(exist_ok=True); atomic_json(ROOT/'exports'/'schedule.json',schedule)
        return schedule

@app.post('/api/reset')
def reset(u=Depends(user)):
    admin(u)
    with transaction():
        fresh=initial(); fresh['schedule']=make_schedule(fresh['data']);fresh['revision']=STATE['revision'];fresh['audit']=STATE['audit']; STATE.clear(); STATE.update(fresh); save('reset',u)
        return dict(ok=True)

@app.post('/api/dataset')
def dataset(body:dict,u=Depends(user)):
    admin(u)
    try:check_dataset(body)
    except (ValueError,KeyError,TypeError) as e: raise HTTPException(422,str(e))
    # Compatibility endpoint: never erase a working timetable before solving the import.
    with transaction():
        protect_import()
        candidate=make_schedule(body)
        STATE.update(data=body,schedule=candidate,proposals=[],requests=[],leaves=[]); save('import-dataset',u)
    return dict(ok=True,message='Dataset imported and independently validated timetable activated.')

def protect_import():
    if any(r['status']=='approved' for r in STATE['requests']) or any(r['status']=='approved' for r in STATE.get('leaves',[])):
        raise HTTPException(409,'Import would replace approved bookings or leave. Use a change file to repair the existing timetable instead.')

@app.post('/api/dataset/preview')
def preview_dataset(body:dict,u=Depends(user)):
    admin(u)
    try:check_dataset(body)
    except (ValueError,KeyError,TypeError) as error:raise HTTPException(422,str(error))
    with LOCK:protect_import();revision=STATE['revision']
    candidate=make_schedule(body)
    with LOCK:
        if revision!=STATE['revision']:raise HTTPException(409,'Campus data changed during preview. Preview the import again.')
        for key,value in list(IMPORT_PREVIEWS.items()):
            if value['requester']==u['id'] or value['expires']<time.time():IMPORT_PREVIEWS.pop(key,None)
        iid='I-'+uuid.uuid4().hex
        IMPORT_PREVIEWS[iid]=dict(requester=u['id'],revision=revision,data=copy.deepcopy(body),schedule=candidate,expires=time.time()+600)
    return dict(id=iid,revision=revision,rooms=len(body['rooms']),sessions=len(candidate['sessions']),exams=len(candidate['exams']),booking_conflicts=[dict(id=b['id'],title=b['title'],status=b['status'],reason=b['reason'],alternatives=b.get('alternatives',[])) for b in candidate['bookings'] if b['status'] in ('alternative','rejected')],warning='Applying replaces the entire dataset, timetable and pending request queues. Cancel keeps the current campus unchanged.',valid=candidate['report']['valid'])

@app.post('/api/dataset/apply')
def apply_dataset(body:dict,u=Depends(user)):
    admin(u)
    if set(body)!={'preview','confirm_replace'} or body['confirm_replace'] is not True:raise HTTPException(422,'Review and explicitly confirm the replacement preview first')
    with transaction():
        preview=IMPORT_PREVIEWS.get(body['preview'])
        if not preview or preview['requester']!=u['id']:raise HTTPException(404,'Your import preview was not found. Preview the file again.')
        if preview['expires']<time.time() or preview['revision']!=STATE['revision']:raise HTTPException(409,'Import preview expired or campus data changed. Preview again.')
        protect_import();validated(preview['data'],preview['schedule'])
        STATE.update(data=preview['data'],schedule=preview['schedule'],proposals=[],requests=[],leaves=[]);save('import-dataset',u)
        IMPORT_PREVIEWS.pop(body['preview'],None)
    return dict(ok=True)

@app.get('/api/sample-disruption')
def sample(u=Depends(user)):return json.loads((ROOT/'data'/'sample_disruption.json').read_text())

@app.post('/api/priorities')
def priorities(body:dict,u=Depends(user)):
    admin(u)
    if set(body)!={'priorities'}:raise HTTPException(422,'Unknown priority fields')
    order=body.get('priorities',[])
    if len(order)!=6 or set(order)!={'exam','class','institute','guest','department','club'}:raise HTTPException(422,'Provide each of the six priority categories exactly once')
    with transaction():
        # Academic displacement is a separate approved repair; priority edits never silently move classes.
        data=copy.deepcopy(STATE['data']);data['priorities']=order
        schedule=copy.deepcopy(active());decisions=decide(data,schedule['sessions'])
        manual=[b for b in schedule['bookings'] if b['id'].startswith('R-') and b['status']=='approved']
        # Keep already-approved manual reservations protected.
        if manual:raise HTTPException(409,'Reset demo or cancel approved manual bookings before re-ranking the seed requests')
        schedule['bookings']=decisions;schedule['report']=validated(data,schedule)
        STATE['data']=data;STATE['schedule']=schedule;save('edit-priority-order',u);return dict(ok=True)

def category_permission(b,u):
    allowed=CATEGORY_ENTITLEMENTS[u['role']]
    if b['category'] not in allowed: raise HTTPException(403,'Role-priority lock: this account cannot submit that event category. Ask the authorised office.')

def check_booking(b,u):
    category_permission(b,u); schedule=active(); data=STATE['data']
    approved=[x for x in schedule['bookings'] if x['status']=='approved']
    sessions=enriched(data,schedule['sessions'])
    errors=booking_errors(data,b,sessions,approved)
    tests={'Role / category':[], 'Schema / timing': ['Valid day','Event crosses','Positive attendance'], 'Capacity':['Insufficient room'], 'Venue type':['Room type','Select a known'], 'Accessibility':['Accessible room'], 'Maintenance':['Room unavailable'], 'Resource clashes':['Room occupied','Mandatory group','Unknown mandatory']}
    checks=[dict(name=name,status='blocked' if any(any(marker in e for marker in markers) for e in errors) else 'pass') for name,markers in tests.items()]
    return dict(valid=not errors,errors=errors,findings=booking_findings(errors,b),checks=checks,revision=STATE['revision'],alternatives=alternatives(data,b,sessions,approved) if errors else [])

@app.post('/api/bookings/check')
def booking_check(body:Booking,u=Depends(user)):
    with transaction():return check_booking(body.model_dump(),u)

@app.post('/api/venues/availability')
def find_available_venues(body:AvailabilityQuery,u=Depends(user)):
    with transaction():
        if not set(body.groups)<={g['id'] for g in STATE['data']['groups']}:raise HTTPException(422,'Unknown mandatory student group')
        schedule=active()
        result=venue_availability(STATE['data'],body.model_dump(),enriched(STATE['data'],schedule['sessions']),[b for b in schedule['bookings'] if b['status']=='approved'])
        return dict(**result,revision=STATE['revision'])

@app.post('/api/bookings')
def booking_submit(body:Booking,u=Depends(user)):
    with transaction():
        b=body.model_dump(); result=check_booking(b,u)
        if not result['valid']:raise HTTPException(422,result)
        b.update(id='R-'+uuid.uuid4().hex[:8],requester=u['id'],department=u['department'],status='pending',reason='Validated draft submitted; awaiting an authorised independent approver.',alternatives=[])
        STATE['requests'].append(b);save('submit-booking',u);return b

@app.post('/api/bookings/{bid}/cancel')
def booking_cancel(bid:str,u=Depends(user)):
    with transaction():
        b=next((b for b in STATE['requests']+STATE['data']['bookings'] if b['id']==bid),None)
        if not b:raise HTTPException(404,'Request not found')
        if b['requester']!=u['id'] and u['role']!='admin':raise HTTPException(403,'Only the requester or Admin may cancel')
        b['status']='cancelled';b['cancelled']=True;b['reason']='Cancelled by requester or Admin'
        for row in active()['bookings']:
            if row['id']==bid:row.update(status='cancelled',reason=b['reason'])
        active()['report']=validated(STATE['data'],active());save('cancel-booking',u);return dict(ok=True)

@app.post('/api/bookings/{bid}/approve')
def booking_approve(bid:str,u=Depends(user)):
    with transaction():
        b=next((b for b in STATE['requests'] if b['id']==bid),None)
        if not b or b['status']!='pending':raise HTTPException(404,'Pending request not found')
        if b['requester']==u['id']:raise HTTPException(403,'Self-approval is forbidden')
        room=next(r for r in STATE['data']['rooms'] if r['id']==b['room'])
        if not can_approve_booking(u,b,room):raise HTTPException(403,'Admin or the department lab coordinator must approve')
        candidate=copy.deepcopy(active()); approved={**b,'status':'approved','approved_by':u['id'],'reason':'Independently approved after fresh deterministic validation.'};candidate['bookings'].append(approved)
        candidate['report']=validated(STATE['data'],candidate);STATE['schedule']=candidate;b.update(approved);save('approve-booking',u);return approved

@app.post('/api/bookings/{bid}/reject')
def booking_reject(bid:str,body:dict,u=Depends(user)):
    if set(body)!={'reason'}:raise HTTPException(422,'Unknown decision fields')
    with transaction():
        b=next((b for b in STATE['requests'] if b['id']==bid and b['status']=='pending'),None)
        if not b:raise HTTPException(404,'Pending request not found')
        room=next(r for r in STATE['data']['rooms'] if r['id']==b['room'])
        if not can_approve_booking(u,b,room):raise HTTPException(403,'You cannot decide this request')
        if b['requester']==u['id']:raise HTTPException(403,'Cannot decide your own request')
        reason=str(body.get('reason','')).strip()
        if not reason:raise HTTPException(422,'A reason is required')
        b.update(status='rejected',reason=reason);save('reject-booking',u);return b

@app.post('/api/leaves')
def request_leave(body:LeaveRequest,u=Depends(user)):
    with transaction():
        window=FacultyLeave.model_validate(body.model_dump(exclude={'reason'}))
        changed_data(Disruption(faculty_leave=[window]),u)
        request=dict(id='L-'+uuid.uuid4().hex[:8],requester=u['id'],status='pending',**body.model_dump(),message='Leave requested; approval must first produce a valid timetable repair.')
        STATE.setdefault('leaves',[]).append(request);save('request-leave',u)
        return request

@app.post('/api/leaves/{lid}/preview')
def preview_leave(lid:str,u=Depends(user)):
    admin(u)
    with transaction():
        leave=next((p for p in STATE.get('leaves',[]) if p['id']==lid and p['status']=='pending'),None)
        if not leave:raise HTTPException(404,'Pending leave not found')
        if leave['requester']==u['id']:raise HTTPException(403,'Independent review is required')
        window=FacultyLeave.model_validate({k:leave[k] for k in FacultyLeave.model_fields})
        data=changed_data(Disruption(faculty_leave=[window]),ACCOUNTS[leave['requester']]);current=active()
        approved=[b for b in current['bookings'] if b['status']=='approved']
        result=solve(data,baseline=current['sessions'],reservations=approved,seconds=15)
        if not result['assignments']:raise HTTPException(409,dict(message='Leave remains pending: no valid timetable repair was found. Resolve the scheduling conflict before approval.',diagnostics=result.get('diagnostics'),status=result['status']))
        exams=solve(data,'exams',baseline=current['exams'],seconds=5)
        if not exams['assignments']:raise HTTPException(409,'Leave remains pending: the exam calendar could not be repaired.')
        candidate=copy.deepcopy(current);candidate.update(sessions=result['assignments'],exams=exams['assignments'])
        candidate['report']=validated(data,candidate)
        diffs=[]
        for section in ('sessions','exams'):
            old={a['id']:a for a in current[section]}
            diffs.extend(dict(id=a['id'],week=7 if section=='sessions' else 8,before=old[a['id']],after=a) for a in candidate[section] if a!=old[a['id']])
        leave.update(_data=data,_schedule=candidate,preview_revision=STATE['revision']+1,diff=diffs,moved=len(diffs),message='Repair preview ready. Review the before-and-after placements before approval.')
        save('preview-leave',u)
        return {k:v for k,v in leave.items() if not k.startswith('_')}

@app.post('/api/leaves/{lid}/approve')
def approve_leave(lid:str,u=Depends(user)):
    admin(u)
    with transaction():
        leave=next((p for p in STATE.get('leaves',[]) if p['id']==lid and p['status']=='pending'),None)
        if not leave:raise HTTPException(404,'Pending leave not found')
        if leave['requester']==u['id']:raise HTTPException(403,'Self-approval is forbidden')
        if not leave.get('_schedule') or leave.get('preview_revision')!=STATE['revision']:raise HTTPException(409,'Preview a fresh timetable repair and review its diff before approving leave.')
        candidate=leave['_schedule'];data=leave['_data'];candidate['report']=validated(data,candidate)
        STATE.update(data=data,schedule=candidate)
        leave.pop('_data',None);leave.pop('_schedule',None)
        leave.update(status='approved',approved_by=u['id'],message='Leave approved and the repaired timetable is active.')
        save('approve-leave',u)
        return dict(ok=True,request=leave,revision=STATE['revision'])

@app.post('/api/leaves/{lid}/reject')
def reject_leave(lid:str,body:dict,u=Depends(user)):
    admin(u)
    if set(body)!={'reason'} or not isinstance(body.get('reason'),str) or not body['reason'].strip():raise HTTPException(422,'A rejection reason is required')
    with transaction():
        leave=next((p for p in STATE.get('leaves',[]) if p['id']==lid and p['status']=='pending'),None)
        if not leave:raise HTTPException(404,'Pending leave not found')
        if leave['requester']==u['id']:raise HTTPException(403,'Self-decision is forbidden')
        leave.update(status='rejected',message=body['reason'].strip(),decided_by=u['id']);save('reject-leave',u)
        return dict(ok=True)

def changed_data(change,u):
    data=copy.deepcopy(STATE['data']); sessions={s['id']:s for s in data['sessions']}
    if u['role']=='club':raise HTTPException(403,'Club representatives cannot change academic schedules')
    if u['role']!='admin' and change.room_closures:raise HTTPException(403,'Admin must upload room closures')
    for w in change.faculty_leave:
        f=next((f for f in data['faculty'] if f['id']==w.faculty),None)
        if not f:raise HTTPException(422,'Unknown faculty')
        if u['role']=='faculty' and w.faculty!=u.get('faculty'):raise HTTPException(403,'You may only mark your own unavailability')
        if u['role']=='coordinator' and f['department']!=u['department']:raise HTTPException(403,'Faculty is outside your department')
        f.setdefault('unavailable',[]).append(w.model_dump(exclude={'faculty'}))
    for w in change.room_closures:
        r=next((r for r in data['rooms'] if r['id']==w.room),None)
        if not r:raise HTTPException(422,'Unknown room')
        r.setdefault('unavailable',[]).append(w.model_dump(exclude={'room'}))
    for move in change.moves:
        s=sessions.get(move.session)
        if not s:raise HTTPException(422,'Unknown session')
        if s.get('fixed'):raise HTTPException(422,'Original fixed slots cannot be moved')
        if u['role']=='faculty' and u.get('faculty') not in s['faculty']:raise HTTPException(403,'You may only request changes to your own sessions')
        if u['role']=='coordinator' and s['department']!=u['department']:raise HTTPException(403,'Session is outside your department')
        s['fixed']=move.model_dump(exclude={'session'},exclude_none=True)
    for s in change.added_sessions:
        if s.id in sessions:raise HTTPException(422,'Added session ID already exists')
        if s.kind=='exam':raise HTTPException(422,'Added teaching sessions cannot be exams; import an updated exam dataset as Admin')
        if u['role']=='faculty' and (s.faculty!=[u.get('faculty')] or s.department!=u['department']):raise HTTPException(403,'Extra sessions must belong to your faculty identity and department')
        if u['role']=='coordinator' and s.department!=u['department']:raise HTTPException(403,'Extra session is outside your department')
        data['sessions'].append(s.model_dump(exclude_none=True))
    try:check_dataset(data)
    except (ValueError,KeyError,TypeError) as e:raise HTTPException(422,str(e))
    return data

@app.post('/api/changes/move-options')
def move_options(body:Move,u=Depends(user)):
    """Read-only placement checks; alternatives keep every other session unchanged."""
    with transaction():
        changed_data(Disruption(moves=[body]),u)  # Same scope and fixed-slot gate as proposals.
        current=active();data=STATE['data'];session=next(s for s in data['sessions'] if s['id']==body.session)
        old=next(a for a in current['sessions'] if a['id']==body.session)
        requested=dict(id=body.session,day=body.day,start_period=body.start_period,room=body.room or old['room'])
        def check(a):
            candidate={**current,'sessions':[a if row['id']==body.session else row for row in current['sessions']]}
            return validate(data,candidate)['errors']
        static=placement_errors(data,session,requested)
        # Include the actual blocked window instead of aggregate solver exclusion counts.
        details=[]
        room=next((r for r in data['rooms'] if r['id']==requested['room']),None)
        from .constraints import overlap
        occupied={**requested,'duration':session['duration'],'week':7}
        for resource,label in [(room,room['name'] if room else 'Room')]+[(f,f['name']) for f in data['faculty'] if f['id'] in session['faculty']]:
            if resource:
                for w in resource.get('unavailable',[]):
                    if overlap(occupied,w):details.append(f"{label} is unavailable in Week 7 on {['Monday','Tuesday','Wednesday','Thursday','Friday'][w['day']]} P{w['start_period']}–P{w['start_period']+w['duration']-1}.")
        alternatives=[];repair_candidates=[]
        rooms=[r for r in data['rooms'] if r['type']==session['room_type'] and r['capacity']>=session['size'] and (not session.get('accessible') or r['accessible'])]
        candidates=[dict(id=session['id'],day=d,start_period=p,room=r['id']) for d in range(5) for p in range(1,10) for r in rooms]
        candidates.sort(key=lambda a:(a['day']!=body.day,abs(a['day']-body.day),abs(a['start_period']-body.start_period),a['room']!=requested['room']))
        for a in candidates:
            if a==old or a==requested or placement_errors(data,session,a):continue
            errors=check(a);r=next(r for r in rooms if r['id']==a['room'])
            described={**a,'name':r['name'],'capacity':r['capacity'],'duration':session['duration']}
            if not errors:
                alternatives.append(described)
                if len(alternatives)>=6:break
            elif len(repair_candidates)<6:repair_candidates.append({**described,'conflicts':errors,'requires_solver_check':True})
        return dict(revision=STATE['revision'],static_errors=static,details=details,direct_errors=check(requested),alternatives=alternatives,repair_candidates=repair_candidates if not alternatives else [],keeps_other_sessions=True)

@app.post('/api/changes')
def propose(body:Disruption,u=Depends(user)):
    with transaction():
        current=active(); data=changed_data(body,u)
        approved=[b for b in current['bookings'] if b['status']=='approved']
        result=solve(data,baseline=current['sessions'],reservations=approved,seconds=15)
        if not result['assignments']:return result
        candidate=copy.deepcopy(current);candidate['sessions']=result['assignments']
        # A requested move constrains this proposal, not every future repair.
        for move in body.moves:
            next(s for s in data['sessions'] if s['id']==move.session).pop('fixed',None)
        # Explicit week-scoped closures preserve the other calendar.
        exams=solve(data,'exams',baseline=current['exams'],seconds=5)
        if not exams['assignments']:return exams
        candidate['exams']=exams['assignments'];candidate['report']=validated(data,candidate)
        candidate['meta']['rescheduled']=True
        before={a['id']:a for a in current['sessions']}; diff=[dict(id=a['id'],before=before.get(a['id']),after=a) for a in candidate['sessions'] if a!=before.get(a['id'])]
        before_exams={a['id']:a for a in current['exams']}
        exam_diff=[dict(id=a['id'],before=before_exams.get(a['id']),after=a) for a in candidate['exams'] if a!=before_exams.get(a['id'])]
        candidate['solver']=dict(sessions={k:v for k,v in result.items() if k!='assignments'},exams={k:v for k,v in exams.items() if k!='assignments'})
        p=dict(id='P-'+uuid.uuid4().hex[:8],status='pending',requester=u['id'],revision=STATE['revision']+1,data=data,schedule=candidate,diff=diff,exam_diff=exam_diff,exam_moved=sum(x['before'] is not None for x in exam_diff),moved=sum(x['before'] is not None for x in diff),added=sum(x['before'] is None for x in diff),minimum_moves_proven=result.get('minimum_moves_proven'),exam_minimum_moves_proven=exams.get('minimum_moves_proven'),solver_status=result['status'],solver=candidate['solver'],before_report=current['report'],after_report=candidate['report'],change=body.model_dump())
        STATE['proposals'].append(p);save('propose-change',u);return {k:v for k,v in p.items() if k not in ['data','schedule']}

@app.post('/api/changes/{pid}/approve')
def approve_change(pid:str,u=Depends(user)):
    admin(u)
    with transaction():
        p=next((p for p in STATE['proposals'] if p['id']==pid and p['status']=='pending'),None)
        if not p:raise HTTPException(404,'Pending proposal not found')
        if p['requester']==u['id']:raise HTTPException(403,'Self-approval is forbidden; use a second authorised Admin')
        if p['revision']!=STATE['revision']:raise HTTPException(409,'The schedule or requests changed. Generate a fresh proposal before approval.')
        p['schedule']['report']=validated(p['data'],p['schedule']);STATE['data']=p['data'];STATE['schedule']=p['schedule'];p.update(status='approved',approved_by=u['id']);save('approve-change',u)
        (ROOT/'exports').mkdir(exist_ok=True);atomic_json(ROOT/'exports'/'schedule_after.json',active());return dict(ok=True)

@app.post('/api/assistant/parse')
def assistant(body:Parse,u=Depends(user)):
    result=guard_interpretation(parse_request(body.message,STATE['data'],body.outage,actor=u),body.message)
    low=body.message.lower();missing=result.setdefault('missing',[])
    conditional=re.split(r'\b(?:or\s+if|if|unless|agar)\b',body.message,maxsplit=1,flags=re.I)
    if len(conditional)>1 and result.get('intent')=='booking':
        primary=parse_local(conditional[0],STATE['data'],u)['draft']
        fallback=parse_local(conditional[1],STATE['data'],u)['draft']
        fallback={**{k:v for k,v in primary.items() if k in ('day','start_period','duration','size','category')},**fallback}
        if re.search(r'\b(exam|midsem)\b',low):primary['category']='exam';fallback['category']='exam'
        result['conditional_request']=dict(primary=primary,fallback=fallback,condition=conditional[1],requires_confirmation=True)
        result['draft']=primary
    if re.search(r'\b(kal|tomorrow|if|unless|agar|maybe|around|approximately)\b',low):missing.append('Explicitly confirm relative dates, conditions or approximate timing in the draft.')
    if result.get('intent')=='booking':
        if not re.search(r'\b(monday|tuesday|wednesday|thursday|friday)\b',low):
            missing.append('Confirm the intended weekday in Week 7.');result['draft'].pop('day',None)
        if not re.search(r'\bp(?:1[0-3]|[1-9])\b|\b\d{1,2}(?::00)?\s*(?:am|pm|baje)\b',low) or re.search(r':(?:[0-5][1-9]|[1-5]0)\b',low):
            missing.append('Confirm an exact one-hour-grid start period; vague evening or partial-hour times are not assumed.');result['draft'].pop('start_period',None)
        if not re.search(r'\d+\s*(hours?|hrs?|ghant)',low):missing.append('Confirm duration in hours.')
        if not re.search(r'\d+\s*(students|people|attendees|log|bacche)',low):missing.append('Confirm attendance.')
    result['missing']=list(dict.fromkeys(missing))
    # Interpretation is never approval. Strict schemas and permissions apply on submission.
    result['validation_status']='not_checked'
    result['firewall']=[dict(name='Schema',status='not_checked'),dict(name='Timing ambiguity',status='needs_clarification' if result.get('missing') else 'review'),dict(name='Hard constraints',status='not_checked')]
    result['clarification_slots']=[]
    if result.get('intent')=='booking':
        draft=result['draft'];denied=False
        try:category_permission(draft,u)
        except (HTTPException,KeyError):denied=True
        result['firewall'].insert(0,dict(name='Role / category',status='blocked' if denied else 'authorised_draft'))
        if denied:
            allowed=CATEGORY_ENTITLEMENTS[u['role']]
            result['denied_claim']=dict(category=draft.get('category'),reason='Your account cannot request this category. Choose an authorised category explicitly.',allowed=allowed)
        if not denied and STATE['schedule'] and all(draft.get(k) for k in ['size','duration']):
            sessions=enriched(STATE['data'],active()['sessions']);approved=[b for b in active()['bookings'] if b['status']=='approved']
            requested_day=next((i for i,d in enumerate(['monday','tuesday','wednesday','thursday','friday']) if re.search(r'\b'+d+r'\b',low)),None)
            days=[requested_day] if requested_day is not None else range(5)
            periods=[draft['start_period']] if 'start_period' in draft else range(6,9) if re.search(r'afternoon|dopahar',low) else range(10,14) if re.search(r'evening|shaam',low) else range(1,14)
            for day in days:
                for period in periods:
                    try:
                        query=AvailabilityQuery.model_validate({k:v for k,v in {**draft,'day':day,'start_period':period}.items() if k in AvailabilityQuery.model_fields}).model_dump()
                    except ValueError:continue
                    available=venue_availability(STATE['data'],query,sessions,approved)['available_rooms']
                    if draft.get('room'):available=[r for r in available if r['room']==draft['room']]
                    if available:result['clarification_slots'].append(available[0])
                    if len(result['clarification_slots'])>=3:break
                if len(result['clarification_slots'])>=3:break
    result['intent_type']={'booking':'VENUE_BOOKING','schedule_change':'FACULTY_RESCHEDULE'}.get(result.get('intent'))
    result['raw_language']='hinglish' if re.search(r'\b(chahiye|baje|shaam|kal|bhaiya|agar|chhutti)\b',low) else 'en'
    result['is_ambiguous']=bool(result['missing'])
    result['clarification_question']='Please confirm: '+ '; '.join(result['missing']) if result['missing'] else None
    result['draft_payload']=result['draft']
    return result

@app.post('/api/changes/{pid}/reject')
def reject_change(pid:str,body:dict,u=Depends(user)):
    admin(u)
    if set(body)!={'reason'} or not isinstance(body['reason'],str) or not body['reason'].strip():raise HTTPException(422,'A reason is required; unknown fields are forbidden')
    with transaction():
        p=next((p for p in STATE['proposals'] if p['id']==pid and p['status']=='pending'),None)
        if not p:raise HTTPException(404,'Pending proposal not found')
        if p['requester']==u['id']:raise HTTPException(403,'Self-approval or rejection is forbidden')
        p.update(status='rejected',reason=body['reason'].strip(),decided_by=u['id']);save('reject-change',u)
        return dict(ok=True)

@app.get('/api/explain/{sid}')
def explain(sid:str,u=Depends(user)):
    schedule=active(); exam=sid.startswith('E'); key='exams' if exam else 'sessions'
    row=next((a for a in schedule[key] if a['id']==sid),None);s=next((s for s in STATE['data'][key] if s['id']==sid),None)
    if not row or not s:raise HTTPException(404,'Session not found')
    room=next(r for r in STATE['data']['rooms'] if r['id']==row['room'])
    return dict(assignment=row,facts=[f'Room type {room["type"]} matches {s["room_type"]}.',f'Effective capacity {room["capacity"]//(2 if exam else 1)} for {s["size"]} students.','Room, group and faculty collisions checked independently.','Original fixed slot is enforced.' if s.get('fixed') else 'This is a feasible solver choice, not a claim that this slot is uniquely forced.'],checks=placement_errors(STATE['data'],s,row,exam),soft_breakdown=schedule['report']['soft_breakdown'])

@app.get('/api/export')
def export(u=Depends(user)):
    admin(u)
    with transaction():
        schedule=copy.deepcopy(active());schedule['report']=validated(STATE['data'],schedule);return schedule

@app.get('/')
def index():return FileResponse(ROOT/'frontend'/'index.html')

@app.get('/workspace')
def workspace_page(request:Request):
    if not session_account(request):return RedirectResponse('/login',status_code=303)
    return FileResponse(ROOT/'frontend'/'index.html')

@app.get('/login')
def login_picker():return FileResponse(ROOT/'frontend'/'login.html')

@app.get('/login/{portal}')
def portal_page(portal:str):
    if portal not in PORTALS:raise HTTPException(404,'Sign-in portal not found')
    return FileResponse(ROOT/'frontend'/'login.html')
app.mount('/static',StaticFiles(directory=ROOT/'frontend'),name='static')
