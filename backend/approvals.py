"""Server-owned category entitlements and independent approver policy."""
CATEGORY_ENTITLEMENTS={
    'admin':('institute','guest','department','club'),
    'coordinator':('department',),
    'faculty':(),
    'club':('club',),
}

def can_approve_booking(user,booking,room):
    return user['id']!=booking['requester'] and (user['role']=='admin' or (
        user['role']=='coordinator' and room.get('department')==user['department'] and room['type'].endswith('_lab')))
