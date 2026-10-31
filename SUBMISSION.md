# Submission preparation

Repository destination: https://github.com/shinjan-2006/CHRONOGRID_IITBBSR . Source and generated synthetic exports are prepared for upload. The hosted demo URL and walkthrough recording remain pending; the team will add them separately.

## Deployment package

Build the provided Dockerfile for a Python 3.12 host that supports OR-Tools and durable volumes. Serve port 8000 behind HTTPS. Mount /app/runtime and /app/exports. Run one worker. Use COOKIE_SECURE=true behind HTTPS. DEMO_MODE=true is explicitly disposable judge-demo access; keep it false for username-and-password operation. AI_API_KEY stays server-only. The frontend is served by the same FastAPI origin.

```text
docker build -t cit-chronogrid .
docker run --rm -p 8000:8000 -e DEMO_MODE=true -v chronogrid-runtime:/app/runtime -v chronogrid-exports:/app/exports cit-chronogrid
```

Sites' Cloudflare Worker runtime cannot host the Python/OR-Tools backend. Do not deploy a static-only frontend and claim it is the connected application. A compatible container/Python hosting destination remains to be selected and authorised for publication.

## Repository and eligibility

Before publishing, confirm the hackathon start and submission deadline, public-repository creation timing, registered-team membership and provenance of the supplied template/code. The existing Git directory was preserved; no history was rewritten. The user supplied the existing empty public repository for source publication. Upload status is reported in the accompanying chat; this document does not claim a hosted deployment. Public access, availability through results and working four-role accounts must be verified on the final destination. Do not push/deploy after the event deadline.

Obtain official cit_public.json, the unmodified validator.py, starter README/export sample and official change schema. Preserve originals byte-for-byte. Implement adapters from those actual documents, run the unmodified checker with its documented CLI and preserve output. Local synthetic verification cannot replace this step.

## Walkthrough recording script (target 4m45s)

| Time | Show actual working browser flow |
|---|---|
| 0:00-0:25 | Education introduction, source badge and computed 980-student count; enter workspace |
| 0:25-1:00 | Admin generation with real job stages, zero-hard report, group/faculty/room timetable |
| 1:00-1:45 | Club representative: explicit Hinglish request -> editable draft -> checks -> pending; Admin independently approves |
| 1:45-2:15 | Forged institute/exam claim is blocked; excessive attendance shows deterministic conflict/counter-offers; manual form remains usable during outage |
| 2:15-2:40 | All Spectra decisions/reasons, cancelled request and alternatives; Week 8 half-capacity exams |
| 2:40-3:55 | Load local synthetic disruption; staged before/after diff including added session; same Admin cannot approve; Deputy Admin approves; show proof/bounds and separate exam count |
| 3:55-4:25 | Utilisation denominator, private requests, approval/audit and mobile drawer |
| 4:25-4:45 | Export revalidation; source/AI limitations; reset control and demo accounts |

Record the actual running app; do not fabricate assignments, overlays, scores or successful results. Keep recording under five minutes. Video recording/upload and final YouTube/Drive link remain outstanding; this is a preparation script, not a submitted video.

Demo accounts: admin, admin2, coordinator, faculty, club. Default disposable password: ChronoGrid2026! (or DEMO_PASSWORD). admin2 provides independent approval for Admin-originated proposals.
