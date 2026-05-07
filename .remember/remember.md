# Handoff

## State
Sprint shipped v0.2.0 → v0.8.0 in 7 atomic commits on local `main` (push pending — no GitHub creds on this WSL distro). Closed RCT-001, RCT-003, RCT-004, RCT-008, RCT-008b, RCT-009, GOV-001 (apexlon side, separate repo). RCT-002 + RCT-006 are scaffolded as code; the Milvus ingest run + study run are RCT-002b. Foundation docs (`adr.md`, `changelog.md`, `backlog.md`, `repo-bridge.md`, `system-design.md`) live at project root and are mutually consistent. `gpt-rct` Custom GPT paste-ready content at `code/governance/gpt-rct-instructions.md`.

## Next
1. **Push** — `git push origin main` from a terminal that has credentials. 7 commits queued.
2. **RCT-002b** — restart chain_server, run `code/scripts/helpers/ingest_nara_pages.py` to populate `rc_nara_pages` collection, then `study_nara_comparison.py` to generate the comparison-study report (RCT-006 unblocks immediately).
3. **GOV-002** — paste `code/governance/gpt-rct-instructions.md` into OpenAI GPT Builder. Set `RCT_URL` + `RCT_API_KEY` on apexlon and chain_server (handshake). Smoke-test the round-trip → closes RCT-010.

## Context
- **Pre-commit hook** is shipped but **not installed locally**. Run `bash code/scripts/git-hooks/install.sh` to dogfood it; until then changelog discipline is on Claude/contributor.
- **Server-side equivalent** (`.github/workflows/check-changelog.yml`) ships in v0.8.0; takes effect on next push to GitHub.
- **Brev instance `funny-rose-catfish` is gone**; `compose.yaml` still defaults to L40S Mixtral 8x7B NIM. Provision a fresh box when ready.
- **Apexlon** has its own ADR/CHANGELOG/BACKLOG (uppercase, different repo). GOV-001 landed there with 6 passing tests; apexlon's docs were NOT synced by this sprint — that's a follow-up the user can drive.
- **System-design.md moved** from `data/scratch/` to project root in v0.7.0 — old links may need updating in any external references.
- **memory rule:** every commit drives a version roll; doc-sync (adr/changelog/backlog) happens before commit, not after.
