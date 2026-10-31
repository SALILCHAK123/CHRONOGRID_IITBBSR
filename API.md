# API contract and examples

FastAPI serves the frontend and API from the same origin. A server-issued HttpOnly SameSite=Strict cookie is required except for health, overview, login and explicitly enabled demo login. Unknown typed request fields are forbidden. The generated contract is evidence/openapi.json; live documentation is /docs.

| Method and route | Request / result | Authority |
|---|---|---|
| GET /api/health | Engine availability | Public |
| GET /api/overview | Computed loaded dataset totals/provenance | Public |
| POST /api/login | username/password -> server identity + session cookie | Known account |
| POST /api/demo/login | username only -> server identity, only DEMO_MODE=true | Explicit disposable demo |
| POST /api/logout | Expire session cookie/token | Session |
| GET /api/state | Identity, dataset, validated timetable, queue, diff, revision, audit | Session |
| POST /api/dataset | Validated development dataset -> solved active timetable (legacy API) | Admin |
| POST /api/generate | Bounded synchronous solve -> independently validated active baseline | Admin |
| POST /api/jobs/generate | 202 {id,status}; nonblocking generation | Admin |
| GET /api/jobs/{id} | Actual running stage, complete report or failure | Admin/requester |
| POST /api/reset | Restore generated fixture and solve; audit/revision retained | Admin |
| POST /api/assistant/parse | message/outage -> editable untrusted draft, missing fields, firewall, valid timing suggestions | Session; read-only |
| POST /api/bookings/check | Booking -> validity, separate checks, rule findings, revision, alternatives | Entitled category |
| POST /api/bookings | Booking -> pending request with server requester/department | Entitled category |
| POST /api/bookings/{id}/approve | Fresh independent validation -> approved reservation | Other Admin/eligible lab coordinator |
| POST /api/bookings/{id}/reject | {reason} -> rejected request | Other Admin |
| POST /api/bookings/{id}/cancel | Release reservation | Requester/Admin |
| GET /api/sample-disruption | Synthetic local fixture; never labelled official | Session |
| POST /api/changes | Disruption -> staged diff/proof/bounds or INFEASIBLE/UNKNOWN diagnostics | Department/faculty scope; room closure Admin |
| POST /api/changes/{id}/approve | Fresh revision/authority/validation -> atomic active commit | Other Admin |
| POST /api/changes/{id}/reject | {reason} -> recorded rejection | Other Admin |
| POST /api/priorities | {priorities:[six categories]} -> validated seed reranking | Admin |
| GET /api/explain/{id} | Assignment, deterministic placement facts and checks | Session |
| GET /api/export | Independently revalidated active schedule | Admin |

Filtered views use the actual dataset and assignments returned by /api/state. Exams are schedule.exams, decisions schedule.bookings, validation schedule.report, utilisation schedule.report.utilisation, approvals requests/proposals, and audit audit. No separate unused API is promised.

## Example booking

POST /api/bookings/check, followed by /api/bookings after review:

```json
{"week":7,"title":"Robotics study circle","day":0,"start_period":13,"duration":1,"room":"AUD","size":30,"category":"club","room_type":"auditorium","accessible":true,"groups":[]}
```

The checker returns valid, errors, findings, checks, revision and alternatives. Each finding includes code, rule_id, resource_ids, week, day, start_period and reason. Alternatives contain day/start_period/room; accepting one fills an editable draft and reserves nothing. Submission and approval both recheck current constraints.

## Example staged change

```json
{"room_closures":[{"week":8,"room":"LH-1","day":1,"start_period":2,"duration":3}],"faculty_leave":[{"week":7,"faculty":"F01","day":2,"start_period":1,"duration":9}],"added_sessions":[],"moves":[]}
```

Proposal responses include teaching diff/moved/added, exam_diff/exam_moved, both minimum-move proof flags, solver bounds/status/budgets, before/after reports, requester and revision. No active timetable changes before independent approval. A stale revision returns HTTP 409; self-approval returns 403. A failed solver returns INFEASIBLE or UNKNOWN without a proposal ID.

Application errors preserve readable detail and add an error envelope containing code, rule_id, resource_ids, week/day/start_period and reason. HTTP 422 schema errors use FastAPI's field-level detail array. Booking constraint failures additionally include exact deterministic findings and alternatives. Parse results are never validation reports.

## Calendars and durability

Academic assignments use integer day 0-4 and periods 1-9. The sessions section is Week 7; exams is Week 8. Booking.week is exactly 7. Maintenance/leave week=null or absent recurs; disruptions default to week=7. All state/queue/decisions/audit persists to runtime/state.json. Sessions persist as token hashes in runtime/sessions.json with 24-hour expiry and logout revocation. Background jobs and import previews expire on restart. Deployment is one worker with durable runtime/exports volumes.


## Room discovery

`POST /api/venues/availability` is an authenticated, read-only lookup. Body: `week: 7`, `day`, `start_period`, `duration`, `size`, optional preferred `room`, optional `room_type`, `accessible`, and mandatory `groups`. It returns all `available_rooms` at the requested time with room name, capacity, type, accessibility and spare seats. `other_times` is separate and only offered when no same-time room matches. `suggested_room_types` requires an explicit filter change. Looking up rooms grants no booking authority and reserves nothing.

The timetable editor stages targeted `moves` through `POST /api/changes`; it does not regenerate or replace the active timetable. Existing scope, fixed-slot validation and independent approval remain enforced.

`POST /api/assistant/parse` remains read-only. Its filtered native `draft` is also exposed as `draft_payload`, with `intent_type`, `raw_language`, `is_ambiguous` and `clarification_question`. `validation_status` is always `not_checked`. Conditional requests expose separate `primary`/`fallback` drafts and `requires_confirmation`; verified `clarification_slots` use deterministic availability checks within the explicitly requested day/time range. Neither branch or slot suggestion reserves anything.

`POST /api/changes/move-options` accepts a `Move` and enforces the same session scope and fixed-slot restrictions as proposals. It returns immutable availability blockers with actual room/faculty windows, current timetable conflicts and up to six independently validated direct alternatives. If none exist, separate `repair_candidates` pass static availability checks but explicitly require a solver feasibility check; they are not advertised as verified free slots. This endpoint changes no state and stages nothing.

## Private requests and leave approval

`GET /api/state` scopes request/proposal/leave history to the signed-in account, plus pending work that account is authorised to review. Each reviewable item has server-owned `can_approve`. Approved public room occupancy remains shared; private outcomes are shown to the requester. Internal leave preview snapshots are never returned.

- `POST /api/leaves`: `FacultyLeave` window plus optional `reason` (max 500 characters). Scope-checked, queues pending leave without changing the timetable.
- `POST /api/leaves/{id}/preview`: independent Admin only. Computes and validates a minimal repair, stores a revision-bound preview, returns the before/after diff; active timetable unchanged.
- `POST /api/leaves/{id}/approve`: independent Admin only. Requires the fresh preview, validates again, then atomically activates the repaired timetable and faculty availability. Missing/stale/infeasible previews cannot be approved.
- `POST /api/leaves/{id}/reject`: independent Admin with `{ "reason": "..." }`.

An infeasible leave remains pending until a feasible repair can be reviewed. Leave approval is not permission to waive scheduling constraints.

## Role sign-in portals

- `GET /api/login-portals`: public portal metadata and demo-mode flag.
- `POST /api/login/{portal}`: strict `{ "username": "...", "password": "..." }` body. Allowed slugs: admin, deputy-admin, department-coordinator, faculty, club-representative. Checks both credentials and the server-owned portal account assignment; returns user and `/workspace` redirect, sets HttpOnly SameSite=Strict session cookie. Incorrect usernames/passwords or wrong-portal accounts return 401; unknown portals 404; extra fields 422.
- `GET /login` and `GET /login/{portal}`: separate role selection/sign-in pages.
- `GET /workspace`: authenticated university workspace; redirects unauthenticated visitors to `/login` with 303. Frontend pages/assets send `Cache-Control: no-store`.


## Safe dataset import

Prefer `POST /api/dataset/preview` with a complete dataset: it validates strict field types/references, solves both calendars and returns a private ten-minute preview ID, summary and rejected/alternative booking decisions. It changes no active state. `POST /api/dataset/apply` requires `{ "preview": "I-...", "confirm_replace": true }`, the original Admin identity, an unexpired preview and unchanged campus revision. Approval revalidates before atomic activation. Approved manual bookings or leave block dataset replacement; use scoped changes instead. The legacy dataset endpoint also solves before committing so infeasible input cannot erase a working timetable.

The file picker accepts JSON up to 5 MB. Change files accept only moves/faculty_leave/room_closures/added_sessions; exported schedule files are not campus datasets. Unsupported formats, malformed JSON and wrong shapes are rejected without mutation.
