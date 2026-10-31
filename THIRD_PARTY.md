# Third-party components

Direct runtime/test dependencies are pinned in `requirements.txt`.

| Component | Use | Licence |
|---|---|---|
| Python 3.12 | Backend runtime and dataset generation | PSF |
| Google OR-Tools 9.15.6755 | CP-SAT mathematical scheduling/repair solver | Apache-2.0 |
| FastAPI 0.162.0 | HTTP API and OpenAPI docs | MIT |
| Pydantic | Strict request/dataset models, pulled by FastAPI | MIT |
| Starlette | ASGI HTTP/static/cookie infrastructure | BSD-3-Clause |
| Uvicorn 0.54.0 | ASGI server | BSD-3-Clause |
| HTTPX 0.28.1 | Optional model HTTP calls and API testing | BSD-3-Clause |
| pytest 9.2.0 | Constraint, solver and API regression tests | MIT |
| Inter | Optional Google Fonts UI typeface | SIL OFL-1.1 |
| JetBrains Mono | Optional Google Fonts monospace typeface | SIL OFL-1.1 |

OR-Tools/FastAPI dependencies include NumPy, pandas, protobuf, absl-py, immutabledict, anyio and typing helpers. Installed transitive versions are recorded in `requirements-lock.txt`. Font loading has local system fallbacks. The active frontend uses no Tailwind CDN script, Font Awesome dependency or JS framework. The retained source template contains its original CDN references solely for provenance.

The optional model provider is user-configured and subject to that provider's API terms. No provider key or proprietary model weights are bundled. The supplied HTML, master prompt and problem statement are user-provided references; their ownership and hackathon eligibility must be confirmed by the team.

The original campus illustration is authored SVG/CSS and has no external image dependency. Oryzo was viewed for visual/story inspiration only. Python standard-library csv/json/hashlib generate the current CSV mirror and artifact hashes. A retained optional export_csv.mjs uses the Codex artifact-tool runtime, but it is not an application dependency or the default reproducible CSV command. pypdf was used in the development environment to read the supplied PDF; it is not required to run the app.

Manrope and Bodoni Moda are optional introduction typefaces loaded through Google Fonts, under SIL Open Font License terms. Avenir/Arial and Baskerville/Georgia provide system fallbacks. The command-centre fonts remain Inter and JetBrains Mono.


## Supplied university Figma template

[University website (Community)](https://www.figma.com/design/Aqein6qAyABgdO8GcRzEtY/University-website--Community-), Frame 16 `14:32`, supplied by the user, is the source for the university workspace layout and bundled reference photography. Figma design context supplied temporary asset URLs; all assets were downloaded to `frontend/assets` rather than referenced remotely at runtime. The original university crest and foreign university text/social links are replaced with CIT project content. Photography is identified in the UI as template reference imagery, not actual CIT campus photography. The supplied file's underlying image rights are not independently established here. Playfair Display and Raleway are optional Google Fonts with system fallbacks (SIL OFL).


## Active Universitas template

The current workspace uses the user-supplied [UI/UX Figma Universitas (Community)](https://www.figma.com/design/xMlengHKBNTJRzMH2S2oEV/ui-ux-figma-universitas--Community-). Design context and screenshots were read for home `1:2`, profile `21:123`, news `21:184`, facilities `42:59` and contact `19:11`. Assets downloaded from Figma are stored locally under `frontend/assets/universitas`; runtime code contains no temporary asset URLs. The home follows the campus hero, three overlapping cards, facilities strip and navy footer. Page headers adapt the reference's full-width, offset photo, split and facility compositions; each workflow has a distinct image. Foreign university branding, contact details and generic news were replaced with CIT project content. Underlying rights to supplied reference photos are not independently established. Elsie, Fira Sans and Fauna One are optional Google Fonts (SIL OFL) with local fallbacks. The earlier template assets remain as reference files but are no longer used by the workspace.


Latest workspace revision: the signed-in UI no longer uses the supplied reference photography or SVG image icons. Historical assets remain locally for provenance. The active dashboard uses optional DM Sans and Manrope Google Fonts (SIL OFL) with system fallbacks.


Current education theme: user-supplied Figma file `NGZM2udTB3ySfzA1sng96m`, frame `1:3`, was inspected as a flattened preview for layout inspiration. Its raster screenshot is not embedded as the application interface. The user-directed image-free workspace uses native text, CSS and existing operational components.


Publication package (2026-11-01): unused historical Figma photography under frontend/assets is excluded from Git. The active application uses inline/code-authored illustrations on the public introduction/login and no photographs in signed-in views. Historical paragraphs above describe earlier development iterations, not assets shipped by the current application.
