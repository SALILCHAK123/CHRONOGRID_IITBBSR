# AI use declaration

## Development tools

OpenAI Codex was used to read the supplied problem statement and master prompt, inspect the user-supplied HTML prototype, design the architecture, generate the synthetic dataset generator, implement frontend/backend/solver/validator, write tests and documentation, and inspect the local app through browser automation. The precise hosted Codex model deployment identifier is not exposed to this project; the team should record the model shown in its own Codex session before submission.

The user supplied the implementation master prompt (retained as `MASTER_PROMPT_FRONTEND_BACKEND.md`) with the supplemental planning brief reproduced inside and `cit_chronogrid_platform.html` as the interface template. The original HTML is retained in `reference/`. It contained simulated validation and scheduling results; the active app does not run that simulation code. The team must declare any additional AI tools used to create those supplied materials; their provenance is not established by this repository.

## Product model/API calls

No external model is configured or called by default. `backend/assistant.py` supports a user-selected OpenAI-compatible `/chat/completions` endpoint using `AI_BASE_URL`, `AI_MODEL`, and server-only `AI_API_KEY`. When enabled, record the actual provider and exact model identifier here before submission. The call interprets English/Hinglish into booking or schedule-change drafts and identifies missing information. It receives the request text and relevant synthetic room/session context plus the current role identity. Do not commit keys.

Prompts are stored in `prompts/parse.txt`. The no-key fallback is a conservative Python rule parser, explicitly labelled as such in the interface; it is not presented as an LLM. Explanations currently come from deterministic placement facts, not model-generated claims.

Guardrails review (2026-10-31): Codex added strict partial-draft filtering, raw exam-claim preservation, read-only weekday/time-bounded free-slot suggestions and explicit conditional branch review. These use deterministic Python and JavaScript, with no additional model or endpoint. The parser response exposes intent_type, raw_language, is_ambiguous, clarification_question and draft_payload alongside the application's existing draft schema. Product provider remains opt-in; no live external model call was made during this review. Provider failures are injected in tests. The example JSON in the supplied guardrails is mapped to existing day integers, period integers and duration fields rather than introducing a second scheduling schema.

## Forbidden model decisions

The model cannot validate a schedule, choose authoritative event priority, grant roles, approve requests, override fixed slots, authorise changes, execute tools, write persisted data, or decide whether an assignment satisfies constraints. The parse endpoint changes no state. Model JSON is untrusted and goes through strict schemas, server-side role checks and the same deterministic constraints as manual requests before it can be submitted or applied. A user can edit and explicitly confirm a draft; this does not bypass those checks.

CP-SAT constructs schedules in Python. The separate validator checks results before persistence, again at independent approval, and again at export. An AI outage leaves manual booking and schedule-change requests usable. API success and JSON parsing are never evidence of schedule validity.

## Current implementation pass

Codex also corrected synthetic department/course/faculty coherence, implemented calendar isolation and independent solver domains, added generation jobs, strict assignment gates, approval/persistence modules, the original education-themed CSS/SVG introduction, responsive mobile drawer, API documentation and regression/evidence scripts. Browser automation inspected the live Oryzo reference and the local desktop/mobile flows. Oryzo was inspiration only: no assets, claims, branding, testimonials or code were copied. No external image/video generation model was used. No live product LLM request was made; timeout, quota and malformed-provider responses in tests are explicitly injected faults.

Codex authored the two-scene Oryzo-style CIT introduction in frontend/story.js and frontend/story.css, adapting spatial composition and interaction ideas to the first two PDF pages. All scene objects are original CSS/HTML; no image-generation model, copied Oryzo asset or extracted proprietary code was used. Counts are loaded from the actual backend and illustrative graphics are labelled.


University workspace iteration: used Figma design context for supplied Frame 16, then translated React/Tailwind prototype output into the existing native HTML/CSS/JS stack. Kept real state, scheduling handlers, permissions and approval APIs. Added five strict server-bound role login routes and six API regression cases. No university news, campus identity claims, or fabricated schedule results were imported from the reference.


Universitas iteration: used Figma design-to-code context and screenshots from the new supplied reference, translated to native JavaScript/CSS without introducing a framework. Implemented distinct imagery/layouts for all six workflow headers, facilities carousel, workspace guide and browser-history navigation. Scheduling and authentication APIs were preserved.
