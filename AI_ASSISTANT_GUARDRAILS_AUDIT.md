# AI assistant guardrails review

Reviewed against the user-supplied `ai_assistant_role_guardrails.md` on 2026-10-31.

| Critical rule | Enforcement / review result |
| --- | --- |
| AI never decides validity | Parser imports no solver and cannot approve. Python constraints, CP-SAT and independent validator remain authoritative. Parse responses always say `validation_status: not_checked`; free-slot pills are computed by deterministic room checks. |
| AI never changes persisted data | Parse endpoint produces editable drafts only. Targeted changes stage proposals; existing role scope, revision checks, independent approval and validation apply before activation. Tests compare state before/after parsing. |
| Manual operation survives API failure | Prominent Manual Form bypasses parsing. Timeout, quota, malformed response and simulated outage tests retain manual submission. Existing timetable editor also bypasses AI. |
| Declare AI tools and prompts | AI_USAGE.md identifies Codex, optional provider configuration, endpoint, prompt path and conservative no-key parser. No additional model or external call was introduced. A real provider's exact model must be recorded before configuring it for submission. |

## Corrections made

- Filter provider output through strict partial booking or disruption schemas. Discard authority/unknown fields and return malformed drafts for manual correction. Model JSON cannot supply approval, role, priority or validity.
- Preserve raw exam claims even if a model relabels them as club events. Club accounts remain restricted to club category; exams use the academic workflow.
- Keep verified free-slot pills within an explicitly requested weekday and afternoon/evening range. Search can suggest real rooms without requiring an already-selected venue, including capacity/accessibility metadata. Choosing a pill only edits the draft.
- Separate conditional primary/fallback drafts. Do not leak fallback accessibility/type requirements into the primary draft or automatically submit either branch. Common explicit timing/attendance is carried to the fallback, and confirmation plus fresh deterministic checking remains required.
- Expose intent, language and ambiguity metadata; change the parse button wording to “Create editable draft” so parsing does not imply validation.
- Remove automatic availability checking after parsing. Disable booking submission for categories outside the current role's entitlement; server-side checks remain authoritative. Discard model-invented weekdays/start periods when the raw request gives no exact value.

## Existing functions retained

English/Hinglish booking drafts, faculty leave/move drafts, manual extra-class entry, scope-checked minimum-change rescheduling, deterministic placement explanations and booking rejection reasons. Explanations describe known facts and do not invent an optimisation rationale or claim a feasible slot was uniquely forced. The conservative local parser asks for session IDs; it is not advertised as a full conversational model. Missing or ambiguous fields require user review.

The guardrails' illustrative schema is mapped to existing native API fields (day 0–4, integer start period and duration). The document's “Lunch P5–P6” shorthand does not replace the project's actual protected 13:00–14:00 break between P5 and P6. Three-hour teaching labs remain P2–P4 or P6–P8.
