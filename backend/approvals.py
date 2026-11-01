"""Server-owned category entitlements, approval authority and priority gates."""
from .constraints import booking_errors, enriched
CATEGORY_ENTITLEMENTS={
    'admin':('institute','guest','department','club'),
    'coordinator':('department',),
    'faculty':(),
    'club':('club',),
}

def approval_route(requester):
    """Return the only Admin identity permitted to decide a request.

    The Dean/Admin account is the normal authority.  The Deputy exists solely
    to independently review work initiated by that primary Admin, which keeps
    self-approval impossible without making the Deputy a second universal
    approver.
    """
    return 'admin2' if requester=='admin' else 'admin'

def can_approve_timetable_change(user,requester):
    return user['role']=='admin' and user['id']!=requester and user['id']==approval_route(requester)

def can_approve_booking(user,booking,room):
    """Admin may decide every independent request; Coordinators decide department labs only."""
    if user['id']==booking['requester']:
        return False
    if user['role']=='admin':
        return can_approve_timetable_change(user,booking['requester'])
    return user['role']=='coordinator' and booking['requester'] not in {'admin','admin2'} and room.get('department')==user['department'] and room['type'].endswith('_lab')

def higher_priority_blocker(data,schedule,requests,booking):
    """Return an unresolved higher-priority request competing for the same resources.

    This makes the published priority order apply when a human approves a
    request, not just when the initial automatic booking decisions are made.
    """
    ranks={category:index for index,category in enumerate(data['priorities'])}
    target_rank=ranks[booking['category']]
    approved=[row for row in schedule['bookings'] if row['status']=='approved']
    sessions=enriched(data,schedule['sessions'])
    for other in requests:
        if other['id']==booking['id'] or other.get('status')!='pending':
            continue
        if ranks.get(other.get('category'),len(ranks))>=target_rank:
            continue
        conflicts=booking_errors(data,booking,sessions,approved+[other])
        if any(marker in issue for issue in conflicts for marker in ('Room occupied','Mandatory group')):
            return other
    return None
