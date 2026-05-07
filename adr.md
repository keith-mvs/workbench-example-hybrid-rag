# Architecture Decision Records — R-CT

Append-only log of architecture, design, and process decisions for the
Revolution Crossroads Teacher (R-CT) project. Each entry uses the Michael
Nygard ADR template with explicit **Timestamp** and **Technical Rationale**
sections per project convention.

**Status values:** `Proposed` · `Accepted` · `Deprecated` · `Superseded by ADR-NNN`

---

## ADR-001 — Fork NVIDIA's Hybrid RAG example as the base

- **Status:** Accepted
- **Timestamp:** 2026-03-12 (initial fork) · documented retroactively 2026-05-06

**Context.** A K-12 lesson-builder grounded in CC0 historical corpora needs a
RAG stack with vector search, an LLM front, and an interactive UI. Building
all three from scratch in the hackathon timeline is unrealistic.

**Decision.** Fork `NVIDIA/workbench-example-hybrid-rag`. Inherit AI
Workbench packaging, Gradio chat UI, FastAPI chain_server, LlamaIndex 0.9.44
orchestration, Milvus 2.3.1 vector store, and the three switchable inference
modes (Cloud / Local TGI / NIM Microservice).

**Technical Rationale.**
- The Workbench packaging gives us reproducible builds (`postBuild.bash`
  produces two pinned conda envs) and a one-click chat surface — saving days
  of orchestration work.
- LlamaIndex 0.9.44's `MilvusVectorStore` + `SimpleNodeParser` handles
  chunking and indexing without us writing it; tradeoff is we're locked to
  setuptools<71 (LlamaIndex 0.9.44 imports `pkg_resources`).
- Three inference modes baked in mean we can pivot the LLM target without
  rearchitecting (used later in ADR-003 and ADR-004).

**Consequences.** R-CT inherits Apache 2.0 license; downstream integrators
must respect it. The two-conda-env constraint (api-env on torch 2.5.0;
ui-env on torch 2.1.1) is intentional and must not be unified — see
`CLAUDE.md` "Pitfalls."

---

## ADR-002 — Single Milvus collection with corpus-tagged metadata, not three indexes

- **Status:** Accepted (interim) — to be revisited per ADR-008
- **Timestamp:** 2026-05-06

**Context.** Per `corpus-specific-role-assignment.md`, the design pitches
three indexes (Objects / Newspapers / Pension Files) with intent-based
routing. LlamaIndex 0.9.44's `MilvusVectorStore` supports per-collection
operations but the existing chain_server uses a single default collection
(`llamalection`).

**Decision.** Keep one Milvus collection for v0. Tag each chunk with a
`corpus` metadata field (`loc` / `nara` / `si`). Implement Evidence Triad
retrieval by single similarity query over `top_k=24`, then group results by
`corpus` metadata and return top-1 per corpus.

**Technical Rationale.**
- One collection eliminates the cross-collection-merge complexity at
  retrieval time.
- The `corpus` metadata field is queryable via Milvus dynamic fields, so we
  can split into per-corpus collections later without a data-format change.
- The existing chain_server doesn't need a `get_vector_index(corpus=)` patch
  for v0 — we can ship retrieve_evidence_triad on the existing function
  signature.

**Consequences.** Top-K must be generous (≥24) to ensure all three corpora
are represented in the result set. If one corpus dominates, we may need
metadata-filtered queries (LlamaIndex `MetadataFilters`) to enforce
diversity. Page-level NARA (rc_nara_pages) is the trigger for the multi-
collection refactor — tracked as RCT-002.

---

## ADR-003 — Cloud Mixtral 8x22B in non-streaming mode (staging-tier workaround)

- **Status:** Accepted (workaround)
- **Timestamp:** 2026-05-06

**Context.** The user's NVIDIA API key resolved to NVIDIA's `stg/...`
(staging) tier — confirmed by direct `curl` returning `stg/mistralai/...`
in the response model field. Streaming requests with `stream=True` to
`https://integrate.api.nvidia.com/v1/` close mid-stream for long
generations, surfacing as `urllib3.exceptions.ProtocolError: Response
ended prematurely` in the chat UI.

**Decision.** Patch `code/chain_server/chains.py` to set
`stream=(inference_mode != "cloud")` everywhere (4 sites). For cloud mode,
collect `completion.choices[0].message.content` after the call returns and
yield the entire response as a single chunk through FastAPI's
`StreamingResponse`.

**Technical Rationale.**
- Direct non-streaming `curl` calls to the cloud endpoint succeed cleanly
  even on staging tier — confirmed empirically.
- The chat client's `iter_content(16)` works with one large chunk just as
  well as with many small ones.
- Streaming UX is a nice-to-have; reliability is must-have for the demo.
- Local TGI and NIM microservice paths keep `stream=True` since their
  upstreams are local and stable.

**Consequences.** Cloud-mode users see a 15–40s blank screen during
generation, then the full answer drops in. We compensated with a
client-side timeout bump from `timeout=10` to `timeout=(10, 300)` in
`code/chatui/chat_client.py`. The proper fix is an NGC API tier upgrade
(production tier) or migration to NIM Microservice (ADR-004).

---

## ADR-004 — Brev L40S + Mixtral 8x7B NIM as production demo target

- **Status:** Accepted
- **Timestamp:** 2026-05-06

**Context.** The dev machine has an RTX 2080 Ti (11 GB VRAM) — too small for
any local LLM beyond ~7B params. Cloud staging tier is unstable (ADR-003).
We need a stable streaming LLM path for the live finale demo.

**Decision.** Provision a Brev L40S instance (48 GB VRAM, single Ada
Lovelace GPU). Deploy `mistralai/mixtral-8x7b-instruct-v01` as a NIM
container via `compose.yaml`. Switch chat UI Mode to "Microservice" pointed
at `http://localhost:8000/v1/`.

**Technical Rationale.**
- Mixtral 8x7B FP16 (~28 GB) fits comfortably in 48 GB with headroom for
  KV cache.
- Mixtral 8x22B does NOT fit even quantized (~70 GB INT4 minimum) — leave
  on Cloud as fallback only.
- L40S is on Brev's standard catalog at ~$1–2/hr — affordable for the
  demo window.
- NIM container exposes OpenAI-compatible API at `/v1/` — drops in via
  existing `openai.chat.completions.create` calls in `chains.py`, no
  client refactor needed.
- Bypasses the staging-tier cloud API entirely → reliable streaming.

**Consequences.** Production deployment requires NVIDIA AI Enterprise
license (~$4,500–$9,000/GPU/yr). For demo only, eval license is sufficient.
First container start downloads ~28 GB weights; persisted to a Docker named
volume (`nim-cache`) so subsequent restarts skip the download.

---

## ADR-005 — YAML-frontmatter ingestion path for .md files (preserves per-row metadata)

- **Status:** Accepted
- **Timestamp:** 2026-05-06

**Context.** `chain_server`'s `/uploadDocument` runs `LlamaIndex
UnstructuredReader`, which strips per-row JSON structure when handed a
`.jsonl` file. Original `chains.ingest_docs` then clobbers
`Document.metadata` with `{filename: <base64>}` only — losing the corpus
tag, source URLs, NAIDs, etc. that downstream retrieval and citation need.

**Decision.** Introduce `_parse_frontmatter()` (no PyYAML dependency, simple
flat-key parser) in `chains.py`. Patch `ingest_docs` to detect `.md` files,
read them directly, split YAML frontmatter from body, attach frontmatter
fields as `Document.metadata` and bypass UnstructuredReader for that path.
Materializer scripts (`materialize-rc-sample.py`, `curate_demo_corpus.py`)
emit `.md` with frontmatter — `corpus`, `doc_index`, `source_url`,
NAID/EDAN/LCCN, dates, places.

**Technical Rationale.**
- `.md` is what UnstructuredReader handles cleanly *and* what the Gradio
  drag-drop accepts — bridges the JSON-records → file-uploads gap.
- Inline parser avoids adding PyYAML to api-env (which is already brittle
  due to setuptools<71).
- Filename-prefix corpus inference (`loc_*` / `nara_*` / `si_*`) provides a
  fallback when frontmatter is absent.
- Other formats (PDF, DOCX) continue through UnstructuredReader unchanged.

**Consequences.** JSONL files cannot be uploaded through the UI; teachers
or curators must materialize to `.md` first, OR power users use
`bulk_ingest_jsonl.py` to bypass the HTTP endpoint and write directly to
Milvus. Documented in `system-design.md` §4.4.

---

## ADR-006 — Curated demo corpus (case-bundle veterans + thematic slices)

- **Status:** Accepted
- **Timestamp:** 2026-05-06

**Context.** Random-sample ingestion (75 docs across 3 corpora, fixed seed)
produced a corpus where Evidence Triad retrieval was unpredictable — some
queries surfaced no SI object or no NARA testimony. For a stage demo we
need predictable, pedagogically rich retrieval results.

**Decision.** Replace the random sample with a curated set built by
`code/scripts/helpers/curate_demo_corpus.py`. Filter the three primary
JSONLs for case-bundle veterans (Henry Knox, Anthony Wayne, Nathanael
Greene) plus four thematic slices (widow, pension, petition). Cap each
veteran-corpus pairing at 6 rows; theme-corpus at 3. Result: **64 .md
files** spanning 16 buckets across 3 corpora.

**Technical Rationale.**
- Knox + Wayne have full-triad coverage in the local JSONLs (verified via
  grep). N. Greene has SI + NARA but no LOC; flagged honestly rather than
  hidden.
- Thematic slices catch high-value content (widow petitions, the home-front
  story) without requiring a named entity match.
- Caps keep the corpus small enough to fully control quality, large enough
  to give Milvus retrieval meaningful diversity.
- Each `.md` carries the `demo_bucket` field so retrieval results can be
  traced back to why they're in the corpus.

**Consequences.** The curated corpus does not reflect the full
RevolutionCrossroads scale (12K+ SI, 78K+ NARA, 58K+ LOC). The deck and
SYSTEM_DESIGN are explicit that this is the demo subset; production
deployment would re-ingest at full scale. `case-bundles.md` and
`case-bundles-summary.md` in the upstream repo are the source of the
case-bundle veteran list.

---

## ADR-007 — Governance lives in apexlon, not in R-CT (the pivot)

- **Status:** Accepted (supersedes the in-flight `code/governance/` module)
- **Timestamp:** 2026-05-06

**Context.** Initial design called for porting apexlon's 5-dimension OECD
KPI rubric, append-only ledger, and prompt-tailoring into R-CT's
`code/governance/` module. Three files were started (`__init__.py`,
`ledger.py`, `prompt_template.py`). Mid-build, decided that apexlon's
existing infrastructure already implements all of this and is wired to a
Custom GPT distribution layer — duplicating it inside R-CT would create
two sources of governance truth.

**Decision.** Stop porting. R-CT becomes a pure retrieval-and-generation
backend exposed via `POST /lesson` on `chain_server`. apexlon's existing
state machine, scorers, ledger, and Custom GPT (`gpt-ledger`) wrap R-CT as
the executor target via a new `app/modules/executor_rct.py` (modeled on
`executor_llm.py` / `executor_nim.py`). A new Custom GPT (`gpt-rct`) is
duplicated from `gpt-ledger` and points at the same apexlon endpoint.

**Technical Rationale.**
- Apexlon's governance is built, tested, and calibrated (5 dimensions × ~70
  lines of deterministic Python each).
- Apexlon's append-only chained-SHA-256 ledger is independent of R-CT's
  storage and survives R-CT restarts.
- The 3-layer demo narrative (ChatGPT → apexlon → R-CT) cleanly mirrors
  the deck's "trustworthy / auditable / data-grounded" message — each
  layer is a slide.
- Net code: ~270 lines deleted from R-CT, ~130 lines added across two
  repos.

**Consequences.** R-CT must expose a clean `POST /lesson` API surface and
add API-key auth for apexlon to call into. Apexlon must add the executor
module and update the Custom GPT Instructions. The repo-bridge document
(`repo-bridge.md`) covers context-doc sharing across the two GitHub repos
involved; a third-party path exists between R-CT and apexlon (separate
machines, HTTP/JSON). Tracked as RCT-003 / RCT-004.

---

## ADR-008 — Page-level NARA as a separate Milvus collection (rc_nara_pages)

- **Status:** Proposed
- **Timestamp:** 2026-05-06

**Context.** File-level NARA chunks (current `llamalection`) preserve
document context but make page-precise citation hard. Page-level NARA gives
exact-page evidence for teacher drill-down. Mixing both granularities into
one collection would double-count the same content under different chunk
boundaries — retrieval would surface near-duplicates.

**Decision.** Build a **separate** Milvus collection `rc_nara_pages` from
`nara_pension_pages.jsonl`, filtered to the same case-bundle scope as the
file-level demo set. Patch `chains.get_vector_index(collection_name=None)`
to accept a collection name. Lesson generation reads file-level for
context; citation drill-down reads page-level on demand.

**Technical Rationale.**
- Different granularities serve different stages of the lesson workflow.
- LlamaIndex's MilvusVectorStore takes a `collection_name` parameter — the
  patch is one-liner-friendly.
- A comparison study (file-level vs page-level) on a fixed prompt suite
  produces the demo-side evidence that the choice is principled.

**Consequences.** Triggers the multi-collection refactor deferred in
ADR-002. Adds a second ingest run (~10K rows) and a study harness script.
Does not block the v0.1.0 demo path. Tracked as RCT-002.

---

## ADR-009 — Pptx layout preservation, content refresh via outline doc

- **Status:** Accepted
- **Timestamp:** 2026-05-06

**Context.** v9 of the deck (`Team1_SmithsonianHackathon2026_v9_REPAIRED_
ENHANCED.pptx`) has the layouts, fonts, color palette, and image placements
the team wants to keep. Content needs a refresh: dataset facts corrected,
overstatements moderated, architecture diagram updated to actual stack.

**Decision.** Author all v10 content as Markdown in `data/scratch/
hackathon-smithsonian/deck-v10-outline.md` matching v9's 21-slide
structure. Refresh the .pptx by editing v9 in PowerPoint slide-by-slide
against the outline (text replacement only). Don't regenerate the .pptx
from scratch.

**Technical Rationale.**
- Markdown outline is reviewable, diff-able, and version-controllable —
  Slack-able to teammates without a PowerPoint license.
- Slide-by-slide text replacement preserves animations, masters, and
  color identity that auto-generation would lose.
- `python-pptx` could programmatically replace text runs if needed
  (deferred until manual edits prove painful).

**Consequences.** Source of truth split between .md (content) and .pptx
(presentation). The pptx files for v1–v7 moved to `archive/`; v9 stays at
the root. Tracked as RCT-005.

---

## ADR-010 — Lowercase kebab-case for new docs and scripts

- **Status:** Accepted
- **Timestamp:** 2026-05-06

**Context.** The project inherited a mix of naming conventions: PascalCase
pptx files, snake_case .md from earlier drafts, files with spaces in
names. Mixed conventions create friction in shells, URLs, and tab
completion.

**Decision.** Default to **lowercase-kebab-case** for any new doc, shell
script, or non-Python module created in this project. Existing third-party
files (NVIDIA upstream, Mistral docs) keep their original names. Python
modules under `code/chain_server/` and `code/governance/` use snake_case
because the Python import system requires it.

**Technical Rationale.**
- Kebab-case is shell-safe, URL-safe, and case-insensitive-filesystem
  safe.
- Single, predictable convention reduces tab-completion friction.
- Acknowledges Python's snake_case requirement explicitly to avoid
  ambiguity.

**Consequences.** All docs created during this session and going forward
use kebab-case. Existing files (`Corpus-specific role assignment.md`,
`SYSTEM_DESIGN.md`, etc.) were renamed in a one-time pass on 2026-05-06.
Saved as `feedback_filename_style.md` in the project memory.
