# Source-to-implementation traceability

All six PDF pages were read. PDF section 3 (pages 2-3) is the authority for all 14 hard and six soft rules. Sections 4-9 cover roles, data, AI boundaries, submission and eligibility. The reproduced supplemental prompt and binding clarifications are in MASTER_PROMPT_FRONTEND_BACKEND.md.

The solver constructs its own domains in backend/solver.py:domain_issues. backend/constraints.py independently enumerates and checks placements; it imports no solver or assistant code. Solver/validator cannot invoke the LLM. Assignments accept only id/day/start_period/room, so trusted identity, duration and attendance cannot be overridden by exported assignment fields.

## Fourteen hard constraints

| PDF section 3 rule | Schema | CP-SAT enforcement | Independent check | API / UI | Verification (tests/test_platform.py) |
|---|---|---|---|---|---|
| H01 Exactly once | Session.id; assignment tuple | One start/room pair per ID | Missing/duplicate/unknown IDs; extra fields | Generate/export; timetable | scope_and_solver; global_hard_constraints missing/duplicate; validator_rejects_assignment_identity_overrides |
| H02 Faculty exclusivity | Session.faculty | Per-faculty no-overlap | Pairwise faculty intersection | Generate/repair; faculty view | global_hard_constraints faculty; basket_exemption_never_waives_room_or_faculty |
| H03 Group exclusivity; combined/basket rules | groups, basket | Every combined group; shared basket interval | Pairwise groups; same-basket exception only | Group timetable; mandatory groups | global_hard_constraints group; booking_collisions_and_mandatory_groups |
| H04 Room exclusivity | Assignment.room | Selected-room optional intervals | Pairwise room overlap | Room timetable; availability | global_hard_constraints room; basket test |
| H05 Capacity and exam halving | Room.capacity; Session.size | Domain capacity; floor(capacity/2) for exams | Independent capacity calculation | Exam seat badges; booking firewall | local_hard_constraints capacity/exam_capacity |
| H06 Room type | Room.type; Session.room_type | Exact type in candidate domains | Independent type comparison | Venue type field | local_hard_constraints type |
| H07 Faculty unavailable | Faculty.unavailable; Window.week | Week-aware exclusions | Independent window overlap | Leave form; repair | local_hard_constraints faculty_leave; proven_impossible_fixed_slot |
| H08 Room unavailable | Room.unavailable; RoomClosure.week | Week-aware exclusions | Independent maintenance check | Change import; firewall; utilisation | local_hard_constraints maintenance; week_specific_closures_and_utilisation; exam_only_repair_has_separate_diff |
| H09 Lunch and 3-hour labs | kind, duration, periods | Exclude lunch crossing; P2/P6 lab starts | Independent boundary/start checks | Lunch row; exact period labels | local_hard_constraints lunch/lab |
| H10 Accessibility | Room/Session.accessible | Domain filter | Independent accessible-room check | Accessibility checkbox | local_hard_constraints accessibility |
| H11 Elective synchronisation | Session.basket | Equal start across basket | Equal day/start per basket | Elective labels | global_hard_constraints basket; basket room/faculty test |
| H12 Daily faculty hours | daily_limit, duration | Duration-weighted day sum | Independent duration sum | Faculty daily limit label | local_hard_constraints daily_limit |
| H13 Approved reservations / mandatory groups | Booking.room/groups/status/week | Approved reservation exclusions during repair | Fresh booking/session/booking overlaps | Check, pending, approve, cancel, offers | booking_collisions_and_mandatory_groups; concurrent_pending_booking_approval; auth_roles_priority_and_manual_outage |
| H14 Fixed slots | Session.fixed | Exact fixed domain | Equality against original fixed fields | FIXED label; locked moves denied | global_hard_constraints fixed; proven_impossible_fixed_slot |

## Six soft constraints

Unit weights and local multiplicities are provisional. Reports include all components and configured weights, including zeroes. These are penalties, not an official score.

| PDF section 3 rule | Schema | Solver objective | Independent report | API/UI and evidence |
|---|---|---|---|---|
| S01 Faculty avoid | Faculty.avoid | Penalise overlapping selected start | faculty_avoid | Utilisation breakdown; generated solver vs checker |
| S02 Group gaps | Session.groups; occupied periods | Empty period between occupied periods | group_gaps; lunch is not a period | Timetable; export validation |
| S03 More than 6 hours/day | Session.duration/groups | Excess occupied periods over 6 | group_overload; basket alternatives use period union | Breakdown; generated validation |
| S04 Repeated course lecture/day | course/kind/groups | Excess lecture count over one | repeated_lecture | Breakdown; generated validation |
| S05 Less than 40% room use | size; capacity | Penalise selected oversized room | underused_room | Room details; generated validation |
| S06 P9 | start_period/duration | Penalise P9 occupancy | p9 | Canonical timetable; generated validation |

## Authority, persistence and repair

backend/approvals.py owns category entitlements and independent lab approval policy. Server-issued sessions establish identity/department. Unknown mutation fields and identity/status forgery are rejected. Self-approval and self-rejection are blocked. A process lock serializes commits, revision checks block stale proposals, and backend/persistence.py flushes/fsyncs then atomically replaces snapshots. Failed mutations restore prior in-memory state. Tests cover forged fields, stale revisions, competing approvals and storage failure.

AI parsing is read-only and returns editable untrusted drafts, missing information and NOT CHECKED hard constraints. Denied category claims are shown without silent relabelling. Computed slot offers reserve nothing. Manual and AI submission/approval use the same deterministic checks. Provider timeout/quota/malformed tests are injected faults, not live model evidence.

Repairs minimise existing tuple changes, fix the achieved count, then minimise soft penalties. Added sessions do not count as moved. Teaching and exam diffs have separate counts/proof flags/bounds. UNKNOWN/time limit is not INFEASIBLE. Assumption diagnostics are sufficient conflict sets; minimality is never claimed. Generation reports actual server job stages; jobs expire on restart while active/staged state persists.

## Source audit and unresolved inputs

- PDF: about 1,000 students. Synthetic fixture: exactly 980, computed in UI. P9 is 17:00-18:00, with lunch strictly between P5/P6.
- Week 7 teaching/Spectra and Week 8 exams are separate calendars. Null/absent window.week recurs; explicit 7/8 is week-specific. New disruptions default to Week 7.
- Exam domains P1-P9 and rejecting events across lunch are documented development policies pending the official starter documentation. No exam-spacing, invigilator or split-room requirements were invented.
- Official cit_public.json, validator.py, export README/sample and proven-official disruption are absent. Local data/change files are explicitly synthetic. Exact official adapters and scoring cannot be certified without these inputs.
- The separate codex_master_prompt (1).md was absent; its reproduction in the supplied master prompt was used. template.html and reference/cit_chronogrid_platform.html were inspected and retained; their simulations are not evidence.
- The live Oryzo page was inspected in a rendered browser: oversized type, spatial composition and story sequence informed original campus visuals. Assets, code, branding, product claims and testimonials were not copied. The operational workspace follows the specified slate-white, blue, red, amber and emerald theme.
- Existing Git metadata was retained. No public repository, deployment or video was published; event timing/template provenance remain team verification items. No history was rewritten.


## Screenshot checklist audit

The user-provided 14-rule image was audited against solver/validator code and live revision 15. All 14 passed with zero hard violations. `tests/test_hard_constraints_audit.py` adds 35 focused negative/boundary cases. `scripts/audit_hard_constraints.py` performs a separate read-only saved-state enumeration and compares the result with the existing validator. Full report: `HARD_CONSTRAINT_AUDIT.md`; live evidence: `evidence/live-hard-constraints-audit.json`.
