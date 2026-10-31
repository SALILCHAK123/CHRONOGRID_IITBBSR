# Request and timetable workflows — 2026-11-01

| Requested change | Result |
| --- | --- |
| Similar timetable/event files with deliberate clashes | Three synthetic fixtures in `fixtures/`. The schedule produces `Room clash: S040, S041`; the booking produces room and mandatory-group conflicts plus alternative slots. The incompatible change proposal is infeasible and cannot replace the active timetable. |
| Remove resources soft breakdown/current conflicts | Both sections removed from the actual resources renderer. Deterministic validation remains active on the server. |
| Small error notifications | Shared errors use compact notifications, with optional details for long messages. Resource/type conflicts state the specific problem and show compatible room alternatives. No page-top error banner or automatic solver diagnostic modal. |
| Approval controls only for authorised roles | Server sends per-request `can_approve`. Independent Admins review timetable/leave repairs; Admins or the matching department lab coordinator review eligible venue requests. No self-approval controls. |
| Infeasible faculty changes can request leave | Faculty receive an explicit “Request leave instead” action. It opens an editable leave form and does not silently submit leave. Leave can be queued even before a feasible repair exists. |
| Approved leave updates the timetable | Admin first previews a solver repair and reviews its before/after diff. Approval requires a fresh preview and reruns independent validation before atomically updating faculty availability and the active teaching/exam schedule. Infeasible requests remain pending; no invalid timetable is applied. |
| Private request statuses | `/api/state` returns an account's own requests/history, plus actionable pending requests for an authorised reviewer. Completed decisions disappear from other reviewers' queues. Public approved room occupancy remains visible so timetable/availability views work. |
| Administration midsem appearance | Day-by-day exam agenda, day filters, room/hour/seating summaries, physical vs effective seat counts, room/accessibility details and explain controls. Mobile and tablet layouts verified. |
| Campus assistant editable draft | Booking and leave drafts verified through actual browser controls. Added a visible draft summary and “Review editable fields” action, preserved manual outage fallback, removed misleading pass/fail-style parsing panel. No external LLM is configured; the interface honestly identifies the local rule parser. |

## Verification

- Full suite: **102 passed in 48.18s**, one existing Starlette/httpx deprecation warning.
- Additional leave impersonation, internal-preview filtering and stale-preview checks: **1 passed in 22.06s** (60 deselected).
- Browser on isolated port 8004: Faculty entered full-day Monday leave through Campus Assistant → submitted → Admin saw preview control but no approval control → preview computed a one-session repair → reviewed diff → approved → Faculty saw APPROVED and no Monday teaching sessions, with all nine Monday periods marked unavailable. Club saw no leave request or approval controls.
- Main local app: resources sections absent; 41 exams across five day sections, filtering to one day works; coordinator's classroom/physics-lab mismatch shows a small notification and a compatible physics lab, with submission blocked for the mismatched selection.
- Exam agenda contained at 320, 390 and 768px; no browser errors.
- The isolated server used a separate copy and separate persistence directory, and was stopped after QA. Browser verification did not change the main active timetable.

Evidence: `evidence/request-workflows-test-results.txt`, `evidence/leave-additional-guards-test-results.txt`, `evidence/clashing-fixtures-results.json`, `evidence/leave-repair-before-approval.png`, `evidence/leave-approved-private-request.png`, `evidence/exams-agenda-redesign.png`.
