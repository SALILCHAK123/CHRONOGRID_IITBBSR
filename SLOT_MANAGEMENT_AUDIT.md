# Slot management verification — 2026-10-31

Result: no scheduling-enforcement mismatch found in the audited state (revision 20). Fixed misleading timetable presentation. No live bookings, proposals or timetable assignments were changed by the verification.

## Coverage and evidence

| Check | Result |
| --- | --- |
| Independent audit of all 14 hard constraints | Pass; 190 teaching sessions, 244 teaching hours, 41 exams, 10 approved bookings, zero hard violations |
| All 27 rooms × 5 weekdays × every bounded P1–P13 start/duration window × capacity boundary/boundary+1 | 24,570 comparisons with an independent set-based occupancy oracle; zero mismatches |
| Room discovery, duration 1/2/3, accessible classroom, mandatory group, each weekday/start | 180 queries; exact result sets and other-time suggestions matched the oracle |
| Solver domain vs independent validator, representative session/exam types, duration, accessibility and fixed status | 19,440 placement comparisons; zero mismatches |
| Full isolated regression suite | 98 passed in 42.67s; one existing Starlette/httpx deprecation warning |
| Actual frontend renderer with isolated daytime/evening booking fixtures | Pass: correct academic placement, P9–P10 continuation, no false Week 8 closure, faculty leave, group view, column alignment, club edit restriction |
| Browser, all five identities × room/faculty/group filters | All 15 views passed; nine Monday LAB-3 closure cells and ten F01 leave cells consistently displayed; Club edit disabled |
| Browser, 390 × 844 | Document width 385px; timetable scrolls within its 353px container; no page overflow; viewport override reset |
| Browser error logs | Empty |

Regression coverage includes lunch endpoints (P5 and P6 independently allowed, crossing blocked), three-hour labs only P2/P6, academic P1–P9 and event P1–P13 bounds, room/faculty/group collisions, combined groups and elective baskets, capacity/accessibility/type matching, half-capacity Week 8 exams, week-scoped/recurring unavailability, faculty daily limits, approved venue reservations, cancellation, competing pending approvals, fixed slots, scoped editing, minimum-change proposals, self-approval rejection and stale revision rejection.

## Defects corrected

1. Room closures and faculty leave could appear as “Free Slot.” Resource views now show **Unavailable**, while an ordinary empty room cell says **Unoccupied** and an empty group/faculty cell says **No session**. A visible note explains that an empty filtered cell is not proof that a proposed placement satisfies every constraint.
2. Approved daytime venue bookings were only listed in the evening area. They now occupy their actual academic cells, span their duration, and continue into the evening summary when crossing P9–P10. Row alignment retains the protected lunch column. Pure daytime events are not duplicated in the evening summary.
3. The secondary timetable edit button remained enabled for Club accounts even though the editor rejected them. It is now disabled consistently.
4. Legacy counter-offers lacking capacity metadata no longer display a blank “seats” value.

Availability results, move checks and approval continue to use server-side validation. “Needs solver repair” candidates remain explicitly unverified for whole-timetable feasibility. No role, priority or scheduling rule was relaxed.

## Reproduce

```powershell
.venv/Scripts/python.exe scripts/audit_slot_management.py
.venv/Scripts/python.exe -m pytest -q
node scripts/verify_slot_rendering.cjs
```

Evidence: `evidence/slot-management-audit.json`, `evidence/slot-management-test-results.txt`, `evidence/slot-rendering-test-results.txt`, `evidence/slot-role-browser-checks.json`, `evidence/slot-maintenance-grid-desktop.png`, `evidence/slot-maintenance-grid-mobile.png`.

This verifies the local synthetic dataset and implementation. The official starter pack and official validator were not supplied; no claim of official judge certification is made.
