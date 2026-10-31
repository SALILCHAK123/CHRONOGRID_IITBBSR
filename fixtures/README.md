# Deliberately clashing examples

These are synthetic test files; they are not replacements for the active campus timetable.

- `clashing-change.json`: import through **Import change file** as an Admin. It forces S040 and S041 into CR-101 on Monday P1. The solver must reject it as infeasible, with no active timetable change.
- `clashing-booking.json`: copy its fields into the manual booking draft, or POST to `/api/bookings/check`. The requested room/mandatory group is already occupied. Expect a rejection with deterministic conflicts and alternatives. Do not treat the file as a dataset import.
- `timetable-with-clash.json`: schedule-shaped copy with two assignments placed in the same room/time. For validator testing only; this is deliberately invalid, not a supported change-file format.

Run `.venv/Scripts/python.exe scripts/verify_clash_fixtures.py` for a read-only demonstration. See `evidence/clashing-fixtures-results.json`. The API regression suite also confirms the incompatible move proposal is infeasible and leaves state unchanged.
