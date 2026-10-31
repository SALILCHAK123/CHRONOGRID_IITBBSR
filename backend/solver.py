"""CP-SAT assignments with independent validation at the service boundary."""
from collections import defaultdict, Counter
from ortools.sat.python import cp_model
from .warmstart import construct

def overlap(a,b):
    if a.get('week') is not None and b.get('week') is not None and a['week']!=b['week']:return False
    return a['day']==b['day'] and bool(set(range(a['start_period'],a['start_period']+a['duration'])) & set(range(b['start_period'],b['start_period']+b['duration'])))

def domain_issues(data,s,a,exam):
    """Solver domain construction; intentionally independent of the export validator."""
    errors=[];p=a['start_period'];d=s['duration'];week=8 if exam else 7
    occupied=set(range(p,p+d));row={**a,'duration':d,'week':week}
    if not occupied<=set(range(1,10)):errors.append('Outside academic periods')
    if 5 in occupied and 6 in occupied:errors.append('Session crosses lunch')
    if s['kind']=='lab' and d==3 and p not in (2,6):errors.append('Three-hour lab must start at P2 or P6')
    room=next((r for r in data['rooms'] if r['id']==a['room']),None)
    if room is None:return errors+['Unknown room']
    capacity=room['capacity']//2 if exam else room['capacity']
    if capacity<s['size']:errors.append('Insufficient room capacity')
    if room['type']!=s['room_type']:errors.append('Room type mismatch')
    if s.get('accessible') and not room['accessible']:errors.append('Accessible room required')
    if any(overlap(row,w) for w in room.get('unavailable',[])):errors.append('Room unavailable')
    for fid in s['faculty']:
        faculty=next((f for f in data['faculty'] if f['id']==fid),None)
        if faculty is None:errors.append('Unknown faculty')
        elif any(overlap(row,w) for w in faculty.get('unavailable',[])):errors.append('Faculty '+fid+' unavailable')
    if any(a[k]!=v for k,v in (s.get('fixed') or {}).items()):errors.append('Fixed slot changed')
    return errors

def solve(data, section='sessions', baseline=None, reservations=None, seconds=20, _diagnose=False):
    model=cp_model.CpModel(); source=data[section]; exam=section=='exams'; active={}; assumption_sessions={}
    rooms=data['rooms']; starts={}; roomvars={}; intervals={}; placements={}; room_intervals=defaultdict(list)
    faculty_intervals=defaultdict(list); group_intervals=defaultdict(list); days={}; baskets={}; choices={}; soft=[]; moved=[]
    baseline={a['id']:a for a in baseline or []}; reservations=reservations or []
    no_domain=[]
    for s in source:
        sid=s['id']; duration=s['duration']; candidates=[]; exclusions=Counter()
        for day in range(5):
            for p in range(1,10):
                for ri,r in enumerate(rooms):
                    a=dict(day=day,start_period=p,room=r['id'])
                    issues=domain_issues(data,s,a,exam)
                    if issues:exclusions.update(issues);continue
                    occupied={**a,'duration':duration,'week':8 if exam else 7}
                    if any(overlap(occupied,b) and (r['id']==b['room'] or set(s['groups'])&set(b.get('groups',[]))) for b in reservations):exclusions['Approved booking reservation']+=1;continue
                    candidates.append((day*13+p-1,ri))
        if not candidates:
            no_domain.append(dict(session=sid,faculty=s['faculty'],groups=s['groups'],room_type=s['room_type'],fixed=s.get('fixed'),reason='No legal slot/room remains. Exclusion counts below are overlapping causes across candidate placements.',excluded_by=dict(exclusions)))
            continue
        start=model.new_int_var_from_domain(cp_model.Domain.from_values(sorted({c[0] for c in candidates})),sid+'_start')
        rv=model.new_int_var_from_domain(cp_model.Domain.from_values(sorted({c[1] for c in candidates})),sid+'_room')
        model.add_allowed_assignments([start,rv],candidates)
        starts[sid]=start; roomvars[sid]=rv; placements[sid]=candidates
        if _diagnose:
            active[sid]=model.new_bool_var(sid+'_required');model.add_assumption(active[sid]);assumption_sessions[active[sid].index]=sid
            interval=model.new_optional_fixed_size_interval_var(start,duration,active[sid],sid)
        else:interval=model.new_fixed_size_interval_var(start,duration,sid)
        intervals[sid]=interval
        for fid in s['faculty']: faculty_intervals[fid].append(interval)
        basket=s.get('basket')
        if basket:
            if basket in baskets: model.add(start==starts[baskets[basket]])
            else: baskets[basket]=sid
        for ri in sorted({c[1] for c in candidates}):
            selected=model.new_bool_var(f'{sid}_r{ri}')
            model.add(rv==ri).only_enforce_if(selected); model.add(rv!=ri).only_enforce_if(selected.Not())
            room_present=selected
            if _diagnose:
                room_present=model.new_bool_var(sid+'_room_present');model.add_min_equality(room_present,[selected,active[sid]])
            room_intervals[ri].append(model.new_optional_fixed_size_interval_var(start,duration,room_present,f'{sid}_room{ri}'))
            if not exam and s['size']<.4*rooms[ri]['capacity']: soft.append(selected)
        # Equality indicators also encode exact soft constraints and daily loads.
        choices[sid]={}
        for t in sorted({c[0] for c in candidates}):
            present=model.new_bool_var(f'{sid}_t{t}'); model.add(start==t).only_enforce_if(present); model.add(start!=t).only_enforce_if(present.Not())
            choices[sid][t]=present
            if not exam:
                if t%13+duration>=9: soft.append(present)
                row=dict(day=t//13,start_period=t%13+1,duration=duration,week=7)
                soft.extend(present for f in data['faculty'] if f['id'] in s['faculty'] and any(overlap(row,w) for w in f.get('avoid',[])))
        for day in range(5):
            onday=model.new_bool_var(f'{sid}_d{day}')
            constraint=model.add(onday==sum(v for t,v in choices[sid].items() if t//13==day))
            if _diagnose:constraint.only_enforce_if(active[sid]);model.add(onday==0).only_enforce_if(active[sid].Not())
            days[sid,day]=onday
        if sid in baseline:
            old=baseline[sid]; matches=[]
            for variable,value in [(start,old['day']*13+old['start_period']-1),(rv,next((i for i,r in enumerate(rooms) if r['id']==old['room']),-1))]:
                eq=model.new_bool_var(sid+'_unchanged_component'); model.add(variable==value).only_enforce_if(eq); model.add(variable!=value).only_enforce_if(eq.Not()); matches.append(eq)
            change=model.new_bool_var(sid+'_moved'); model.add_bool_or([x.Not() for x in matches]).only_enforce_if(change); model.add_bool_and(matches).only_enforce_if(change.Not()); moved.append(change)
    if no_domain: return dict(status='INFEASIBLE',diagnostics=no_domain,assignments=[])
    # A basket consumes one group interval, at the common start and longest duration.
    for g in data['groups']:
        seen=set()
        for s in source:
            if g['id'] not in s['groups']: continue
            basket=s.get('basket')
            if basket:
                if basket in seen: continue
                seen.add(basket)
                members=[x for x in source if x.get('basket')==basket and g['id'] in x['groups']]
                if _diagnose:
                    basket_present=model.new_bool_var(g['id']+basket+'_required');model.add_max_equality(basket_present,[active[x['id']] for x in members])
                    group_intervals[g['id']].append(model.new_optional_fixed_size_interval_var(starts[s['id']],max(x['duration'] for x in members),basket_present,g['id']+basket))
                else:group_intervals[g['id']].append(model.new_fixed_size_interval_var(starts[s['id']],max(x['duration'] for x in members),g['id']+basket))
            else: group_intervals[g['id']].append(intervals[s['id']])
    for collection in [room_intervals,faculty_intervals,group_intervals]:
        for values in collection.values(): model.add_no_overlap(values)
    for f in data['faculty']:
        for day in range(5): model.add(sum(s['duration']*days[s['id'],day] for s in source if f['id'] in s['faculty'])<=f['daily_limit'])
    if not exam:
        for g in data['groups']:
            members=[s for s in source if g['id'] in s['groups']]
            for day in range(5):
                occupied=[]
                for p in range(1,10):
                    terms=[v for s in members for t,v in choices[s['id']].items() if t//13==day and t%13+1<=p<t%13+1+s['duration']]
                    cell=model.new_bool_var(f'{g["id"]}_{day}_{p}'); model.add_max_equality(cell,terms or [0]); occupied.append(cell)
                overload=model.new_int_var(0,9,'overload'); model.add_max_equality(overload,[sum(occupied)-6,0]); soft.append(overload)
                for pi in range(1,8):
                    before=model.new_bool_var('before'); after=model.new_bool_var('after'); gap=model.new_bool_var('gap')
                    model.add_max_equality(before,occupied[:pi]); model.add_max_equality(after,occupied[pi+1:])
                    model.add(gap>=before+after-occupied[pi]-1); soft.append(gap)
                for course in {s['course'] for s in members if s['kind']=='lecture'}:
                    count=sum(days[s['id'],day] for s in members if s['course']==course and s['kind']=='lecture')
                    repeat=model.new_int_var(0,len(members),'repeat'); model.add_max_equality(repeat,[count-1,0]); soft.append(repeat)
    solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=seconds; solver.parameters.num_search_workers=4; solver.parameters.random_seed=17
    def diagnostics(status):
        if status!=cp_model.INFEASIBLE:return ['Time limit reached without a feasible solution; infeasibility is not proven.']
        if not _diagnose:return solve(data,section,reservations=reservations,seconds=5,_diagnose=True).get('diagnostics',['The complete set of required sessions conflicts under the active resource constraints.'])
        core=[assumption_sessions[i] for i in solver.sufficient_assumptions_for_infeasibility() if i in assumption_sessions]
        if not core:core=[s['id'] for s in source]
        affected=[s for s in source if s['id'] in core]
        return [dict(reason='These required sessions cannot all be placed under the active availability, resource exclusivity, basket synchronisation, fixed-slot and daily-load rules. This is a sufficient conflict set, not necessarily minimal.',sessions=core,faculty=sorted({f for s in affected for f in s['faculty']}),groups=sorted({g for s in affected for g in s['groups']}),room_types=sorted({s['room_type'] for s in affected}))]
    hint=construct(data,source,placements) if not baseline else {sid:(a['day']*13+a['start_period']-1,next((i for i,r in enumerate(rooms) if r['id']==a['room']),-1)) for sid,a in baseline.items() if sid in starts}
    for sid,(t,ri) in hint.items():
        if (t,ri) in placements[sid]:
            model.add_hint(starts[sid],t);model.add_hint(roomvars[sid],ri)
            for tt,v in choices[sid].items():model.add_hint(v,int(t==tt))
    solver.parameters.cp_model_presolve=False
    # Lexicographic repair: prove minimum moves before optimising timetable quality.
    primary_status=None; min_moves=None; move_bound=None
    if moved:
        model.minimize(sum(moved)); status=solver.solve(model); primary_status=solver.status_name(status)
        if status not in [cp_model.OPTIMAL,cp_model.FEASIBLE]: return dict(status=primary_status,assignments=[],diagnostics=diagnostics(status))
        min_moves=sum(solver.value(v) for v in moved)
        move_bound=solver.best_objective_bound
        first=[dict(id=s['id'],day=solver.value(starts[s['id']])//13,start_period=solver.value(starts[s['id']])%13+1,room=rooms[solver.value(roomvars[s['id']])]['id']) for s in source]
        model.add(sum(moved)==min_moves)
        model.clear_hints()
        for sid in starts:
            model.add_hint(starts[sid],solver.value(starts[sid]));model.add_hint(roomvars[sid],solver.value(roomvars[sid]))
    model.minimize(sum(soft)); status=solver.solve(model)
    name=solver.status_name(status)
    if status not in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
        if moved: return dict(status=primary_status,assignments=first,moves=min_moves,minimum_moves_proven=primary_status=='OPTIMAL',quality_status=name)
        return dict(status=name,assignments=[],diagnostics=diagnostics(status))
    assignments=[dict(id=s['id'],day=solver.value(starts[s['id']])//13,start_period=solver.value(starts[s['id']])%13+1,room=rooms[solver.value(roomvars[s['id']])]['id']) for s in source]
    return dict(status=name,assignments=assignments,moves=min_moves,minimum_moves_proven=primary_status=='OPTIMAL' if moved else None,move_status=primary_status,move_bound=move_bound,time_budget_per_stage_seconds=seconds,objective=solver.objective_value,best_bound=solver.best_objective_bound)
