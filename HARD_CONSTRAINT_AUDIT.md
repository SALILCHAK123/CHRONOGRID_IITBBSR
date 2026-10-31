# Hard-constraint audit

Audited the 14 hard constraints in the supplied screenshot against the solver, independent validator, booking checks, and the running website’s active state.

**Result: all 14 pass.** Live revision 15: 190 teaching sessions (244 hours), 41 examinations and 10 approved bookings. The independent validator reports **0 hard violations**. Highest faculty daily load: **4 hours**.

| Rule | Check | Active schedule |
|---|---|---|
| H01 | Exactly one day, start period and room per session | PASS |
| H02 | No simultaneous faculty assignments | PASS |
| H03 | No group clashes; all combined groups count; same-basket exception | PASS |
| H04 | No simultaneous room assignments | PASS |
| H05 | Room capacity; floor(capacity / 2) for examinations | PASS |
| H06 | Required room type matches | PASS |
| H07 | Faculty unavailability respected | PASS |
| H08 | Room unavailability respected | PASS |
| H09 | No lunch crossing; three-hour labs only P2–P4 or P6–P8 | PASS |
| H10 | Accessible sessions receive accessible rooms | PASS |
| H11 | Same-basket sessions share day and start period | PASS |
| H12 | Faculty daily teaching hours stay within their limit | PASS |
| H13 | Approved bookings protect rooms and mandatory groups | PASS |
| H14 | Original fixed slots are preserved | PASS |

## Verification

- Existing full regression: 49 tests passed before additional audit coverage.
- Added 35 focused tests covering the checklist and boundary cases. They include combined-group protection, elective exemptions without waiving room/faculty exclusivity, lunch boundaries, all three-hour lab starts, odd-capacity exam halving, all four approved-booking collision forms, and recurring week-unspecified closures.
- Final complete regression: **84 passed in 31.28s**, including all 35 new audit tests. One existing Starlette/httpx deprecation warning. Output: `evidence/constraint-audit-test-results.txt`.
- Active API state was fetched read-only, independently enumerated against the checklist, and also passed through the existing validator. Evidence: `evidence/live-hard-constraints-audit.json`.
- Saved-state reproducibility: `.venv\Scripts\python.exe scripts/audit_hard_constraints.py`. This reads state and writes a report; it does not change the schedule.
- Enforcement traceability: `CONSTRAINTS.md`. Core code: `backend/constraints.py`, `backend/solver.py`, `backend/models.py`, and the submission/approval handlers in `backend/main.py`.

## Conclusion and scope

No missing enforcement was found for these 14 rules. No timetable, booking, role, or production scheduling logic was changed by this audit. Added test coverage and a read-only audit utility.

The website currently uses synthetic development data. These results certify the local implementation and active local schedule against the supplied checklist, not compatibility with an absent official starter pack or official validator.

Active data/schedule SHA-256: `85db555f531ae563ed21065f0dac474805c57f61d516174a390d8537b93e2cf3`.
Checked at: `2026-10-31T15:30:23.444186+00:00`.
