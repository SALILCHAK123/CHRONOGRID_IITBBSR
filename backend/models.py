from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Window(Strict):
    week:int|None=Field(default=None,ge=7,le=8)
    day:int=Field(ge=0,le=4)
    start_period:int=Field(ge=1,le=13)
    duration:int=Field(ge=1,le=13)
    @model_validator(mode='after')
    def bounds(self):
        if self.start_period+self.duration>14: raise ValueError('Window exceeds P13')
        return self

class Booking(Window):
    week:Literal[7]=7
    title:str=Field(min_length=1,max_length=180)
    room:str
    size:int=Field(ge=1,le=10000)
    category:Literal['institute','guest','department','club']='club'
    room_type:str|None=None
    accessible:bool=False
    groups:list[str]=Field(default_factory=list)

class AvailabilityQuery(Window):
    week:Literal[7]=7
    size:int=Field(ge=1,le=10000)
    room:str|None=None
    room_type:str|None=None
    accessible:bool=False
    groups:list[str]=Field(default_factory=list)

class RoomClosure(Window):
    week:int=Field(default=7,ge=7,le=8)
    room:str
class FacultyLeave(Window):
    week:int=Field(default=7,ge=7,le=8)
    faculty:str
class LeaveRequest(FacultyLeave):
    reason:str=Field(default='',max_length=500)
class Move(Strict):
    session:str
    day:int=Field(ge=0,le=4)
    start_period:int=Field(ge=1,le=9)
    room:str|None=None
class Session(Strict):
    id:str
    course:str
    faculty:list[str]
    groups:list[str]
    size:int=Field(ge=1)
    duration:int=Field(ge=1,le=9)
    kind:Literal['lecture','tutorial','lab','exam']
    room_type:str
    accessible:bool=False
    department:str
    basket:str|None=None
    fixed:dict|None=None
class Disruption(Strict):
    room_closures:list[RoomClosure]=Field(default_factory=list)
    faculty_leave:list[FacultyLeave]=Field(default_factory=list)
    added_sessions:list[Session]=Field(default_factory=list)
    moves:list[Move]=Field(default_factory=list)
class Login(Strict):
    username:str
    password:str
class PortalLogin(Strict):
    username:str=Field(min_length=1,max_length=100)
    password:str=Field(min_length=1,max_length=1024)
class Parse(Strict):
    message:str=Field(min_length=1,max_length=5000)
    outage:bool=False

class BookingDraft(Strict):
    """Partial, untrusted interpretation; never a valid booking by itself."""
    title:str|None=Field(default=None,max_length=180)
    week:Literal[7]|None=None
    day:int|None=Field(default=None,ge=0,le=4)
    start_period:int|None=Field(default=None,ge=1,le=13)
    duration:int|None=Field(default=None,ge=1,le=13)
    room:str|None=None
    size:int|None=Field(default=None,ge=1,le=10000)
    category:Literal['institute','guest','department','club','exam']|None=None
    room_type:str|None=None
    accessible:bool|None=None
    groups:list[str]|None=None

class Room(Strict):
    id:str=Field(min_length=1)
    name:str=Field(min_length=1)
    type:str=Field(min_length=1)
    capacity:int=Field(ge=1,strict=True)
    accessible:bool
    department:str|None=None
    features:list[str]=Field(default_factory=list)
    unavailable:list[Window]=Field(default_factory=list)

class Faculty(Strict):
    id:str=Field(min_length=1)
    name:str=Field(min_length=1)
    department:str
    daily_limit:int=Field(ge=1,strict=True)
    unavailable:list[Window]=Field(default_factory=list)
    avoid:list[Window]=Field(default_factory=list)

class Group(Strict):
    id:str=Field(min_length=1)
    name:str=Field(min_length=1)
    department:str
    size:int=Field(ge=1,strict=True)

class Course(Strict):
    id:str=Field(min_length=1)
    name:str=Field(min_length=1)
    department:str

class SeedBooking(Booking):
    id:str
    requester:str
    department:str
    cancelled:bool=False
    message:str
    status:Literal['cancelled']|None=None
    reason:str|None=None

def check_dataset(data):
    if 'meta' in data and not isinstance(data['meta'],dict):raise ValueError('Dataset meta must be an object')
    if set(data)-{'meta','rooms','faculty','groups','courses','sessions','exams','bookings','priorities'}:raise ValueError('Unknown dataset fields')
    for key in ['rooms','faculty','groups','courses','sessions','exams','bookings','priorities']:
        if key not in data or not isinstance(data[key],list): raise ValueError(f'Missing dataset array: {key}')
    for key in ['rooms','faculty','groups','courses','sessions','exams','bookings']:
        ids=[v['id'] for v in data[key]]
        if len(ids)!=len(set(ids)): raise ValueError(f'Duplicate IDs in {key}')
    known={k:{r['id'] for r in data[k]} for k in ['rooms','faculty','groups','courses']}
    for key,model in [('rooms',Room),('faculty',Faculty),('groups',Group),('courses',Course),('bookings',SeedBooking)]:
        for row in data[key]:model.model_validate(row,strict=True)
    if {s['id'] for s in data['sessions']} & {s['id'] for s in data['exams']}:raise ValueError('Teaching and exam IDs must be distinct')
    for r in data['rooms']:
        if type(r['capacity']) is not int or r['capacity']<1 or not isinstance(r['accessible'],bool) or not r['type']: raise ValueError('Invalid room')
        for w in r.get('unavailable',[]): Window.model_validate(w,strict=True)
    for f in data['faculty']:
        if type(f['daily_limit']) is not int or f['daily_limit']<1: raise ValueError('Invalid faculty daily limit')
        for w in f.get('unavailable',[])+f.get('avoid',[]): Window.model_validate(w,strict=True)
    for section in ['sessions','exams']:
        baskets={}
        for raw in data[section]:
            s=Session.model_validate(raw,strict=True)
            if len(s.groups)!=len(set(s.groups)) or len(s.faculty)!=len(set(s.faculty)):raise ValueError('Duplicate session group or faculty')
            if (section=='exams')!=(s.kind=='exam'):raise ValueError('Session kind does not match calendar')
            if not set(s.faculty)<=known['faculty'] or not set(s.groups)<=known['groups'] or s.course not in known['courses'] or not s.groups: raise ValueError(f'Unknown faculty/group/course in {s.id}')
            if s.size>sum(g['size'] for g in data['groups'] if g['id'] in s.groups):raise ValueError('Session attendance exceeds enrolled groups')
            if s.fixed:
                if not set(s.fixed)<={'day','start_period','room'}: raise ValueError('Unknown fixed-slot field')
                if s.fixed.get('day') not in range(5) or s.fixed.get('start_period') not in range(1,10): raise ValueError('Invalid fixed slot')
                if s.fixed.get('room') and s.fixed['room'] not in known['rooms']: raise ValueError('Unknown fixed room')
            if s.basket:
                if s.basket in baskets and baskets[s.basket]!=s.duration: raise ValueError('Basket members must have equal duration in this schema')
                baskets[s.basket]=s.duration
    if set(data['priorities'])!={'exam','class','institute','guest','department','club'} or len(data['priorities'])!=6: raise ValueError('Priority order must contain each of the six categories once')
    for b in data['bookings']:
        Booking.model_validate({k:v for k,v in b.items() if k in Booking.model_fields})
        if b['room'] not in known['rooms']:raise ValueError('Unknown booking room')
        if not set(b.get('groups',[]))<=known['groups']:raise ValueError('Unknown booking mandatory group')
    return data
