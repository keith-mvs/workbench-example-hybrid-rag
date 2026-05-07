# Backlog — R-CT

Open and closed work items. **ID convention:** `RCT-NNN` for R-CT-engineering
items, `GOV-NNN` for cross-repo apexlon governance work, `DECK-NNN` for the
hackathon deck and presentation, `OPS-NNN` for deployment / infrastructure.
IDs are append-only (never reuse, never renumber).

**Status values:** `open` · `in-progress` · `blocked` · `done` · `wont-fix`

---

## Active

| ID | Title | Status | Priority | Owner | Created | Updated | Notes / Cross-refs |
|---|---|---|---|---|---|---|---|
| RCT-002 | Build `rc_nara_pages` Milvus collection (page-level NARA) | open | P2 | claude | 2026-05-06 | 2026-05-06 | Patch `chains.get_vector_index(collection_name=)`. Ingest from `nara_pension_pages.jsonl` filtered to case-bundle scope. ADR-008. |
| GOV-002 | Duplicate `gpt-ledger` Custom GPT → `gpt-rct` | open | P0 | user | 2026-05-06 | 2026-05-06 | OpenAI GPT Builder. Reuse apexlon Cloudflare tunnel. Update Instructions to teach lesson-request shape. Action item for user (requires their OpenAI account). |
| OPS-001 | Provision Brev L40S + run `docker compose up local-nim` | in-progress | P0 | user | 2026-05-06 | 2026-05-06 | Brev box `funny-rose-catfish` provisioned. Claude Code installed. Project cloned. NIM compose pull pending. |
| OPS-002 | NGC API key on staging vs production tier | blocked | P1 | user | 2026-05-06 | 2026-05-06 | Current key is staging — Mistral 7B v0.3 returns 404, only Mixtral 8x22B is provisioned. Mitigated by ADR-004 (Microservice mode bypasses cloud entirely). Resolution: NVIDIA support / NGC web console. |
| RCT-005 | Refresh v9 pptx → v10 per `deck-v10-outline.md` | open | P1 | user | 2026-05-06 | 2026-05-06 | Slide-by-slide text replacement in PowerPoint. ADR-009. 21 slides; v10-outline.md is canonical content. |
| DECK-001 | Rehearse 3-layer demo narrative (ChatGPT → apexlon → R-CT) | open | P1 | user | 2026-05-06 | 2026-05-06 | Deck slides 3, 7, 13 carry the governance thread; the live demo must show each layer in turn. Practice the chunk-score callout (the e5 similarity score visible in the chunked context area). |
| DECK-002 | Record presentation per submission packet timing | open | P2 | user | 2026-05-06 | 2026-05-06 | Submission deadline 2026-05-04 has passed; current target is the 2026-06-17 finale event. Verify whether a recorded presentation is still required for the finale. |
| RCT-006 | Comparison study: file-level vs page-level NARA retrieval | open | P2 | claude | 2026-05-06 | 2026-05-06 | Run a fixed prompt suite against `llamalection` and `rc_nara_pages`. Score with apexlon's KPI rubric. Output side-by-side study report. Depends on RCT-002. |
| RCT-007 | Bridge sync-script auth when enterprise repo flips back to private | open | P3 | claude | 2026-05-06 | 2026-05-06 | Decision deferred until visibility flip. Options: SSH key + fleming-keith identity, fine-grained PAT in `~/.gh-token-fleming-keith`, or move authoritative copies into R-CT. See `repo-bridge.md` §"When the enterprise repo goes back to private". |
| RCT-008 | CI enforcement of changelog version-roll-on-commit rule | open | P3 | claude | 2026-05-06 | 2026-05-06 | Pre-commit / pre-push hook that checks `changelog.md` was updated in the commit. Currently relies on contributor discipline. |
| RCT-009 | Add page-level NARA collection metadata to `system-design.md` §5.3 | open | P3 | claude | 2026-05-06 | 2026-05-06 | After RCT-002 ingest, document collection schema, row count, and routing rules. |
| GOV-003 | Wire OECD-scoring KPIs into the Custom GPT Instructions | open | P2 | user | 2026-05-06 | 2026-05-06 | After GOV-001 + GOV-002, the Custom GPT should surface KPI scores back to the teacher in a "trust panel" format mirroring `ui_mockup.html`'s right sidebar. |
| GOV-004 | Calibrate apexlon KPI confidence values against R-CT lesson outputs | open | P3 | user | 2026-05-06 | 2026-05-06 | Apexlon's CONFIDENCE map was calibrated for compiled-prompt artifacts. Once R-CT produces real lesson outputs through the bridge, recompute confidence per dimension over a fixture corpus. |
| OPS-003 | Cloudflare named-tunnel pointed at chain_server (not just apexlon) | open | P2 | user | 2026-05-06 | 2026-05-06 | If we want chain_server reachable directly (e.g. for testing the /lesson endpoint without going through apexlon). Optional — apexlon-only access is the intended production path. |
| RCT-010 | Smoke test: full ChatGPT → apexlon → R-CT round-trip | open | P0 | claude | 2026-05-06 | 2026-05-06 | After RCT-003 + RCT-004 + GOV-001 + GOV-002. Verify end-to-end with one canonical lesson request. |

## Done

| ID | Title | Status | Closed | Notes |
|---|---|---|---|---|
| RCT-001 | Delete dead `code/governance/` .py files after apexlon-pivot | done | 2026-05-07 | ADR-007. ~270 lines removed. `code/governance/schemas/` retained for synced rag-record schema. |
| RCT-003 | `POST /lesson` endpoint on chain_server | done | 2026-05-07 | New `code/chain_server/lesson.py`. Cloud + microservice dispatch, structured JSON response, non-streaming per ADR-003. |
| RCT-004 | `X-API-Key` middleware on `/lesson` | done | 2026-05-07 | FastAPI `Depends(require_api_key)`. Dev mode when `RCT_API_KEY` unset; 401 on mismatch when set. Existing endpoints unchanged. |
| GOV-001 | `app/modules/executor_rct.py` in apexlon | done | 2026-05-07 | HTTP-calls R-CT `/lesson` via `httpx`. Stub mode + live mode + error handling. 6 new unit tests pass. State-machine + router wired through `task_type` ∈ {rct, lesson, revolution_crossroads}. Apexlon config: `RCT_URL`, `RCT_API_KEY`, `RCT_INFERENCE_MODE`. |
| RCT-100 | chain_server cloud-mode non-streaming patch | done | 2026-05-06 | ADR-003. `stream=(inference_mode != "cloud")` plus single-yield branch. |
| RCT-101 | chat_client timeout bump from 10s to (10,300) | done | 2026-05-06 | Cloud cold-start absorption. |
| RCT-102 | Frontmatter parser + `ingest_docs` rewrite for .md | done | 2026-05-06 | ADR-005. Preserves per-row metadata. |
| RCT-103 | `retrieve_evidence_triad(query, top_k)` helper | done | 2026-05-06 | ADR-002. Single-collection corpus-grouped retrieval. |
| RCT-104 | Curated demo corpus (64 .md across 16 buckets) | done | 2026-05-06 | ADR-006. Knox / Wayne / N. Greene + widow / pension / petition. |
| RCT-105 | NIM compose.yaml refresh (Mixtral 8x7B default, named volume, healthcheck, env-key) | done | 2026-05-06 | ADR-004. Brev L40S target. |
| RCT-106 | RAG-template dispatch refactor (model-aware, mode-agnostic) | done | 2026-05-06 | Microservice now picks the right family template. |
| RCT-107 | `_DEFAULT_NIM_MODEL` constant + env override | done | 2026-05-06 | Removes hardcoded llama-3.1-8b fallback. |
| RCT-108 | Embedding device flipped to cuda:0 | done | 2026-05-06 | `variables.env`. Required project restart to take effect. |
| RCT-109 | Doc consolidation pass (system-design / deck-v10-outline / doc-status) | done | 2026-05-06 | Source-of-truth split + index. |
| RCT-110 | Naming standardization to lowercase-kebab + archive/ folder | done | 2026-05-06 | ADR-010. |
| RCT-111 | Project memory: filename style + upload-gating feedback | done | 2026-05-06 | `~/.claude/projects/.../memory/` updated. |

---

## Conventions

- **Adding an item:** append a row to "Active" with the next ID. Update the
  changelog `[unreleased]` section if the work has begun.
- **Closing an item:** move the row to "Done" with a `Closed` date. Add an
  `[unreleased]` changelog entry naming the ID. Bump the version per the
  rules in `changelog.md` on the same commit.
- **Blocked items:** use the `blocked` status and capture the blocker
  inline in the Notes column. Never delete an item — even abandoned ones
  go to `wont-fix` with a one-line reason.
- **Cross-repo items:** if the work is in apexlon (not R-CT), use the
  `GOV-NNN` prefix and link to the relevant apexlon file in Notes.
