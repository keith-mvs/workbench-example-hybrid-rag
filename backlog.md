<!-- Copyright (c) 2026 Booz Allen Hamilton (or per applicable hackathon participation terms). Architecture and design content; not licensed under the Apache 2.0 LICENSE.txt that covers the surrounding code. See ADR-013 + NOTICE. -->

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
| RCT-002 | Build `rc_nara_pages` Milvus collection (page-level NARA) — *part 1 of 2 done in v0.3.0; ingest run pending* | in-progress | P2 | claude | 2026-05-06 | 2026-05-07 | `chains.get_vector_index(collection_name=)` patched; `ingest_nara_pages.py` written. RCT-002b is the actual ingest run. ADR-008. |
| RCT-002b | Run `ingest_nara_pages.py` against Milvus | open | P2 | claude | 2026-05-07 | 2026-05-07 | Inside the Workbench container with api-env python. ~1500 rows × case-bundle filter. Frees `RCT-006` (comparison study). |
| RCT-018 | Empirical recalibration of `code/governance/__init__.py:CONFIDENCE` | open | P3 | claude | 2026-05-07 | 2026-05-07 | v1 confidence values are placeholders mirrored from apexlon. Recompute against a gpt-rct fixture corpus once we have one. |
| RCT-013 | Port apexlon's append-only ledger into `code/governance/` | open | P0 | claude | 2026-05-07 | 2026-05-07 | ledger.py with chained SHA-256, JSONL at `data/governance/ledger.jsonl`. Same shape apexlon uses, no apexlon dependency. v0.11.0. |
| RCT-014 | Wire ledger + scorer into `/lesson` endpoint | open | P0 | claude | 2026-05-07 | 2026-05-07 | chain_server/lesson.py emits ledger events at request_received → retrieval_completed → generation_completed → kpi_scored. Returns scores + event_id in response JSON. v0.12.0. |
| RCT-015 | Rewrite `gpt-rct-instructions.md` to call gpt-rct directly (not apexlon) | open | P0 | claude | 2026-05-07 | 2026-05-07 | OpenAPI Action points at gpt-rct `/lesson`. Trust panel uses scores returned in the response, not pulled from apexlon's `evaluation.kpi`. v0.13.0. |
| RCT-016 | Cloudflare tunnel config for gpt-rct's chain_server | blocked | P1 | user | 2026-05-07 | 2026-05-07 | Same Cloudflare account as apexlon, possibly new tunnel + hostname. User confirms account/hostname plan. |
| GOV-002 | Duplicate `gpt-ledger` Custom GPT → `gpt-rct` — *paste-ready content shipped in v0.6.0; user must create in GPT Builder* | open | P0 | user | 2026-05-06 | 2026-05-07 | Paste-ready Instructions, Description, conversation starters, Actions OpenAPI schema, and env-var handshake all in `code/governance/gpt-rct-instructions.md`. User action: copy-paste into OpenAI GPT Builder. |
| OPS-001 | Provision Brev L40S + run `docker compose up local-nim` | in-progress | P0 | user | 2026-05-06 | 2026-05-06 | Brev box `funny-rose-catfish` provisioned. Claude Code installed. Project cloned. NIM compose pull pending. |
| OPS-002 | NGC API key on staging vs production tier | blocked | P1 | user | 2026-05-06 | 2026-05-06 | Current key is staging — Mistral 7B v0.3 returns 404, only Mixtral 8x22B is provisioned. Mitigated by ADR-004 (Microservice mode bypasses cloud entirely). Resolution: NVIDIA support / NGC web console. |
| RCT-005 | Refresh v9 pptx → v10 per `deck-v10-outline.md` | open | P1 | user | 2026-05-06 | 2026-05-06 | Slide-by-slide text replacement in PowerPoint. ADR-009. 21 slides; v10-outline.md is canonical content. |
| DECK-001 | Rehearse 3-layer demo narrative (ChatGPT → apexlon → R-CT) | open | P1 | user | 2026-05-06 | 2026-05-06 | Deck slides 3, 7, 13 carry the governance thread; the live demo must show each layer in turn. Practice the chunk-score callout (the e5 similarity score visible in the chunked context area). |
| DECK-002 | Record presentation per submission packet timing | open | P2 | user | 2026-05-06 | 2026-05-06 | Submission deadline 2026-05-04 has passed; current target is the 2026-06-17 finale event. Verify whether a recorded presentation is still required for the finale. |
| RCT-006 | Comparison study: file-level vs page-level NARA retrieval — *harness done in v0.4.0; run pending RCT-002b* | in-progress | P2 | claude | 2026-05-06 | 2026-05-07 | `study_nara_comparison.py` written. 7 default prompts × top-K × both collections. Outputs markdown w/ summary stats (similarity, latency, NAID overlap). Run blocked on RCT-002b. |
| RCT-007 | Bridge sync-script auth when enterprise repo flips back to private | open | P3 | claude | 2026-05-06 | 2026-05-06 | Decision deferred until visibility flip. Options: SSH key + fleming-keith identity, fine-grained PAT in `~/.gh-token-fleming-keith`, or move authoritative copies into R-CT. See `repo-bridge.md` §"When the enterprise repo goes back to private". |
| GOV-003 | Wire OECD-scoring KPIs into the Custom GPT Instructions | open | P2 | user | 2026-05-06 | 2026-05-06 | After GOV-001 + GOV-002, the Custom GPT should surface KPI scores back to the teacher in a "trust panel" format mirroring `ui_mockup.html`'s right sidebar. |
| GOV-004 | Calibrate apexlon KPI confidence values against R-CT lesson outputs | open | P3 | user | 2026-05-06 | 2026-05-06 | Apexlon's CONFIDENCE map was calibrated for compiled-prompt artifacts. Once R-CT produces real lesson outputs through the bridge, recompute confidence per dimension over a fixture corpus. |
| OPS-003 | Cloudflare named-tunnel pointed at chain_server | open | P2 | user | 2026-05-06 | 2026-05-07 | After ADR-011 the tunnel target IS chain_server (not apexlon). Tracked in detail as RCT-016 going forward. |
| OPS-004 | GitHub SSH setup on this WSL distro | in-progress | P1 | user | 2026-05-07 | 2026-05-07 | Key generated at `~/.ssh/id_ed25519` (fingerprint `SHA256:dEUzu5O//ktMjtc/MybMKJpkebhv5+tNKz6Y5iVprcE`). Remote switched from HTTPS to SSH. **Action remaining:** paste the public key into github.com → Settings → SSH and GPG keys → New SSH key. Public key was printed to chat. Then `git push` works and 11 queued commits go up at once. |
| OPS-005 | Rename GitHub repo `workbench-example-hybrid-rag` → `gpt-rct` | open | P1 | user | 2026-05-07 | 2026-05-07 | github.com → repo Settings → General → Rename. After rename, ping me — I update `git remote set-url origin` and sweep doc references (repo-bridge.md, system-design.md, remember.md, .git config inside the Workbench container, etc.). |
| OPS-006 | Detach repo from NVIDIA fork relationship on GitHub | open | P2 | user | 2026-05-07 | 2026-05-07 | Self-serve isn't available; needs github.com/contact ticket → category "Repositories" → "Detach fork" with the repo URL. 1–2 day turnaround. Local-side `upstream` remote already removed in v0.9.3. |
| RCT-010 | Smoke test: full ChatGPT → apexlon → R-CT round-trip | open | P0 | claude | 2026-05-06 | 2026-05-06 | After RCT-003 + RCT-004 + GOV-001 + GOV-002. Verify end-to-end with one canonical lesson request. |

## Done

| ID | Title | Status | Closed | Notes |
|---|---|---|---|---|
| RCT-001 | Delete dead `code/governance/` .py files after apexlon-pivot | done | 2026-05-07 | ADR-007. ~270 lines removed. `code/governance/schemas/` retained for synced rag-record schema. |
| RCT-003 | `POST /lesson` endpoint on chain_server | done | 2026-05-07 | New `code/chain_server/lesson.py`. Cloud + microservice dispatch, structured JSON response, non-streaming per ADR-003. |
| RCT-004 | `X-API-Key` middleware on `/lesson` | done | 2026-05-07 | FastAPI `Depends(require_api_key)`. Dev mode when `RCT_API_KEY` unset; 401 on mismatch when set. Existing endpoints unchanged. |
| GOV-001 | `app/modules/executor_rct.py` in apexlon | done | 2026-05-07 | HTTP-calls R-CT `/lesson` via `httpx`. Stub mode + live mode + error handling. 6 new unit tests pass. State-machine + router wired through `task_type` ∈ {rct, lesson, revolution_crossroads}. Apexlon config: `RCT_URL`, `RCT_API_KEY`, `RCT_INFERENCE_MODE`. |
| RCT-008 | Client-side pre-commit hook for changelog enforcement | done | 2026-05-07 | `code/scripts/git-hooks/pre-commit` + `install.sh` + README. v0.5.0. Server-side counterpart is RCT-008b. |
| RCT-009 | Move `system-design.md` to project root + refresh for v0.3.0/v0.4.0 architecture | done | 2026-05-07 | v0.7.0. Doc now tracked in git with the other foundation docs. §5.3 rewritten with multi-collection support + page-level NARA scaffold + comparison-study harness. |
| RCT-008b | Server-side check-changelog GitHub Action | done | 2026-05-07 | v0.8.0. `.github/workflows/check-changelog.yml`. Override via `[skip changelog]` token. |
| RCT-011 | Re-establish `code/governance/` scaffold (un-RCT-001 per ADR-011) | done | 2026-05-07 | v0.10.0. Module structure + SPDX headers + BAH-derivative attribution per ADR-012. |
| RCT-012 | Port apexlon's 5-dimension OECD scorer into `code/governance/` | done | 2026-05-07 | v0.10.0. dimensions/{auditability,transparency,robustness,fairness,reproducibility}.py + scorer.py composer. Adapted for lesson-event scoring (not compiled-prompt artifacts). All 8 files compile clean. |
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
