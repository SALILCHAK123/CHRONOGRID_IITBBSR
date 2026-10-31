"""Bounded deterministic construction for CP-SAT hints, never a validity authority."""
from collections import defaultdict

def construct(data,source,placements,baseline=None):
    rooms=data['rooms']; faculty={f['id']:f for f in data['faculty']}; groups=defaultdict(list)
    for s in source:groups[s.get('basket') or s['id']].append(s)
    units=sorted(groups.values(),key=lambda ss:(min(len(placements[s['id']]) for s in ss),-max(s['duration'] for s in ss)))
    used_room=defaultdict(set);used_group=defaultdict(set);used_faculty=defaultdict(set);loads=defaultdict(int);hint={};attempts=0
    def visit(index):
        nonlocal attempts
        if index==len(units):return True
        if attempts>30000:return False
        members=units[index];s=members[0];times=set(t for t,r in placements[s['id']])
        for other in members[1:]:times&={t for t,r in placements[other['id']]}
        def score(t):
            day=t//13;p=t%13
            load=sum(len(used_group[g]&set(range(day*13,day*13+9))) for g in s['groups'])
            return (p==8,load>=6,day,p)
        for t in sorted(times,key=score):
            local=[];valid=True
            for m in members:
                occ=set(range(t,t+m['duration']));day=t//13
                if any(occ&used_faculty[f] or loads[f,day]+m['duration']>faculty[f]['daily_limit'] for f in m['faculty']) or any(occ&used_group[g] for g in m['groups']):valid=False;break
                options=[ri for tt,ri in placements[m['id']] if tt==t and not occ&used_room[ri] and not any(ri==rr and occ&oo for mm,rr,oo in local)]
                if not options:valid=False;break
                ri=min(options,key=lambda i:(m['size']<.4*rooms[i]['capacity'],rooms[i]['capacity'],i));local.append((m,ri,occ))
            if not valid:continue
            attempts+=1
            group_add=defaultdict(set)
            for m,ri,occ in local:
                used_room[ri]|=occ
                for f in m['faculty']:used_faculty[f]|=occ;loads[f,t//13]+=m['duration']
                for g in m['groups']:group_add[g]|=occ
                hint[m['id']]=(t,ri)
            for g,occ in group_add.items():used_group[g]|=occ
            if visit(index+1):return True
            for m,ri,occ in local:
                used_room[ri]-=occ
                for f in m['faculty']:used_faculty[f]-=occ;loads[f,t//13]-=m['duration']
                hint.pop(m['id'],None)
            for g,occ in group_add.items():used_group[g]-=occ
        return False
    return hint if visit(0) else {}
