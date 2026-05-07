# Changelog

All notable changes to R-CT (Revolution Crossroads Teacher) are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Project rule (per user directive 2026-05-06):** every commit on `main`
drives a version roll. The semantics:

- **PATCH (0.0.x)** — internal fixes, doc-only edits, in-place tuning that
  does not change observable behavior.
- **MINOR (0.x.0)** — new functionality (endpoints, scorers, dimensions,
  helper scripts) that does not break existing callers.
- **MAJOR (x.0.0)** — breaking change to the chain_server API surface, the
  governance ledger schema, or the chat UI's call contract. Reserve for
  v1.0.0 (first stable release) and any subsequent contract breaks.

The current `unreleased` section accumulates changes between version rolls.
On commit, the contributor moves entries from `[unreleased]` into a new
versioned section, dated to the commit day, and bumps the version per the
rules above. CI enforcement is **not** in place yet (tracked as RCT-008);
discipline is contributor-side until then.

---

## [unreleased]

(empty — next entry lands here)

---

## [0.8.0] — 2026-05-07

Closes RCT-008b — server-side GitHub Action mirror of the client-side
changelog-update pre-commit hook from v0.5.0.

### Added

- **`.github/workflows/check-changelog.yml`** — runs on push to `main`
  and on PR targeting `main`. Fails the workflow if `changelog.md` was
  not touched in the diff. Override path: literal `[skip changelog]` in
  the commit message (rare; genuine CI-only changes).

### Notes

- The override token (`[skip changelog]`) keeps emergency commits
  possible. Drift created via override is a lint-bot follow-up, not a
  hard block.

---

## [0.7.0] — 2026-05-07

Moves `system-design.md` to the project root (was in gitignored scratch)
and refreshes it for the v0.3.0 multi-collection support + RCT-002 +
RCT-006 work. Closes RCT-009.

### Changed

- **`system-design.md` moved**: `data/scratch/hackathon-smithsonian/` →
  project root. Now tracked in git alongside `adr.md`, `changelog.md`,
  `backlog.md`. Subject to the same version-roll rule.
- **`system-design.md` §5.3** rewritten to reflect:
  - `chains.get_vector_index(collection_name=)` multi-collection support
    (v0.3.0)
  - `rc_nara_pages` collection scaffold (v0.3.0; ingest run is RCT-002b)
  - Comparison-study harness (`study_nara_comparison.py`, v0.4.0)
  - Future per-corpus splits framed as same pattern, deferred until study
    validates
- **`repo-bridge.md`** onboarding-order list updated to point at the new
  location.
- **`doc-status.md`** (in scratch) annotated to note the move.

---

## [0.6.0] — 2026-05-07

GOV-002 prep: paste-ready Custom GPT setup doc. The actual GPT creation
in OpenAI's GPT Builder is still a user action (we don't have OpenAI
account credentials).

### Added

- **`code/governance/gpt-rct-instructions.md`** — paste-ready content for
  the gpt-rct Custom GPT: Name, Description, Conversation Starters,
  Instructions block, Actions OpenAPI schema, env-var handshake
  (RCT_URL/RCT_API_KEY on both sides), test queries, and a publishing
  checklist. Surfaces the OECD KPI scores + ledger hash in a "trust
  panel" section the GPT renders below each lesson.

---

## [0.5.0] — 2026-05-07

Closes RCT-008 — client-side git pre-commit hook that enforces the
"every commit drives a version roll" rule.

### Added

- **`code/scripts/git-hooks/pre-commit`** — bash pre-commit hook. Fails
  the commit if `changelog.md` is not in the staged set. Override with
  `git commit --no-verify` when intentional.
- **`code/scripts/git-hooks/install.sh`** — idempotent symlink installer
  into `.git/hooks/`. Run once after cloning.
- **`code/scripts/git-hooks/README.md`** — documents the rule and the
  install dance.

### Notes

- This is **client-side** enforcement. A server-side workflow under
  `.github/workflows/check-changelog.yml` would catch contributor commits
  too; deferred until we add a CI surface to the repo.

---

## [0.4.0] — 2026-05-07

Comparison-study harness for RCT-006 (file-level vs page-level NARA).
Code-only — actual run produces the report once `rc_nara_pages` is
ingested (RCT-002b).

### Added

- **`code/scripts/helpers/study_nara_comparison.py`** — runs a fixed
  prompt suite against both `llamalection` (NARA-filtered) and
  `rc_nara_pages`, records top-K retrieval per collection (snippet, score,
  NAID, page hint), and writes a side-by-side markdown report at
  `data/scratch/hackathon-smithsonian/nara-comparison-study.md`. Includes
  a Summary section with mean top-1 similarity, mean retrieval latency,
  and NAID overlap percentage between collections.
- **7 default study prompts** baked into the harness, mapped to the demo
  corpus's strengths (widow petitions, Knox post-war finances, evidence
  taxonomy queries). Override with `--prompt` (repeatable).

### Changed

- **RCT-006 status:** code in place; run blocked on RCT-002b (page-level
  ingest needs to populate `rc_nara_pages` first).

---

## [0.3.0] — 2026-05-07

Page-level NARA scaffold. RCT-002 part 1 of 2 — code in place, ready to
ingest. Actual ingest run + verification deferred to RCT-002b.

### Added

- **`chains.get_vector_index(collection_name=None)`** now takes an optional
  collection_name parameter. Default behavior (no arg) is unchanged: hits
  the `llamalection` default collection. Pass a name to address a separate
  per-corpus index. `@lru_cache` keys per-name. Closes ADR-008's prerequisite.
- **`code/scripts/helpers/ingest_nara_pages.py`** — standalone ingest script
  that reads `nara_pension_pages.jsonl`, filters to the case-bundle scope
  (Knox / Wayne / N. Greene + widow / petition / pension), and inserts into
  a separate Milvus collection `rc_nara_pages`. Sets up its own service
  context (chain_server doesn't share with subprocess). Flags: `--max-rows`,
  `--filter-name` (repeatable), `--batch-size`, `--drop-first`, `--dry-run`.
  Does not touch `llamalection`.

### Changed

- **ADR-008 status:** `Proposed` → `Accepted (in progress)`. Code is ready;
  ingest run is the remaining step.

---

## [0.2.0] — 2026-05-07

The apexlon-pivot bridge work: R-CT exposes a structured lesson-generation
endpoint; apexlon learns to call it as a new executor. Closes RCT-001,
RCT-003, RCT-004, GOV-001.

### Added

- **`POST /lesson` on chain_server (RCT-003).** New `code/chain_server/lesson.py`
  module with `LessonRequest` Pydantic model, `build_lesson_prompt`, cloud
  and microservice dispatch helpers, and `handle_lesson` orchestrator.
  Returns structured JSON: `{request_id, triad, lesson_markdown, model,
  retrieval, generation_ms}`. Local mode returns 501 in v1; cloud and
  microservice paths use `stream=False` per ADR-003.
- **`X-API-Key` middleware on `/lesson` (RCT-004).** Reads `RCT_API_KEY`
  env var. Unset → dev mode (no auth). Set → header must match or 401.
  Implemented as a FastAPI `Depends(...)` so existing endpoints (`/health`,
  `/uploadDocument`, `/generate`, `/documentSearch`) stay UI-facing and
  unauthenticated.
- **`app/modules/executor_rct.py` in apexlon (GOV-001).** Mirrors
  `executor_llm.py` / `executor_nim.py` shape. Uses `httpx` (already in
  apexlon's deps; `requests` is not). Stub mode echoes raw_input when
  `RCT_URL` is unset; live mode POSTs to `${RCT_URL}/lesson`, populates
  `obj.outputs.{text,triad,rct_request_id}` and
  `obj.execution.{model,latency_ms,rct_generation_ms,retrieval}`.
- **6 unit tests for executor_rct in apexlon.** `tests/test_executor_rct.py`
  covers stub mode, missing compiled prompt, live happy path, omitted
  API key, ConnectError, HTTPStatusError. **6 passed in 0.37s.**
- **Routing for the new executor (apexlon).** `app/core/state_machine.py`
  imports `executor_rct` and dispatches `if target == "rct":`.
  `app/modules/router.py` adds `"rct"`, `"lesson"`, `"revolution_crossroads"`
  to `TASK_TYPE_TO_EXECUTOR`. Default behavior (no selector) stays
  `executor_llm.run` — existing tests don't regress.
- **Apexlon config additions.** `RCT_URL`, `RCT_API_KEY`,
  `RCT_INFERENCE_MODE` (default `"cloud"`).

### Removed

- **`code/governance/{__init__.py,ledger.py,prompt_template.py}` (RCT-001).**
  ~270 lines of dead weight after ADR-007. `code/governance/schemas/`
  remains for the canonical `rag-record.schema.json` synced from the
  enterprise repo.

### Notes

- Pre-existing failures in apexlon's `tests/test_state_machine.py` (hitting
  `compiler._fallback_template`'s `TODO(human)`) are unrelated to this
  release and remain open in apexlon's own backlog.
- Smoke-test of the full ChatGPT → apexlon → R-CT round-trip (RCT-010)
  now unblocked; deferred to next release until OPS-001 (Brev NIM) and
  GOV-002 (Custom GPT duplication) are complete.

---

## [0.1.0] — 2026-05-06

First baseline. Captures the state achieved during the hands-on session that
brought the demo path from concept to live retrieval.

### Added

- **chain_server patches.** YAML frontmatter parser (`_parse_frontmatter`)
  in `code/chain_server/chains.py`. `ingest_docs` rewritten to bypass
  UnstructuredReader for `.md` and preserve frontmatter as queryable
  Document metadata. New `retrieve_evidence_triad(query, top_k=24)` returns
  top-1 chunk per corpus (loc / nara / si).
- **Cloud non-streaming workaround.** `stream=(inference_mode != "cloud")`
  in chains.py (4 sites). Cloud mode now collects full LLM response and
  yields once. Workaround for NGC staging-tier streaming flakiness
  (ADR-003).
- **Chat client timeout bump.** `code/chatui/chat_client.py` post-request
  timeout changed from `timeout=10` to `timeout=(10, 300)` to accommodate
  cloud-mode cold-start of 15–40 s.
- **NIM compose for L40S deployment.** `compose.yaml` defaults to
  `nvcr.io/nim/mistralai/mixtral-8x7b-instruct-v01:latest` with persistent
  named volume (`nim-cache`), `shm_size: 16gb`, healthcheck on
  `/v1/models`, and env-var-only API key.
- **Multi-mode prompt template dispatch.** `rag_chain_streaming` selects
  Mistral / Llama / Phi / Nemotron RAG template based on the active model
  id (cloud `nvcf_model_id` or microservice `nim_model_id`), no longer
  fall-through to GENERIC for microservice mode.
- **`_DEFAULT_NIM_MODEL` constant** in chains.py — configurable via
  `NIM_MODEL_ID` env var, defaults to `mistralai/mixtral-8x7b-instruct-v0.1`
  to match compose.yaml.
- **Helper scripts under `code/scripts/helpers/`:**
  - `materialize-rc-sample.py` — reservoir-samples N rows per dataset →
    per-row .md with YAML frontmatter.
  - `curate_demo_corpus.py` — filters JSONLs for case-bundle veterans +
    thematic slices → 64 .md (Knox / Wayne / N. Greene + widow / pension /
    petition).
  - `bulk_ingest_jsonl.py` — direct JSONL → Milvus ingest bypassing the
    HTTP `/uploadDocument` round-trip.
  - `materialize-rc-sample.sh` — wrapper that prefers api-env python.
- **`code/governance/`** scaffold (ledger.py, prompt_template.py,
  __init__.py). **Status:** dead weight after ADR-007 pivot — tracked for
  removal as RCT-001.
- **Curated demo corpus** ingested into Milvus `llamalection` collection
  (64 chunks across 16 demo buckets).
- **Embedding device** flipped from `cpu` → `cuda:0` in `variables.env`.
- **Documentation suite** in `data/scratch/hackathon-smithsonian/`:
  `system-design.md`, `deck-v10-outline.md`, `doc-status.md`. Older
  artifacts moved to `archive/` with index README.
- **Naming standardization.** All actively-maintained docs renamed to
  lowercase-kebab-case (ADR-010). 7 superseded reports + 7 older pptx
  versions moved to `archive/`.
- **Project foundation files (this commit):** `adr.md`, `changelog.md`,
  `backlog.md`, `repo-bridge.md`, `code/scripts/sync-from-enterprise.sh`.

### Changed

- **Default upload path.** `data/documents/` now expects `.md` with YAML
  frontmatter, not raw JSONL. UI drag-drop continues to work; JSONL is no
  longer a valid input through the UI.
- **`data/sources/revolutioncrossroads/`** added to `.gitignore` (JSONL
  source bundles do not enter git).

### Fixed

- **JSON-noise hypothesis disproven.** Earlier suspicion that JSONL
  uploads via the UI produce garbage chunks turned out to be wrong — the
  user's manual upload was actually the curated `.md` set, which has clean
  metadata. Bible-passage chunks in NARA `R. 10,759` are real evidentiary
  pages from Henry Turner's pension file (family Bible used as marriage
  proof), not retrieval artifacts. Documented in system-design.md §6.

### Deprecated

- **`code/governance/` in R-CT.** Will be deleted after explicit user
  go-ahead (per ADR-007). Apexlon owns governance going forward.

### Removed

- **Random-sample 75-doc demo corpus** (replaced by the 64-doc curated set
  per ADR-006).
- **Hardcoded NGC API key** in `compose.yaml` (replaced by
  `${NVIDIA_API_KEY:?Error NVIDIA_API_KEY not set}` env var pattern).

### Security

- API key now exclusively in environment / Workbench secret store; no
  hardcoded values in committed files.

---

## [0.0.0] — pre-session baseline

Inherited state from the upstream NVIDIA Hybrid RAG example. No R-CT
specific changes; serves as the comparison point for the 0.1.0 entry.
