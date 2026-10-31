"""Stable, machine-readable deterministic booking constraint findings."""
RULES=[('Room occupied','H13'),('Mandatory group','H13'),('Insufficient room','H05'),('Room type','H06'),('Room unavailable','H08'),('Event crosses','H09'),('Accessible room','H10'),('category','ROLE_CATEGORY'),('Unknown mandatory','SCHEMA'),('Select a known','SCHEMA')]

def booking_findings(issues,booking):
    return [dict(code='BOOKING_CONSTRAINT',rule_id=next((rule for marker,rule in RULES if marker.lower() in reason.lower()),'TIME_GRID'),resource_ids=[booking.get('room')]+([reason.rsplit(' by ',1)[1]] if ' by ' in reason else []),week=7,day=booking.get('day'),start_period=booking.get('start_period'),reason=reason) for reason in issues]
