# Handoff

## State
R-CT (Hybrid RAG fork) demo path is live: 64 curated .md ingested into Milvus `llamalection`, Cloud Mixtral 8x22B answering coherently after non-streaming patch (`code/chain_server/chains.py`) + 300s read timeout (`code/chatui/chat_client.py`). `compose.yaml` defaults to Mixtral 8x7B NIM for Brev L40S deploy. Consolidated docs live at `data/scratch/hackathon-smithsonian/{system-design,deck-v10-outline,doc-status}.md`; older artifacts in `archive/`. Started a `code/governance/` module (ledger, prompt_template, __init__) — **superseded by pivot, awaiting user OK to delete**.

## Next
1. **Delete `code/governance/`** (now dead weight) once user confirms.
2. **Add `POST /lesson` to `code/chain_server/server.py`** (~50 lines): takes `{essential_question, grade_band, duration_minutes}`, calls `chains.retrieve_evidence_triad`, builds prompt, calls Mistral, returns JSON.
3. **Add `app/modules/executor_rct.py` to apexlon** (`/mnt/c/Users/kjfle/Workspace/apexlon`) modeled on `executor_llm.py` — calls R-CT `/lesson` over HTTP, populates `obj.outputs`.
4. **Duplicate `gpt-ledger` Custom GPT in OpenAI GPT Builder → `gpt-rct`** with R-CT-specific Instructions; reuse apexlon Cloudflare tunnel + auth.

## Context
- **Pivot:** governance, ledger, KPI scoring, prompt-tailoring all stay in apexlon. R-CT is pure retrieval+generation. Apexlon's existing 5-dimension OECD scorers, append-only ledger, Custom GPT, and Cloudflare-tunnel pattern are reused as-is.
- **Demo target:** Brev L40S box `funny-rose-catfish`. Claude Code is installed there (Node 20 via nvm); project cloned at `~/workbench-example-hybrid-rag`. Run NIM via `compose.yaml`, switch chat UI Mode=Microservice.
- **NVIDIA_API_KEY is on staging tier** (`stg/...` model prefix, Mistral-7B 404s). Mixtral 8x22B works for cloud, Mixtral 8x7B NIM works for microservice.
- **User preferences (memory):** lowercase-kebab for new files; never trigger RAG ingest/upload without explicit "go".
- **Submission deadline 2026-05-04 has passed** — work now targets the **2026-06-17 finale**, not the deck submission.
