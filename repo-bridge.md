# repo bridge — local R-CT ↔ enterprise wai-hackathon-2026

This project (R-CT, the Hybrid RAG fork) has a sibling repository under a
different GitHub account that holds **strategy and dataset-context** material
the engineering work refers to. This document is the contract for how those
two repos relate, what crosses the boundary, and how to keep them in sync
without divergence.

## The two repos

| Repo | Path / URL | Owner | What lives there |
|---|---|---|---|
| **R-CT** (this one) | `keith-mvs/workbench-example-hybrid-rag` (github.com) | keith-mvs (personal) | All R-CT engineering: chain_server, chatui, NIM compose, governance bridge, demo curator scripts. Forked from NVIDIA's upstream Hybrid RAG example. |
| **WAI-Hackathon-2026** | `fleming-keith/wai-hackathon-2026` (github.com, **temporarily public**) | fleming-keith (enterprise persona) | Dataset extractors, schemas, BAH-supplied facts, case-bundle research, original strategy docs the local scratch folder originally seeded from. keith-mvs is a collaborator. |

Local clone of the enterprise repo lives at:
`/home/workbench/wai-hackathon-2026` (WSL) — accessible from Windows at
`\\wsl.localhost\NVIDIA-Workbench\home\workbench\wai-hackathon-2026`.

## Why two repos

- The gpt-rct engineering work is forked from NVIDIA's open Workbench example
  and needs to stay forkable / public-runnable for the hackathon demo.
- The strategy + research material was seeded under fleming-keith because that
  is the BAH-affiliated identity for the hackathon — even though the code was
  built on a personal box. Moving everything into one repo would either expose
  enterprise context publicly, or hide engineering work from non-collaborators.
- Splitting lets each repo carry its own license, visibility, and audit trail
  without compromising the other.

## Apexlon: a third repo, referenced as inspiration only

`/mnt/c/Users/kjfle/Workspace/apexlon` is a **separate tool** built for a
different purpose (a generic LLM/tool-orchestration control plane). gpt-rct
draws on apexlon's *patterns* — the 5-dimension OECD scorer, append-only
chained-SHA-256 ledger, state-machine module contract — but does **not**
depend on apexlon at runtime. ADR-011 is the canonical statement of this
boundary. Apexlon stays unmodified by gpt-rct work; gpt-rct stays runnable
without apexlon deployed.

## What crosses the boundary

Direction is **read-only enterprise → R-CT**. We never push back to the
enterprise repo from R-CT automation; if a R-CT-side improvement should live
in the enterprise repo, it goes through a manual PR opened from the cloned
checkout under fleming-keith credentials.

**Files we pull into R-CT** (see `code/scripts/sync-from-enterprise.sh` for
the canonical manifest):

| Enterprise path | R-CT destination | Why |
|---|---|---|
| `schemas/rag-record.schema.json` | `code/governance/schemas/rag-record.schema.json` | Canonical record shape — used by validators and any future ingest writes that need to conform. |
| `outputs/case-bundles-summary.md` | `data/scratch/hackathon-smithsonian/upstream/case-bundles-summary.md` | Authoritative source of the 5 demo veterans. Our local `case-bundles.md` is the pitch-edited version. |
| `docs/project/participant-packet.md` | `data/scratch/hackathon-smithsonian/upstream/participant-packet.md` | BAH-supplied facts. Our local `track1-hackathon-facts.md` is the distilled version. |
| `docs/project/team-plan.md` | `data/scratch/hackathon-smithsonian/upstream/team-plan.md` | Original team plan referenced by REPO_SYNC_2026-04-23.md. |
| `outputs/curation-workflow.md` | `data/scratch/hackathon-smithsonian/upstream/curation-workflow.md` | Reference for the Evidence Triad pedagogy lineage. |

Anything pulled into `data/scratch/hackathon-smithsonian/upstream/` is **read-only
mirror**. Do not edit — edit the enterprise source and re-sync.

## What does NOT cross

- Enterprise repo's runtime code (`scripts/extract_*.py`, `src/`, `tests/`) —
  we already have our own ingest pipeline (`code/scripts/helpers/...`). Pulling
  the enterprise scripts in would create two sources of ingest truth.
- Enterprise repo's deck files and presentation drafts — those live in
  `data/scratch/hackathon-smithsonian/` and are owned by the local repo.
- Anything containing identifiable BAH internal details, partner names,
  contracts, or fly.io secrets.

## How to sync

```bash
# From the R-CT project root:
bash code/scripts/sync-from-enterprise.sh
```

Effect: `git -C ~/wai-hackathon-2026 pull --ff-only`, then `rsync` the
manifest files into `data/scratch/hackathon-smithsonian/upstream/` (and the
schema into `code/governance/schemas/`). The script is idempotent and prints
which files changed.

The sync target paths are gitignored except `code/governance/schemas/` so the
authoritative schema travels with the engineering code.

## Setup checklist for a new collaborator

1. Clone R-CT: `git clone https://github.com/keith-mvs/workbench-example-hybrid-rag.git`
2. Clone enterprise (must have collaborator access while it's public, or
   fleming-keith credentials):
   `git clone https://github.com/fleming-keith/wai-hackathon-2026.git ~/wai-hackathon-2026`
3. Run sync once: `bash code/scripts/sync-from-enterprise.sh`
4. Read in this order: `system-design.md` (project root), `adr.md`,
   `backlog.md`, `data/scratch/hackathon-smithsonian/track1-hackathon-facts.md`.

## When the enterprise repo goes back to private

Currently the enterprise repo is **temporarily public** for hackathon
visibility. When it flips back to private, the sync script will fail with a
404 unless the running user has fleming-keith credentials configured. At that
point, options are:

1. Switch to SSH with keys configured for fleming-keith.
2. Use a fine-grained GitHub PAT with read access on the enterprise repo,
   stored in `~/.gh-token-fleming-keith` and consumed by the sync script.
3. Move authoritative copies of the synced files into R-CT directly (and
   accept the divergence cost).

Decision deferred until visibility flip; tracked in `backlog.md` as RCT-007.
