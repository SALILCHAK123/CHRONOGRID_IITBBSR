"""Synthetic development fixture, NOT the organisers' starter pack."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def create():
    branches = ['CSE', 'ECE', 'EE', 'ME', 'CE']
    groups = [{'id': f'Y1-{c}', 'name': f'Year 1 · Section {c}', 'size': 70, 'department': 'COMMON'} for c in 'ABCD']
    groups += [{'id': f'Y{y}-{b}', 'name': f'{b} · Year {y}', 'size': 70, 'department': b} for y in [2, 3] for b in branches]
    rooms = []
    for i in range(12):
        rooms.append(dict(id=f'CR-{101+i}', name=f'Classroom {101+i}', type='classroom', capacity=80 if i < 8 else 160, accessible=i % 3 != 2, features=['projector'], unavailable=[]))
    for i in range(3):
        rooms.append(dict(id=f'LH-{i+1}', name=f'Lecture Hall {i+1}', type='classroom', capacity=200, accessible=True, features=['projector','audio'], unavailable=[]))
    for i, kind in enumerate(['computer','computer','physics','chemistry','electrical','mechanical','civil']):
        rooms.append(dict(id=f'LAB-{i+1}', name=f'{kind.title()} Lab {i+1}', type=f'{kind}_lab', capacity=80, accessible=i != 5, department=['CSE','CSE','COMMON','COMMON','EE','ME','CE'][i], features=['workstations'], unavailable=[]))
    for rid, name, cap, kind in [('AUD','Main Auditorium',500,'auditorium'),('SH-1','Seminar Hall 1',120,'seminar'),('SH-2','Seminar Hall 2',160,'seminar'),('OAT','Open Air Theatre',600,'outdoor'),('SH-3','Seminar Hall 3',100,'seminar')]:
        rooms.append(dict(id=rid,name=name,capacity=cap,type=kind,accessible=True,features=['audio'],unavailable=[]))
    rooms[0]['unavailable']=[dict(day=0,start_period=1,duration=2)]
    faculty=[dict(id=f'F{i+1:02}',name=f'Dr. {("Mohanty","Patnaik","Das","Mishra","Rao")[i%5]} {i+1}',department=branches[i%5],daily_limit=4,unavailable=[dict(day=i%5,start_period=9,duration=1)],avoid=[dict(day=(i+1)%5,start_period=1,duration=1)]) for i in range(40)]
    courses=[dict(id=f'C{i+1:03}',name=['Mathematics','Programming','Circuits','Mechanics','Design','Data Structures','Networks'][i%7]+f' {i+1}',department=branches[i%5]) for i in range(62)]
    sessions=[]
    labtypes=['computer','computer','physics','chemistry','electrical','mechanical','civil']
    for i in range(189):
        lab=i<27
        g=groups[i%14]
        s=dict(id=f'S{i+1:03}',course=courses[i%62]['id'],faculty=[faculty[i%40]['id']],groups=[g['id']],size=g['size'],duration=3 if lab else 1,kind='lab' if lab else ('tutorial' if i%6==0 else 'lecture'),room_type=labtypes[i%7]+'_lab' if lab else 'classroom',accessible=i%11==0,department=g['department'])
        if lab and i%7==5: s['accessible']=False
        sessions.append(s)
    # Exercise combined groups, a fixed slot, and a synchronised elective basket.
    sessions[27]['groups']=[groups[0]['id'],groups[1]['id']]; sessions[27]['size']=140
    sessions[28]['fixed']=dict(day=2,start_period=3)
    for i in [29,30]:
        sessions[i]['basket']='ELECTIVE-A'; sessions[i]['groups']=['Y2-CSE']; sessions[i]['size']=35
    # Subject ownership and faculty are assigned deliberately, rather than by unrelated moduli.
    subjects={
        'COMMON':['Engineering Mathematics','Computational Thinking','Engineering Physics','Engineering Chemistry','Technical Communication','Engineering Drawing','Environmental Studies','Materials Science','Statistics','Applied Mathematics','Physics Practicum','Chemistry Practicum'],
        'CSE':['Programming','Data Structures','Algorithms','Computer Architecture','Operating Systems','Databases','Computer Networks','Software Engineering','Machine Learning','Computer Practicum'],
        'ECE':['Electronic Circuits','Digital Electronics','Signals and Systems','Communication Systems','Microprocessors','VLSI Design','Electromagnetics','Embedded Systems','Instrumentation','Electronics Practicum'],
        'EE':['Circuit Theory','Electrical Machines','Power Systems','Control Systems','Power Electronics','Electrical Measurements','Network Theory','Energy Systems','Digital Control','Electrical Practicum'],
        'ME':['Engineering Mechanics','Thermodynamics','Fluid Mechanics','Machine Design','Manufacturing','Heat Transfer','Dynamics','CAD','Industrial Engineering','Mechanical Practicum'],
        'CE':['Structural Analysis','Surveying','Geotechnical Engineering','Concrete Technology','Transportation','Hydrology','Construction Management','Environmental Engineering','Strength of Materials','Civil Practicum']}
    courses=[]
    for dept,names in subjects.items():
        for name in names:courses.append(dict(id=f'C{len(courses)+1:03}',name=name,department=dept))
    # 10 common faculty and six in each branch, all with four-hour daily limits.
    departments=['CSE']+['COMMON']*10+['CSE']*5+sum(([b]*6 for b in branches[1:]),[])
    for f,dept in zip(faculty,departments):f['department']=dept
    bydept={dept:[c for c in courses if c['department']==dept] for dept in subjects}
    faculty_cursor={dept:0 for dept in subjects};course_cursor={dept:0 for dept in subjects}
    group_index={g['id']:g for g in groups}
    for i,s in enumerate(sessions):
        dept=group_index[s['groups'][0]]['department'];s['department']=dept
        pool=[f for f in faculty if f['department']==dept]
        s['faculty']=[pool[faculty_cursor[dept]%len(pool)]['id']];faculty_cursor[dept]+=1
        if s['kind']=='lab':
            kind={'CSE':'computer','ECE':'electrical','EE':'electrical','ME':'mechanical','CE':'civil'}.get(dept,['physics','chemistry','computer'][i%3])
            s['room_type']=kind+'_lab';s['accessible']=kind!='mechanical' and i%11==0
            course=next((c for c in bydept[dept] if c['name']=={'physics':'Physics Practicum','chemistry':'Chemistry Practicum','computer':'Computational Thinking' if dept=='COMMON' else 'Computer Practicum','electrical':'Electronics Practicum' if dept=='ECE' else 'Electrical Practicum','mechanical':'Mechanical Practicum','civil':'Civil Practicum'}[kind]))
        else:
            course=bydept[dept][course_cursor[dept]%len(bydept[dept])];course_cursor[dept]+=1
        s['course']=course['id']
    exams=[dict(id=f'E{i+1:03}',course=courses[i]['id'],faculty=[],groups=[groups[i%14]['id']],size=70,duration=2,kind='exam',room_type='classroom',accessible=i%7==0,department=groups[i%14]['department']) for i in range(41)]
    for i,e in enumerate(exams):e['course']=bydept[e['department']][i%len(bydept[e['department']])]['id']
    bookings=[]
    categories=['institute','guest','department','club']
    for i in range(25):
        room=rooms[22+i%5]
        bookings.append(dict(id=f'B{i+1:03}',title=['Spectra opening','Guest talk','Department workshop','Club showcase'][i%4]+f' {i+1}',category=categories[i%4],day=i%5,start_period=10+(i//5)%3,duration=2 if i%4==0 else 1,room=room['id'],size=80 if i%6 else 180,room_type=room['type'],accessible=i%5==0,groups=[],requester='club' if i%4==3 else 'coordinator',department='CSE',cancelled=i==24,message=f'{room["name"]} chahiye day {i%5+1}, P{10+(i//5)%3}, {80 if i%6 else 180} students'))
    for i,b in enumerate(bookings):
        b['requester']={'institute':'admin','guest':'coordinator','department':'coordinator','club':'club'}[b['category']]
        day=['Monday','Tuesday','Wednesday','Thursday','Friday'][b['day']]
        b['message']=(f"Please reserve {b['room']} on {day} at P{b['start_period']} for {b['duration']} hours, {b['size']} people for {b['title']}." if i%2==0 else f"{day} ko {b['room']} chahiye P{b['start_period']} se, {b['duration']} ghante, {b['size']} students, {b['title']} ke liye.")
    bookings[3].update(day=bookings[0]['day'],start_period=bookings[0]['start_period'],room=bookings[0]['room'],room_type=bookings[0]['room_type'])
    bookings[3]['message']='Monday AUD chahiye P10 se, 1 ghanta, 80 students, Club showcase ke liye.'
    bookings[2]['groups']=['Y2-CSE']
    return dict(meta=dict(synthetic=True,description='Synthetic CIT development dataset; replace with official starter pack before submission.',schema_version=1,generator='scripts/create_dataset.py',seed=17,teaching_week=7,exam_week=8),rooms=rooms,faculty=faculty,groups=groups,courses=courses,sessions=sessions,exams=exams,bookings=bookings,priorities=['exam','class','institute','guest','department','club'])

if __name__=='__main__':
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'data'/'cit_synthetic.json').write_text(json.dumps(create(),indent=2),encoding='utf-8')
    extra=create()['sessions'][40].copy();extra.update(id='S190',faculty=['F01'],groups=['Y2-CSE'],department='CSE',course='C013',duration=1,kind='tutorial',room_type='classroom',size=70)
    (ROOT/'data'/'sample_disruption.json').write_text(json.dumps({'room_closures':[{'week':7,'room':'LAB-3','day':0,'start_period':1,'duration':9}],'faculty_leave':[{'week':7,'faculty':'F01','day':1,'start_period':1,'duration':9}],'added_sessions':[extra]},indent=2),encoding='utf-8')
