"""Read-only demonstration: deliberately clashing files never touch active state."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.constraints import validate,booking_errors,enriched
from backend.bookings import alternatives

raw=(ROOT/'runtime/state.json').read_bytes();state=json.loads(raw)
schedule=json.loads((ROOT/'fixtures/timetable-with-clash.json').read_text(encoding='utf-8'))
booking=json.loads((ROOT/'fixtures/clashing-booking.json').read_text(encoding='utf-8'))
report=validate(state['data'],schedule)
errors=booking_errors(state['data'],booking,enriched(state['data'],state['schedule']['sessions']),[b for b in state['schedule']['bookings'] if b['status']=='approved'])
offers=alternatives(state['data'],booking,enriched(state['data'],state['schedule']['sessions']),[b for b in state['schedule']['bookings'] if b['status']=='approved'])
result=dict(timetable_rejected=not report['valid'],timetable_errors=report['errors'],booking_rejected=bool(errors),booking_errors=errors,booking_alternatives=offers,active_file_unchanged=(ROOT/'runtime/state.json').read_bytes()==raw)
print(json.dumps(result,indent=2));assert result['timetable_rejected'] and result['booking_rejected'] and result['active_file_unchanged']
