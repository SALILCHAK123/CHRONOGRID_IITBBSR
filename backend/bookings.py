from .constraints import booking_errors, enriched


def venue_availability(data,query,sessions,approved):
    """Read-only room discovery. Booking authority remains enforced on submission."""
    def describe(room,day,period):
        return dict(room=room['id'],name=room['name'],capacity=room['capacity'],room_type=room['type'],accessible=room['accessible'],day=day,start_period=period,duration=query['duration'],spare_seats=room['capacity']-query['size'])
    def available(day,period,room_type):
        return [describe(room,day,period) for room in sorted(data['rooms'],key=lambda r:(r['id']!=query.get('room'),r['capacity'],r['name']))
                if not booking_errors(data,{**query,'day':day,'start_period':period,'room':room['id'],'room_type':room_type},sessions,approved,check_category=False)]
    matching=available(query['day'],query['start_period'],query.get('room_type'))
    other_times=[]
    if not matching:
        for day,period in [(d,p) for d in range(5) for p in range(1,14) if (d,p)!=(query['day'],query['start_period'])]:
            other_times.extend(available(day,period,query.get('room_type')))
            if len(other_times)>=3:
                other_times=other_times[:3];break
    selected_errors=booking_errors(data,query,sessions,approved,check_category=False) if query.get('room') else []
    other_types={}
    if not matching and query.get('room_type'):
        for room in available(query['day'],query['start_period'],None):
            other_types[room['room_type']]=other_types.get(room['room_type'],0)+1
    return dict(available_rooms=matching,other_times=other_times,selected_room_available=bool(query.get('room')) and not selected_errors,selected_room_errors=selected_errors,suggested_room_types=[dict(room_type=key,count=value) for key,value in sorted(other_types.items())])

def alternatives(data,b,sessions,approved,limit=3):
    offers=[]
    slots=[(b['day'],b['start_period'])]+[(d,p) for d in range(5) for p in range(1,14) if (d,p)!=(b['day'],b['start_period'])]
    for day,p in slots:
        for r in sorted(data['rooms'],key=lambda r:(r['id']!=b['room'],r['capacity'])):
            candidate={**b,'day':day,'start_period':p,'room':r['id']}
            if not booking_errors(data,candidate,sessions,approved):
                offers.append({k:candidate[k] for k in ['day','start_period','room']})
                if len(offers)>=limit:return offers
    return offers

def decide(data,rows):
    sessions=enriched(data,rows); decisions=[]; approved=[]
    priorities={v:i for i,v in enumerate(data['priorities'])}
    for b in sorted(data['bookings'],key=lambda b:(priorities[b['category']],b['id'])):
        if b.get('cancelled'):
            decisions.append({**b,'status':'cancelled','reason':'Cancelled by requester; consumes no room capacity.','alternatives':[]}); continue
        errors=booking_errors(data,b,sessions,approved)
        if errors:
            offers=alternatives(data,b,sessions,approved)
            decisions.append({**b,'status':'alternative' if offers else 'rejected','reason':'; '.join(errors)+'. Existing classes and higher-priority accepted requests are protected.','alternatives':offers})
        else:
            decision={**b,'status':'approved','reason':'Passed deterministic room, capacity, availability and mandatory-group checks in priority order.','alternatives':[],'approved_by':'system-policy'}
            decisions.append(decision); approved.append(decision)
    return sorted(decisions,key=lambda b:b['id'])
