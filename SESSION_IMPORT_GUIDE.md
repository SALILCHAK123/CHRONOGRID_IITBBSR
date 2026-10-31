# Session recovery and importing files

Create editable draft no longer redirects the active editor on session expiry. Sign in within the prompt and retry; the message and editable fields are retained for the same account. Sessions survive server restarts for up to 24 hours, and explicit logout revokes them. Refresh once after installing this frontend update so an older tab loads the corrected handler.

## Supported files

- JSON only, maximum 5 MB. Excel/CSV/PDF cannot be imported directly.
- **Import change file**: scoped `moves`, `faculty_leave`, `room_closures`, `added_sessions`. This stages a repair for independent approval.
- **Rooms & resources → Import dataset**: complete ChronoGrid data containing rooms, faculty, groups, courses, sessions, exams, bookings and priorities. Review the generated preview before applying an entire-campus replacement. Cancel preserves everything.
- An exported timetable is an output/validator artifact, not a complete campus dataset or a change file.

## Conflicts and resolution

1. Invalid JSON, references or field types: notification explains the issue; correct the file and retry. No changes are applied.
2. Infeasible teaching/exam constraints (for example, two fixed sessions in one room/time): import is rejected. Review details for affected sessions, then correct fixed times, availability, room types/capacity or other source requirements. Use a scoped change if you want to repair the existing timetable.
3. Venue overlaps: the preview lists the occupied room/group, rejected or alternative decision, and verified counter-offers. Choose another room/time or revise attendance/type/accessibility requirements, then preview again. Rejected bookings do not reserve space and cannot displace teaching silently.
4. Existing approved manual bookings/leave: full replacement is blocked; use a change proposal that preserves those commitments.
5. Campus changed while reviewing or preview expired: preview again. Applying a stale result is blocked.

Examples: fixtures/clashing-change.json, fixtures/clashing-booking.json, fixtures/timetable-with-clash.json. Deliberately malformed fixtures are named import-malformed.json and import-unsupported.csv; they exist only to test rejection.

Verification: 109 regression tests passed, plus actual browser checks of session recovery/restart, unsupported/malformed imports, infeasible changes and a cancellable dataset conflict preview. Main live timetable was not replaced during verification.
