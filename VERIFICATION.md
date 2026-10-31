# Development verification

Date: 31 October 2026, Asia/Calcutta. This is local synthetic evidence, not official acceptance or a rubric score.

Story: the browser loads generated campus data, invokes deterministic scheduling/checking, presents editable English/Hinglish drafts and staged diffs, and applies a request only through server authority plus fresh independent validation.

## Final generated artifacts

The actual application API generated exports/schedule.json and exports/schedule_after.json. scripts/generate_exports.py reset the synthetic data, exported the baseline, staged the synthetic leave/closure/added-session disruption, asserted that self-approval returned HTTP 403, signed in as admin2, approved, and exported the result. exports/repair_proposal.json preserves the reviewed diff and proof metadata; exports/dataset_after.json preserves the changed input.

| Artifact | Teaching sessions / hours | Exams | Hard violations | Local soft penalty | Solver |
|---|---|---|---|---|---|
| Baseline | 189 / 243 | 41 | 0 | 0 | OPTIMAL |
| After synthetic change | 190 / 244 | 41 | 0 | 1 | OPTIMAL |

The final exported repair moved two existing teaching sessions, added one session, and moved zero exams. Teaching move optimum was proven with bound 2; exam optimum was proven with bound 0. Both files were rerun through the independent local checker. Scoring is provisional unit weights; the six-component breakdown and weights are embedded in each export.

Baseline utilisation is 243 / 988 eligible available academic room-hours (24.60%). After change it is 244 / 979 (24.92%). The denominator includes teaching-compatible room types in Week 7 P1-P9, subtracts maintenance/closure unions, and excludes event-only venues. Attendance/capacity occupancy is not this metric.

The input is generated synthetic data: 27 rooms including seven labs, 40 faculty, 14 groups, 980 students, 62 courses, 189 initial sessions, 25 seed Spectra requests with exactly one cancellation, and 41 exams. scripts/verify_artifacts.py verified that scripts.create_dataset.create() equals the consumed input, checked both datasets and exports, and recorded SHA-256 hashes in evidence/artifact-verification.json. The CSV mirror was regenerated, checked field-by-field against JSON, and packaged in exports/cit_synthetic_dataset_csv.zip.

## Commands and automated results

```powershell
.venv\Scripts\python.exe scripts/create_dataset.py
.venv\Scripts\python.exe scripts/export_csv.py
.venv\Scripts\python.exe scripts/package_csv.py
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pytest -q -k generation_job_revision_gate
.venv\Scripts\python.exe scripts/generate_exports.py
.venv\Scripts\python.exe scripts/validate_schedule.py data/cit_synthetic.json exports/schedule.json
.venv\Scripts\python.exe scripts/validate_schedule.py exports/dataset_after.json exports/schedule_after.json
.venv\Scripts\python.exe scripts/verify_artifacts.py
node --check frontend/app.js
```

The final complete regression run passed **43 tests in 27.38 seconds**, including background-generation success/stale-commit checks and an independent guard against an untrusted parser hiding vague timing. The non-fatal warning concerns Starlette's deprecated HTTPX test-client integration. The earlier targeted job log is also retained as additional evidence.

Coverage includes all fourteen hard rules; combined/basket resource rules; fixed/lunch/lab bounds; half-capacity exams; actual dataset links; faculty/department scopes; unknown trusted fields; category spoofing; cancellations; competing approvals; stale revisions; zero-key manual operation; injected provider timeout/quota/malformed output; staged repair; independent approval/rejection; explicit week isolation; exam-only diffs; INFEASIBLE diagnostics; UNKNOWN/time-limit paths; and storage rollback. Solver and validator use separate domain implementations.

## Actual browser/API evidence

The final backend was started with FastAPI/Uvicorn and DEMO_MODE=true on loopback port 8003. Browser requests exercised actual server state and CP-SAT; no mock success responses were used in these browser flows.

- Generated a baseline via /api/jobs/generate, observed job completion and a live zero-hard report. Generation stage text comes from the server, not a simulated timer.
- Club account parsed the explicit Hinglish example to Monday/P10/SH-1/80 attendees/one hour. The read-only response showed authorised draft and hard constraints NOT CHECKED. A separate check returned PASS for category, timing/schema, capacity, type, accessibility, maintenance and clashes.
- Submitted that draft to pending approval, switched to Admin, approved, and observed the pending queue clear with an approve-booking audit entry.
- A Club Rep exam-priority claim remained visibly denied with an explicit authorised club-category option; it was not silently relabelled.
- Loaded the synthetic disruption with the approved manual booking protected. This separate browser run staged three teaching moves, zero exam moves and one added session; its minimum count was proven and its same-Admin approval button disabled. Deputy Admin approved. The difference from the final export's two moves comes from a separately generated baseline and protected manual reservation; neither result is a fixed UI value.
- Inspected student-group, faculty and room filters, Week 8 half-capacity exam cards, utilisation, approvals/audit and the repair diff.
- Inspected the 1440px desktop layout and 390px mobile layout. Corrected the mobile drawer overlap discovered during QA; Manual mode now hides the AI pane. The page contains the 740px table within horizontal scrolling while period labels stay pinned. Reduced-motion CSS disables animations/transitions.
- Final browser console inspection returned no error/warning entries. Static script syntax check passed.

Screenshots in evidence/: landing-desktop.png, workspace-desktop.png, priority-firewall.png, repair-staged.png, workspace-mobile.png, manual-mobile.png and landing-final.png. These are real captured UI states from the described runs. evidence/openapi.json records the actual backend contract; test logs and independent validation JSON are also saved there.

## Remaining limits and submission work

Official cit_public.json, the organisers' unmodified validator.py, export README/sample and proven-official disruption are absent. Official adapters, weights, booking scores and acceptance are unverified. Source conflicts and development time/lunch policies are explicit in CONSTRAINTS.md. No live external model call was made because no provider/model/key was supplied; injected faults verify fallback behaviour only.

The public repository, compatible external deployment and recorded/uploaded walkthrough video have not been created. SUBMISSION.md contains deployment preparation, eligibility checks and a recording script under five minutes. Event start/deadline and supplied-template provenance still require team verification. No Git history was rewritten or external publication performed. The app remains a single-worker JSON-persistence demo rather than campus SSO or a multi-worker production service.

## Supplied-template correction (same day)

Following visual feedback, the default entry and command-centre presentation were restored to match template.html rather than the custom introductory screen. Both supplied HTML references have SHA-256 75614b1bb18fad1accde2691defa88c8b40ea3457ef8c3f6905a4dcfa1ac1b1c and remain unchanged. The original reference was inspected as a rendered page for comparison; its temporary preview copy was removed.

Verified the connected five-day horizontal timetable, exact P1-P9/lunch labels and evening zone, merged three-hour laboratory cells, group/faculty/room filters, repair navigation, and one-click scenario -> editable draft -> server check. The Hinglish lab scenario returned a real blocked resource result, not a fabricated pass. Browser console errors/warnings were empty. At 390px, manual mode hid the AI pane, the drawer began exactly below the telemetry strip, and page width remained contained. New screenshots: evidence/template-restored-desktop.png and evidence/template-restored-mobile.png. node --check passed for both frontend scripts. No backend scheduling code or exports changed during this presentation correction.


## Two-scene Oryzo-style introduction (latest presentation update)

The default entry now presents two original interactive scenes adapted from the opening composition and next reveal of https://oryzo.ai/. This replaces the previous conventional introduction; the supplied command-centre UI remains behind Enter workspace and is reachable directly with #workspace.

Scene 1 maps to problem-statement page 1: an oversized ChronoGrid wordmark, academic desk, dimensional planner, Week 7/Week 8 toggle, campus-conflict narrative and live dataset totals. Scene 2 maps to page 2: a dimensional constraint card, fourteen selectable rule explanations, lunch/lab timing, exam half-capacity and the AI/Python/approval boundary. Pointer movement tilts the objects; scrolling transforms the planner and updates section progress. Reduced-motion preferences disable the motion. Both scenes are original HTML/CSS/JavaScript, with no extracted Oryzo assets, branding, testimonials, product claims or proprietary source code.

Illustrative planner tiles and rule cards are explicitly labelled; they never claim to be active schedules or validation results. Actual totals come from /api/overview. Enter workspace was exercised in the browser and reached the existing server-reported Hard 0 / Soft 1 / 190-session state. Week 8 toggle, capacity rule selection, one selected rule among fourteen, and phone-width containment were checked. Frontend scripts passed node --check. The server now returns Cache-Control: no-store for frontend responses, with versioned asset URLs to prevent stale previews; the served root and policy were verified over actual local HTTP.

Evidence: evidence/oryzo-cit-scene-1-desktop.png, evidence/oryzo-cit-scene-2-desktop.png, evidence/oryzo-cit-scene-1-mobile.png, evidence/oryzo-cit-scene-2-mobile.png. Scheduling algorithms, datasets and verified exports are unchanged by these presentation scenes. Earlier backend test results remain separately recorded; no new solver score is claimed.


## Interactive-scene refinements

Added cubic-eased chapter navigation (650-1250ms, interruptible by wheel/touch), a gradual desk-to-paper seam, and an entering rule-object reveal. Reduced-motion preference uses an immediate chapter jump and disables reveal motion.

The pencil is now an actual labelled button: pointer drag moves it, a click/Space rotates it, arrows adjust position, Alt+arrows rotate, and Escape/Home/double-click reset. Actual browser checks moved it from x=12px to x=82px/y=45px by dragging and exercised keyboard rotation/reset. The five-sided glass nav uses a transparent polygon clip and backdrop blur; the browser reported a five-point polygon and rgba background alpha 0.07 on the opening scene.

Manrope now provides the introduction's sans-serif typography; Bodoni Moda provides editorial italic accents, with local/system fallbacks. The operational workspace typography is unchanged. The rules scene now reserves separate grid rows for the heading and object. Browser bounding-box checks at 1920px measured a positive 28px heading/card gap with no intersection. Further checks at 800px and 390px also showed positive gaps and no page overflow. This directly fixes the supplied screenshot's overlapping possibility headline.

Updated screenshots: evidence/polished-opening-desktop.png, evidence/polished-rules-desktop.png and evidence/polished-rules-mobile.png. All frontend JavaScript syntax checks passed. These refinements change presentation and interaction only; prior scheduling/export evidence is unchanged.


## University workspace and role portals · 2026-10-31

Full regression: **49 passed in 31.23s**, with one existing Starlette/httpx deprecation warning. Six new portal cases cover all five server-bound identities, incorrect credentials, forged username fields, authenticated workspace access, HttpOnly cookies, logout invalidation and unknown routes. Final targeted portal regression: **6 passed in 0.86s**, including non-ASCII incorrect passwords.

Browser verified Deputy Administrator password login → university home → real timetable; faculty sign-in error rendering; desktop and 390px home/login layouts; hero highlight selection; locally loaded Figma photography. Six workflow cards use the existing operational renderers, metrics use current state, and the original introduction is preserved. Reference: Figma Frame 16 `14:32`, retrieved with design context and screenshot. University typography is Playfair Display/Raleway, adapted to native HTML/CSS/JS.

Browser follow-up: all five role headings verified; Faculty login selected F01, generation disabled, and mobile operational copilot toggle visible. Home/login document widths did not exceed the 390px viewport. Browser error log empty. Evidence: `evidence/university-workspace-desktop.png`, `evidence/university-workspace-mobile.png`, `evidence/administrator-login.png`.


## New Universitas workspace · 2026-10-31

Replaced the earlier workspace presentation using the newly supplied Universitas Figma design, with the existing native HTML/CSS/JS stack. Source frames: home `1:2`, profile `21:123`, news `21:184`, facilities `42:59`, contact `19:11`. The introduction and five role sign-in portals remain available.

Verification for this frontend change:
- `node --check frontend/university.js` passed.
- Browser checked all six live workflow renderers on desktop (1280px) and mobile (390px): six distinct header images and six distinct header layout classes; no document overflow at either size. All mobile banner photos loaded with non-zero natural dimensions.
- Facilities carousel next control advanced from 1/7 to 2/7. Workspace guide opened and navigated to the faculty timetable. Mobile request drawer opened with close control visible, top 80px and bottom 844px.
- Workflow fragment deep link, refresh and browser back restored the examination page and correct page title.
- Browser error logs empty. Fifteen referenced local image/icon files verified non-empty; all three SVG icons preserve their intrinsic root dimensions.
- No backend scheduling, login or approval behaviour changed; no full solver regression rerun was needed for the presentation changes. Previous backend regression remains recorded above.

Evidence: `evidence/universitas-home-desktop.png`, `evidence/universitas-home-full.png`, `evidence/universitas-home-mobile.png`, `evidence/universitas-exams-desktop.png`, `evidence/universitas-approvals-desktop.png`, and `evidence/universitas-page-checks.json`.


## Image-free signed-in redesign · 2026-10-31

Removed all image markup, image icons, photo banners and photo carousel from the workspace. Replaced the home with a typographic dashboard, real schedule totals, role-aware five-day teaching summary, six workflow cards, room-type counts and activity. All operational headers now use text and live counts. Data summaries use enriched assignments, matching the existing timetable.

`node --check frontend/university.js` passed. Browser verified home plus all six operational pages at 1280px and 390px: zero image/SVG/canvas/picture/video elements within the signed-in application, zero computed image backgrounds on desktop, and no document horizontal overflow. All six live operational renderers opened. Final browser error logs empty. No backend scheduling or permissions changes.

Evidence: `evidence/imagefree-checks.json`, `evidence/imagefree-workspace-desktop.png`, `evidence/imagefree-workspace-full.png`. This redesign supersedes the image-based workspace screenshots above. The introduction and login pages are outside this signed-in-only change.


## White and yellowish-brown education theme · 2026-10-31

Read Figma design context and screenshot for `NGZM2udTB3ySfzA1sng96m`, frame `1:3`; the source frame is a flattened preview. Applied the education layout language to all five separate sign-in portals and the workspace without introducing images into signed-in pages. Removed the previous login SVG illustration and role-specific colour accents in favour of one white/yellowish-brown palette and distinct role copy.

JavaScript syntax checks passed. Portal security regression: **6 passed in 0.85s** (one existing Starlette/httpx deprecation warning). Browser verified Administrator password login → themed workspace, all five mobile role portal headings/colours, all six mobile operational views, no horizontal overflow and zero image elements. Final browser error log empty. Evidence: `evidence/gold-admin-login.png`, `evidence/gold-workspace-desktop.png`, `evidence/gold-workspace-mobile.png`, `evidence/gold-theme-checks.json`.


## Sign-in/workspace role palette continuity · 2026-10-31

Restored the earlier sign-in design (cream backgrounds, role-coloured story panel, Bodoni italic headings and campus drawing). Added one shared palette stylesheet used by login and authenticated workspace pages. Theme selection follows the authenticated identity, including a distinct Deputy Admin palette, without changing permissions.

Browser checks: all five password sign-in flows produced an exact computed RGB match for panel/dark colour, accent and cream background between sign-in and workspace. All 30 role/workflow combinations retained their matching dark/accent colours with zero images. Faculty/Club demo switching updated the selected theme immediately. Club mobile workspace fit 390px (document width 385px). Error logs empty. JavaScript syntax checks passed. Backend authentication/approval code was unchanged.

Evidence: `evidence/role-palette-checks.json`, `evidence/club-matched-workspace.png`, `evidence/club-matched-mobile.png`, `evidence/restored-admin-login.png`.


## Operational typography and appearance polish · 2026-10-31

Added scoped `frontend/operations.css` for the six operational views, preserving the restored login design and role colours. Manrope headings/metrics and DM Sans controls replace the dense monospace presentation; improved metric hierarchy, tab labels, filters, timetable session typography, report cards, tables and request form spacing. Operational timetable now uses the full content width. The campus assistant starts closed on all viewport sizes and opens as an optional drawer; close control, Escape and manual-session-change entry remain functional. All existing backend permissions and validation paths are preserved.

JavaScript syntax checks passed. Browser verified all 30 role/page combinations on desktop and all 30 on mobile: correct role palettes, 38px Manrope desktop headings and 25px metric values, no document overflow and zero image elements. Verified room/faculty/group filters, deterministic placement explanation dialog, session-change form opening, assistant open/close/Escape and mobile manual booking form. Drawer geometry fit the mobile viewport (20px top, 824px bottom at 844px height). Browser error logs empty. No backend changes or solver regression required for this presentation update.

Evidence: `evidence/operations-polish-checks.json`, `evidence/polished-timetable-desktop.png`, `evidence/polished-timetable-mobile.png`.


## Fourteen-rule screenshot audit · 2026-10-31

All 14 hard constraints passed both the live API state audit and saved-state audit at revision 15: 190 teaching sessions / 244 hours, 41 exams, 10 approved bookings, maximum faculty daily load 4h, and zero independent-validator hard violations. Added 35 focused rule/boundary tests. Final full suite: **84 passed in 31.28s**, with one existing Starlette/httpx deprecation warning. No scheduling enforcement defect found and no backend production logic changed. Added a read-only audit script and report; the website continues to use the explicitly synthetic dataset. See `HARD_CONSTRAINT_AUDIT.md` and `evidence/live-hard-constraints-audit.json`.


## Availability & alternatives button · 2026-10-31

Reproduced the reported issue: the API returned correct checks, but the button had no pending state, incomplete fields produced raw schema errors, and result/alternative feedback was easy to miss in the drawer. The form now validates/highlights required fields before calling the server, shows a checking state, and displays an accessible result below the check button. Conflicts show selectable alternatives before the detailed checks; choosing one updates the draft and performs a fresh check. Available/no-alternative/service-error states have explicit messages. Draft changes or state refresh invalidate the previous result; stale async responses are ignored. No permissions or hard-constraint checks were relaxed.

Browser verified: incomplete draft (four labelled fields), occupied AUD Monday P10 (three alternatives), selecting CR-101/CR-102 (available), attendance 10000 (no alternatives), editing a checked draft (old result hidden), enabled/reusable button after completion, and 390px mobile layout with visible results. No browser errors. Checks did not submit a booking. New API regression verifies conflict → alternatives → valid rechecks, no-alternative response, and no state mutation. Full suite: **85 passed in 24.44s**, one existing Starlette/httpx deprecation warning. JavaScript syntax check passed.

Evidence: `evidence/availability-alternatives-fixed.png`, `evidence/availability-fixed-mobile.png`, `evidence/availability-fix-test-results.txt`.

## Room discovery and existing timetable editor · 2026-10-31

Replaced the availability button's primary diagnostics with actual room discovery. Browser verified Monday P10, 80 students, classroom: 15 same-time rooms with capacity and accessibility; selecting a room enables submission only after a fresh check. A physics-lab request for 180 students displayed explicit alternative room-type filters rather than silently relaxing requirements. Detailed reasons remain collapsed. Desktop and 390px mobile layouts checked, with no browser errors.

Added a searchable existing-session editor through home, timetable and individual session controls. Browser verified current placement, compatible room choices, lab start periods, unchanged-placement feedback, cancellation, faculty scope and disabled club editing. Isolated API tests verified targeted room moves preserve the active timetable until independent approval, reject self-approval, and validate the approved result. No live timetable or booking was modified during browser checks (revision 19).

Full suite: **88 passed in 39.07s**, with the existing Starlette/httpx deprecation warning. JavaScript syntax checks passed. Evidence: `evidence/room-discovery-editor-test-results.txt`, `evidence/available-rooms-capacities.png`, `evidence/modify-timetable-editor.png`, `evidence/modify-timetable-mobile.png`, `evidence/room-capacity-mobile.png`.

## AI assistant critical guardrails · 2026-10-31

Reviewed the user-supplied guardrails and added strict partial-draft filtering, deterministic raw exam-claim preservation, explicit conditional branch drafts, ambiguity metadata and verified free-slot pills constrained to the requested weekday/time range. Ambiguous provider start times are discarded. Parsing no longer automatically checks availability; unauthorised booking categories cannot enable the submission button.

Browser verified Club exam-spoof rejection, disabled submission, no automatic availability result after parsing, Thursday afternoon free-room pills with capacities, conditional primary/fallback review, fallback copying into editable fields and manual form visibility during a simulated outage. No browser errors, bookings or timetable changes during verification. Current live data remains revision 19. Provider timeout/quota/malformed-output tests use injected failures; no live external LLM is configured or tested. See AI_ASSISTANT_GUARDRAILS_AUDIT.md and evidence/assistant-guardrails-test-results.txt.

Final full suite: **94 passed in 31.19s**, one existing Starlette/httpx deprecation warning. Frontend JavaScript syntax checks passed.

## Existing-session maintenance explanation · 2026-10-31

Reproduced the screenshot's S001 → Monday P2–P4, LAB-3 rejection from the saved live data: Physics Lab 3 has a Week 7 Monday P1–P9 closure. The editor now provides a read-only “Check this move & find free slots” action, shows the exact blocked resource/window, and checks static blockers before invoking the proposal solver. Direct alternatives are independently validated with all other sessions unchanged. Separate repair candidates are explicitly unverified for whole-timetable feasibility and must go through the existing solver/approval workflow.

Regression tests reproduce the maintenance closure in isolated data, validate every direct alternative, verify read-only behavior and reject out-of-scope roles. Evidence: evidence/move-options-test-results.txt. Browser checks do not stage proposals or alter live schedules.

Final suite: **98 passed in 41.10s**, one existing Starlette/httpx warning. Browser verified the exact Monday P1–P9 maintenance message, separately labelled repair candidates, selecting Wednesday P2–P4 into the draft and fresh conflict checking. No browser errors. Screenshot: evidence/move-maintenance-explanation.png.

## Thorough slot-management audit · 2026-10-31

Revision 20 passed all 14 hard rules, 24,570 independent booking-window oracle comparisons, 180 discovery result-set checks and 19,440 solver/validator domain comparisons. Full suite: **98 passed in 42.67s**, one existing deprecation warning. Corrected misleading empty-cell labels, missing daytime booking occupancy, Club toolbar edit state and absent counter-offer capacity labels. Actual renderer fixtures passed academic/evening spans, calendar isolation and column alignment. Browser verified all five identities across room/faculty/group filters, closure/leave indicators, no console errors and mobile containment. Live timetable data remained untouched. See SLOT_MANAGEMENT_AUDIT.md and evidence/slot-management-audit.json.

## Responsive usability pass · 2026-10-31

Added scoped frontend/responsive.css to the public and authenticated shells. Improved mobile text sizes, 44–50px touch controls, wrapping navigation/action tabs, two-column mobile week summaries, compact role sign-in introduction, 16px handheld form inputs, safe-area/dynamic-height overlays and contained table scrolling. Role palettes, image-free workspace and scheduling handlers remain intact.

Actual viewport assertions verified all seven workspace views at widths 320, 390, 600, 768, 900, 1024 and 1440 (49 combinations), plus introduction/directory/five sign-in portals at those widths (49 combinations). All five roles passed all seven workspace views at 390 and 768 (70 combinations). No page horizontal overflow. Editor and assistant bounds fit 320×740, 390×844, 844×390 landscape and 768×1024 tablet with internal scrolling. Introduction rule title, object, details and selector have separate vertical bounds at 390px; interactive rule switching works. Empty browser error logs. Final tablet form fonts also use 16px. Temporary viewport override reset and extra test tabs closed. No backend changes or live timetable mutations.

Evidence: evidence/responsive-verification.json, evidence/responsive-home-mobile.png, evidence/responsive-login-mobile.png, evidence/responsive-rules-mobile.png. Presentation renderer smoke check passed; prior full scheduling suite remains 98 passing, with no scheduling code changed in this pass.

## Editable role-portal usernames · 2026-10-31

Replaced the read-only prefilled account with a blank, required, editable Username field on every role sign-in page. Requests now submit username and password; the server verifies the username belongs to the selected portal before creating a session. Demo panels show each assigned username below the default password. Browser verified all five blank/editable fields and correct demo labels, rejected admin2 in the Admin portal, then signed in successfully as admin. Six portal regression tests passed in 0.95s, including wrong credentials, missing username, forged role fields, portal separation, session cookies and logout. Login JavaScript syntax passed; scheduling logic unchanged. Evidence: evidence/editable-login-test-results.txt.

## Request privacy, leave repair, clash fixtures and assistant · 2026-11-01

Implemented server-scoped request history and per-request approval authority; separate queued leave requests with independent before/after preview and revision-checked approval; compact errors; resource section removal; exam agenda; clear assistant draft review. Full suite 102 passed in 48.18s, additional leave/stale/impersonation guard test passed. Actual isolated browser leave flow repaired one teaching assignment after Admin approval and kept the decision private. Main timetable unchanged by QA. See REQUEST_WORKFLOWS_VERIFICATION.md and fixtures/README.md.

## Assistant create-draft and submit buttons · 2026-11-01

Reproduced the handoff gap: schedule drafts populated only the advanced JSON, leaving visible move controls untouched. Also found Submit for approval disabled until a separate availability check. Draft creation now prefills editable session/day/period/room fields and hides the unrelated booking form for schedule requests. The timetable editor has a direct Create editable draft with Campus Assistant action. Advanced JSON is optional. Change/modify/edit timetable phrases are recognised. Missing fields never default to Monday/P1, and unchanged moves get an explanatory notification.

Booking submission now performs fresh deterministic server validation directly, without requiring an availability click first. Required fields, role restrictions, ambiguity confirmation and independent approval remain enforced. Pending controls have clear labels, duplicate writes are guarded, empty-input/outage paths restore the draft button, and role changes clear stale assistant intent. Clarification confirmation remains visible for both booking and schedule drafts.

Full suite **105 passed in 55.01s**, one existing deprecation warning. Actual browser on isolated port 8004 verified: create booking draft → submit without availability precheck → Pending private request; timetable editor → assistant → visible S040/Friday/P8/CR-102 controls; edited CR-103 → one-session staged diff with zero hard violations. Empty prompt and simulated outage produced small feedback with reusable controls. No browser errors. The isolated server was stopped, and no test requests were added to the active timetable. Evidence: evidence/assistant-handoff-test-results.txt and evidence/assistant-submit-pending-proof.png.

## Session redirect and file-import safety · 2026-11-01

Confirmed the prior server log contained an assistant parse 401 followed by GET /login. Replaced memory-only session authority with durable token-hash records, fixed 24-hour expiry and logout revocation. Preview QA uses an isolated cookie name. An API 401 during editing now opens in-place sign-in, retains message/booking/move/leave draft fields and restores them for the same account; it no longer navigates away. Explicit logout and unauthenticated initial navigation still require normal sign-in.

Imports now check JSON extension, 5 MB limit, syntax and file shape before dispatch. Full datasets are solved/validated in a read-only ten-minute preview, including booking conflicts/reasons/alternatives. Confirmed apply requires the preview owner, unchanged revision and fresh validation. Approved manual bookings/leave block replacement. Legacy direct dataset import also solves before committing; invalid or infeasible data cannot clear the working timetable. Strict dataset types and metadata shape prevent malformed-data crashes.

Full suite: **109 passed in 49.51s**, one existing Starlette/httpx deprecation warning. Browser on isolated port 8004: explicit logout in a second tab invalidated the session; Create editable draft stayed at /workspace#timetable, showed in-place sign-in and retained the message; reauthentication restored the draft. Restarting the isolated server retained login. Unsupported CSV, malformed JSON, schedule-as-change and infeasible move import all produced feedback without navigation. Valid dataset preview showed 189 sessions / 41 exams and 14 booking conflicts with alternatives; Cancel preserved revision 24. Main administrator session also survived a real server restart and created a draft without redirect. QA server stopped; main timetable unchanged by import tests.

Evidence: evidence/session-import-test-results.txt, evidence/import-ui-checks.json, evidence/import-conflict-preview.png, evidence/assistant-session-no-redirect.png. See SESSION_IMPORT_GUIDE.md for supported files and conflict resolution.
