# Revolution Crossroads Teacher (R-CT) — System Design

**Status:** CURRENT — source of truth as of 2026-05-07. Lives at the project
root (was previously in `data/scratch/...` which is gitignored — moved in
v0.7.0 so the document gets the same version-roll discipline as `adr.md`,
`changelog.md`, and `backlog.md`).
**Supersedes:** the architecture sections of `smithsonian_compiled_report_v3.md`,
`enhancement_plan.md`, `Corpus-specific role assignment.md`, and the technical
slides of `Team1_SmithsonianHackathon2026_v9_REPAIRED_ENHANCED.pptx`.
This document reconciles what the deck *promised* with what is actually built.

---

## 1. One-paragraph summary

R-CT is a governance-aware AI lesson builder for K-12 social-studies teachers.
It runs on **NVIDIA AI Workbench** as a fork of the upstream Hybrid RAG example
project. A FastAPI **chain_server** (LlamaIndex 0.9.44 + Milvus 2.3.1 + e5-large-v2
embeddings) serves a Gradio **chat UI**; a teacher's essential question fans out
to three corpus-tagged retrievals (LOC newspapers, NARA pension files,
Smithsonian objects — the "Evidence Triad"), and a Mistral-family LLM drafts a
lesson around the retrieved sources. Inference is swappable at runtime between
**Cloud** (NVIDIA API Catalog), **Local TGI**, and **Microservice (NIM)**; the
production demo target is a **Brev L40S** instance running a **Mixtral 8x7B
NIM container** via `compose.yaml`. Source data is the six **CC0** datasets in
the Hugging Face `RevolutionCrossroads` organization.

---

## 2. What the user actually interacts with

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser (Workbench-proxy port 10000 → chat app port 8080)          │
│                                                                     │
│  Gradio chat UI — code/chatui/                                      │
│   • converse.py  — chat panel + RAG toggle + inference-mode picker  │
│   • kb.py        — "Upload Documents Here" + Clear Vector DB        │
│   • info.py      — credits/help                                     │
│                                                                     │
│  HTTP → http://localhost:8000  (chain_server)                       │
└─────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  chain_server — code/chain_server/  (api-env, port 8000)            │
│                                                                     │
│  server.py        — FastAPI: /generate, /uploadDocument, /health    │
│  chains.py        — LlamaIndex orchestration:                       │
│    - get_vector_index()                                             │
│    - get_doc_retriever(num_nodes)                                   │
│    - retrieve_evidence_triad(query, top_k)   [NEW]                  │
│    - _parse_frontmatter(text)                [NEW]                  │
│    - ingest_docs(file_path, filename)        [PATCHED]              │
│    - llm_chain_streaming(...)                [PATCHED: stream off   │
│    - rag_chain_streaming(...)                  for cloud + dispatch │
│                                                  refactored]        │
│  chat_templates.py — MISTRAL/LLAMA_3/MICROSOFT/NVIDIA_RAG_TEMPLATE  │
│  nvcf_llm.py      — direct NVCF LLM client (legacy, unused now)     │
│  configuration*.py — @configclass / configfield env-var overrides   │
└─────────────────────────────────────────────────────────────────────┘
            │
            ├──► Milvus :19530          (vector store, 1024-dim e5-large-v2)
            │
            └──► LLM (one of):
                  • Cloud  — https://integrate.api.nvidia.com/v1/   (staging)
                  • Local  — http://127.0.0.1:9090/  (HF text-generation-launcher)
                  • Microservice — http://<nim_ip>:8000/v1/  (NIM container)
```

The "AI Workbench" piece is the runtime: it owns the build (`preBuild.bash`,
`postBuild.bash`), the two conda envs (`api-env`, `ui-env`), GPU allocation,
and the proxy. There is no Make/uv/poetry orchestrator.

---

## 3. The three inference modes — what works today

| Mode | Endpoint | Model used in our testing | VRAM | Streaming | Demo verdict |
|---|---|---|---|---|---|
| **Cloud** | `https://integrate.api.nvidia.com/v1/` | `mistralai/mixtral-8x22b-instruct-v0.1` | 0 (remote) | **Disabled** for cloud only — staging tier dropped streams mid-response, so chain_server now collects the full response and yields once | ✅ Reliable after non-streaming patch; ~15-40s blank screen then full answer |
| **Local TGI** | `http://127.0.0.1:9090/` | Llama-2-7b-chat-hf or similar | ≥12 GB | ✅ | Untested in this session; works on devices with sufficient VRAM |
| **Microservice (NIM)** | `http://localhost:8000/v1/` | `mistralai/mixtral-8x7b-instruct-v0.1` (default) | ≥28 GB | ✅ | Recommended for the demo. Requires Brev L40S or equivalent. Stable streaming. |

**API key surface.** `NVIDIA_API_KEY` is a Workbench secret (`.project/spec.yaml`).
The same key is used as `NGC_API_KEY` for `docker login nvcr.io` to pull NIM
containers. Both interpolated into `compose.yaml` via `${NVIDIA_API_KEY:?...}`
— no hardcoded keys in committed files.

**Known constraint.** The user's NGC key is on the **staging tier**
(`stg/...` model prefix in responses). Mistral 7B v0.3 returned 404 ("function
not found") when tested directly — only Mixtral 8x22B is provisioned for
cloud-mode use. Resolution: switch to Microservice mode on Brev L40S to escape
the staging tier entirely.

---

## 4. Code patches landed in this branch (vs upstream Hybrid RAG)

All committed to `main`, pushed to `origin`. References are to the post-patch
file states.

### 4.1 `code/chain_server/chains.py`

| Addition / change | Purpose |
|---|---|
| `_DEFAULT_NIM_MODEL` constant near other module defaults; reads `NIM_MODEL_ID` env var, defaults to `mistralai/mixtral-8x7b-instruct-v0.1` | Single source of truth for what NIM serves; matches `compose.yaml` default |
| `_FRONTMATTER_RE` + `_parse_frontmatter(text)` | Strip flat-key YAML frontmatter from .md, no PyYAML dep |
| `ingest_docs(file_path, filename)` rewritten | For .md files: bypass UnstructuredReader, parse frontmatter into `Document.metadata` (corpus, source_url, NAID/EDAN/LCCN, dates, etc.), instead of clobbering metadata with `{filename: <base64>}` only. Falls back to filename-prefix corpus tag (`loc_`, `nara_`, `si_`) when frontmatter is missing. |
| `retrieve_evidence_triad(query, top_k=24) -> dict` | Single similarity query with generous `top_k`, group by `corpus` metadata, return top-1 per corpus. Implements the Evidence Triad retrieval pattern on the existing single-collection setup. |
| RAG-template dispatch refactored in `rag_chain_streaming` | Computes `_model_hint` from `nvcf_model_id` (cloud) or `nim_model_id` (microservice, defaulting to `_DEFAULT_NIM_MODEL`), then picks a family-appropriate `chat_templates.*_RAG_TEMPLATE`. **Microservice mode now picks the right Mistral/Llama/Phi template instead of falling through to GENERIC.** |
| `stream=True` → `stream=(inference_mode != "cloud")` everywhere (4 sites) | Cloud non-streaming due to staging-tier flakiness |
| Both `llm_chain_streaming` and `rag_chain_streaming` non-stream branch added | When `inference_mode == "cloud"`, read `completion.choices[0].message.content` and yield the whole answer once; UI receives a single chunk |
| Both hardcoded `"meta/llama-3.1-8b-instruct"` fallbacks → `_DEFAULT_NIM_MODEL` | NIM model id default tracks compose.yaml |

### 4.2 `code/chatui/chat_client.py`

| Change | Purpose |
|---|---|
| `timeout=10` → `timeout=(10, 300)` on the streaming `requests.post` | Fail fast on connect (10s) but allow 5 min for slow first-token / cold-start (Mixtral 8x22B cold-starts in 15-40s) |

### 4.3 `compose.yaml` (NIM compose for Microservice mode)

| Change | Purpose |
|---|---|
| Default `image:` switched to `nvcr.io/nim/mistralai/mixtral-8x7b-instruct-v01:latest` | Same Mistral family as cloud, fits L40S 48 GB |
| Three commented alternatives (Llama 70B, Llama 3.1 8B, Mistral 7B v0.3) | One-line switch for other targets |
| `volumes: /tmp` bind → named volume `nim-cache` | Persistent — model weights survive restart instead of re-downloading 28 GB |
| Added `shm_size: 16gb` | NIMs need more shared memory than Docker default |
| Added `healthcheck` on `/v1/models` | docker compose can tell when the NIM is actually ready (cold-start can be 5-10 min) |
| `${NVIDIA_API_KEY:?Error NVIDIA_API_KEY not set}` | No hardcoded key — fails clearly if env not set |

### 4.4 New helper scripts under `code/scripts/helpers/`

**JSONL files cannot be uploaded into Hybrid RAG through the chat UI.** The
chat UI's "Upload Documents Here" widget POSTs each file to
`chain_server`'s `/uploadDocument` endpoint, which runs LlamaIndex's
`UnstructuredReader`. That reader treats `.json` / `.jsonl` as plain text and
strips the per-row structure — useless for our records. To get JSONL data into
Milvus you have to convert first (option 1) or write to Milvus directly
without the HTTP path (option 2):

| Script | What it does | Output | Use via UI? |
|---|---|---|---|
| `materialize-rc-sample.py` | Option 1. Reservoir-samples N rows per dataset from JSONL → writes per-row `.md` with YAML frontmatter the patched `chain_server` knows how to parse | `data/documents/{loc,nara,si}/` | ✅ user drag-drops the folder |
| `curate_demo_corpus.py` | Option 1. Filters JSONLs for case-bundle veterans (Knox / Wayne / Nathanael Greene) + thematic slices (widow / pension / petition) → 64 `.md` files with frontmatter | `data/documents/curated/` | ✅ user drag-drops the folder |
| `bulk_ingest_jsonl.py` | Option 2. Backfill / power-user path. Reads JSONL, builds `LlamaIndex Document` objects with full metadata, calls `chains.get_vector_index().insert_nodes()` directly. **Bypasses `chain_server` HTTP entirely.** Must be run inside the container with `api-env` python. Not a UI feature. | Milvus directly | ❌ command-line only |
| `materialize-rc-sample.sh` | Thin wrapper for the materializer; tries api-env python, falls back to system python3 | — | — |

---

## 5. Data architecture

### 5.1 Source corpora (Hugging Face, all CC0-1.0)

Verified row counts and sizes from the HF dataset cards (2026-04-23):

| Dataset | Rows | Size | Use in R-CT |
|---|---|---|---|
| `RevolutionCrossroads/loc_chronicling_america_1770-1810` | **58,116 pages** | 164 GB | Primary LOC newspaper page index |
| `RevolutionCrossroads/loc_chronicling_america_1770-1810_issues` | **14,563 issues** | 604 GB | Optional issue-aggregated newspaper layer |
| `RevolutionCrossroads/loc_chronam_textract_ocr_bah` | 22,076 | 528 MB | OCR-comparison overlay for newspapers |
| `RevolutionCrossroads/si_us_revolutionary_era_collections` | **12,667** | 2.5 MB | Smithsonian object index (Evidence Triad: Object) |
| `RevolutionCrossroads/si_images_textlabeling_bah` | 5,218 | 209 kB | Image-text routing helper (admin/QA) |
| `RevolutionCrossroads/nara_revolutionary_war_pension_files` | **2.24 M pages** | 6.32 GB | Page-level pension drill-down |
| `RevolutionCrossroads/nara_revolutionary_war_pension_files_PDFs` | **78,926 files** | 4.23 TB | File-level pension index (Evidence Triad: Testimony) |

**Corrections vs deck v9:** the page-level LOC dataset is **58,116 rows, NOT
340,000** (the 340K figure in the dataset card narrative contradicts the actual
parquet — do not cite). The "3,941 image-bearing SI objects" and "27% NARA
human-transcribed" figures are not stated on the cards; mark as derived/TBD.

### 5.2 Local data layout (this repo)

```
data/
├── sources/revolutioncrossroads/        ← gitignored; 3 active JSONLs
│   ├── loc_textract_ocr.jsonl           (10 000 rows)
│   ├── nara_pension_pdfs.jsonl          ( 4 998 rows)
│   └── si_collections.jsonl             (12 667 rows)
│
├── documents/                            ← gitignored; ingest target dir
│   └── curated/                          ← 64 demo .md (frontmatter)
│
└── scratch/hackathon-smithsonian/        ← gitignored; project bundle
    ├── data/rag_ready/                   ← other 3 JSONLs (loc_newspapers,
    │                                       nara_pension_pages, si_images_labels)
    ├── scripts/                          ← user's pre-existing scripts
    │   ├── download_and_transform.py
    │   └── upload_to_rag.py              (targets CA-RAG, not this project's
    │                                      chain_server — DO NOT use as-is)
    ├── *.md  *.pptx                      ← all design/strategy docs and decks
    ├── sample-lessons/*.docx             ← 8 Smithsonian classroom handouts
    └── workspace/                        ← pptx mockup builders
```

### 5.3 Vector store (Milvus)

| Property | Value |
|---|---|
| Collection name | `llamalection` (single collection — all corpora mixed) |
| Embedding model | `intfloat/e5-large-v2` (HuggingFace), runs on `cuda:0` (`EMBEDDING_DEVICE=cuda:0` in `variables.env`) |
| Dim | 1024 |
| Chunker | `SimpleNodeParser.from_defaults()` |
| Per-chunk metadata (post-patch) | `{filename, corpus, doc_index, source_url, naid|edan_id|lccn, ...per-corpus fields}` |
| Persistence | `/mnt/milvus/` (Workbench volume mount) |

**Multi-collection support is in (v0.3.0):** `chains.get_vector_index` now
accepts an optional `collection_name` parameter. Default behavior (no arg)
hits `llamalection`; pass a name to address a separate per-corpus index.
Per-name results are `lru_cache`d.

**Currently in Milvus:**
- `llamalection` — the curated demo corpus (~64 chunks across LOC / NARA / SI,
  16 demo buckets). NARA chunks are file-level slices from
  `nara_pension_pdfs.jsonl`. Used by `retrieve_evidence_triad()` for the
  Evidence Triad lesson generation.
- `rc_nara_pages` *(scaffolded in v0.3.0; ingest run is RCT-002b)* — the
  page-level companion built by
  `code/scripts/helpers/ingest_nara_pages.py`. One row per pension page,
  filtered to the same case-bundle scope as the demo corpus. Used as the
  citation drill-down layer when teachers want to cite an exact page rather
  than a whole pension file.

**Comparison study (RCT-006):** `code/scripts/helpers/study_nara_comparison.py`
runs a fixed prompt suite against both collections, records top-K retrieval
per collection (snippet, score, NAID, page hint), and writes a side-by-side
report. Summary reports mean top-1 similarity, retrieval latency, and NAID
overlap percentage — the deck-side evidence that the two granularities
serve different stages of the lesson workflow.

**Future per-corpus splits** (`rc_loc`, `rc_si`, `rc_nara_files`) follow the
same pattern; deferred until the comparison-study run validates the
approach. ADR-008.

---

## 6. The Evidence Triad retrieval pattern

```
teacher essential question
        │
        ▼
e5-large-v2 embedding (1024-dim, cuda:0)
        │
        ▼
Milvus similarity search   ── top_k = 24
        │
        ▼
group by metadata.corpus
        │
        ├── corpus="loc"   → top-1   "Coverage"  (newspaper page)
        ├── corpus="nara"  → top-1   "Testimony" (pension file)
        └── corpus="si"    → top-1   "Object"    (Smithsonian artifact)
        │
        ▼
3-source evidence packet (text + source_url + ids + score)
        │
        ▼
chat_templates.MISTRAL_RAG_TEMPLATE.format(
    context_str=", ".join(triad),
    query_str=essential_question)
        │
        ▼
LLM (current: Mixtral 8x22B cloud, target: Mixtral 8x7B NIM on L40S)
        │
        ▼
lesson draft (markdown, with citations to each of the 3 sources)
```

Provenance is preserved end-to-end: every retrieved chunk carries its
`source_url`, NAID/EDAN/LCCN, and corpus tag in `Document.metadata`, so the
generated lesson can cite back to the canonical Smithsonian / LOC / NARA URL.

---

## 7. Deployment paths

### 7.1 Local (NVIDIA AI Workbench on Windows + WSL)

The development setup. Workbench owns build + run via `.project/spec.yaml`. GPU
is the host's RTX 2080 Ti (11 GB VRAM) — sufficient for embedding (e5-large-v2
≈ 1.3 GB on cuda:0) but **not for any local LLM larger than Llama 3.1 8B / Mistral
7B**. Cloud mode is therefore the only realistic chat backend on this host —
which is why we hit the staging-tier streaming issue and patched non-streaming.

### 7.2 Production demo target — Brev L40S (48 GB VRAM)

The intended demo box. L40S has enough VRAM for Mixtral 8x7B FP16 (~28 GB) or
Llama 3.1 70B INT4 (~40 GB) NIM containers. Ingest:

```bash
# On the Brev box, after `brev shell <instance>` and `claude` install:
git clone https://github.com/keith-mvs/workbench-example-hybrid-rag.git
cd workbench-example-hybrid-rag

export NVIDIA_API_KEY=nvapi-...
docker login nvcr.io --username '$oauthtoken' --password "$NVIDIA_API_KEY"
docker compose -f compose.yaml up -d local-nim
docker compose -f compose.yaml logs -f local-nim   # ~5–10 min weight pull
curl http://localhost:8000/v1/models               # readiness check

# In the chat UI: Mode = Microservice, IP = localhost, port = 8000.
# Leave nim_model_id blank — chains.py uses _DEFAULT_NIM_MODEL.
```

This sidesteps the cloud staging tier entirely. Streams reliably.

---

## 8. The teacher UX (mockup → live)

The reference UI is `data/scratch/hackathon-smithsonian/ui_mockup.html` — a
single screen showing:

- **Header** — branding, breadcrumbs, teacher profile
- **Lesson header** — essential question + grade / subject / duration / class size
- **Template card** — based on a Smithsonian classroom handout (KWL Chart, 3-2-1
  Notes, Read an Object, Venn Diagram, etc. — the eight `.docx` in
  `sample-lessons/`)
- **Three primary source cards** — color-coded Testimony (NARA, red),
  Coverage (LOC, purple), Object (SI, cyan); each shows title, attribution,
  and a 1-line quote
- **Lesson pack** — 5-step time-budgeted activity sequence
- **Right sidebar — "Classroom-ready" checklist** — sources are public domain,
  reading level matches grade, every quote is cited, optional teacher heads-up

That right-sidebar checklist is **the teacher-facing surface of the governance
ledger** described in §9.

**Current status:** the mockup is static HTML. None of the form inputs or
buttons are wired to chain_server. Wiring it up — a small FastAPI app at
`code/lesson_app/` that serves the mockup as a Jinja template, hits
`retrieve_evidence_triad`, then `/generate` with a lesson-template prompt — is
the prototype-dashboard work item.

---

## 9. Governance / control plane (planned, not built)

The deck's "GPT-Ledger" claim is **conceptual only — not implemented**. The
smallest useful first version would be:

```python
# governance/ledger.py
def log_event(session_id, essential_question, grade_band, template,
              retrieved_corpora, retrieved_ids, model, prompt_hash,
              response_hash, checks: dict) -> None:
    """Append one entry to governance_ledger.jsonl (chained SHA-256)."""
```

Per-entry record (target schema):

```json
{
  "ts": "2026-05-06T18:42:11.103Z",
  "session_id": "uuid-...",
  "essential_question": "...",
  "grade_band": "8",
  "template": "KWL",
  "retrieved_corpora": ["loc", "nara", "si"],
  "retrieved_ids": [
      "lccn:sn83021188#1809-07-08-p1",
      "naid:111512786",
      "edanmdm:nmah_1097221"
  ],
  "model": "mistralai/mixtral-8x7b-instruct-v0.1",
  "prompt_hash": "sha256:...",
  "response_hash": "sha256:...",
  "prev_hash": "sha256:...",
  "checks": {
      "all_cc0_or_public": true,
      "every_quote_cited": true,
      "evidence_sufficient": true,
      "reading_level_target": "Grade 8",
      "reading_level_estimated": "Grade 9",
      "ocr_low_confidence_flagged": false,
      "culturally_sensitive_terms_flagged": [],
      "geographic_coverage_gaps": ["South"],
      "demographic_caveats": ["officer-heavy sample"]
  }
}
```

Surface in UI: those `checks` populate the Classroom-ready checklist on the
right sidebar of `ui_mockup.html`. The Smithsonian's three AI values
(innovation / transparency / responsibility) and the four OECD principles
(fairness / transparency / robustness / accountability) map onto specific
check fields, which is what makes the system "OECD-aligned" in a measurable
sense rather than a slogan.

---

## 10. What's NOT in the system (honest gap list)

The deck and supplementary docs reference these as if implemented; they are
not. They belong in "Phase 2/3" framing or should be cut from the v10 deck.

| Claimed | Reality | Path to close |
|---|---|---|
| Three Milvus indexes | One collection with corpus metadata tag | Add per-corpus collections in `chains.get_vector_index(corpus=)`, ingest separately |
| GPT-Ledger / SHA-256 audit trail | Not implemented | Sketch in §9; ~half a day to scaffold |
| PII redaction before LLM | Not implemented | None of our corpora contain modern PII; relevant only when teacher-typed input enters audit log |
| PDF/DOCX export | UI buttons; no backend | Use `python-docx` + `weasyprint`; output to a download dir |
| Learning Lab deep-link export | Not implemented | Construct `learninglab.si.edu` search URLs with EDAN ids |
| Trust panel / classroom-readiness checks | UI mockup only | Wire to the (planned) governance ledger's `checks` field |
| Reading-level estimation | Not implemented | Use `textstat` library (Flesch-Kincaid grade) |
| Cultural-sensitivity flagging | Not implemented | Curated keyword list + LLM-as-judge call |
| Image embeddings for SI objects | Not implemented; pipeline is text-only | Add CLIP/SigLIP encoder + parallel Milvus collection + fused retriever |
| LMS / LTI / SSO integration | Not implemented | Out of scope for hackathon |
| Smithsonian Learning Lab API integration | **No public SLL API exists** (verified, see `learning_lab_integration_research.md`) | Frame as future partnership conversation, not deliverable |

---

## 11. Naming and style — pick one, use everywhere

| Field | Canonical |
|---|---|
| Product name | **Revolution Crossroads Teacher (R-CT)** — short form for body text; full form on title slide |
| Pedagogy | **Evidence Triad** (Testimony · Coverage · Object) |
| Story hook | **Economy Dashboard** — what did the war cost different people? |
| Initiative name | **Revolution Crossroads** (Smithsonian's; capitalize R, C, no hyphen) |
| Hackathon | **Women in AI × Smithsonian Hackathon 2026**, Track 1 — Teacher Toolkits & Classroom Innovation |

---

## 12. Code change index (for reviewers)

| File | Lines touched | Substance |
|---|---|---|
| `code/chain_server/chains.py` | ~120 lines added/changed across 5 sites | _DEFAULT_NIM_MODEL, _parse_frontmatter, ingest_docs rewrite, retrieve_evidence_triad, RAG-template dispatch, non-streaming cloud branch |
| `code/chatui/chat_client.py` | 1 line + comment | streaming-request timeout (10, 300) |
| `compose.yaml` | full rewrite (~70 lines) | Mixtral 8x7B default, named volume, shm_size, healthcheck, env-var key |
| `code/scripts/helpers/materialize-rc-sample.py` | new file (~120 lines) | YAML frontmatter materialization |
| `code/scripts/helpers/curate_demo_corpus.py` | new file (~190 lines) | Veteran/theme curation |
| `code/scripts/helpers/bulk_ingest_jsonl.py` | new file (~140 lines) | Direct JSONL→Milvus ingest |
| `code/scripts/materialize-rc-sample.sh` | new file (8 lines) | Wrapper |
| `.gitignore` | +2 lines | `data/sources/*` ignored |
| `variables.env` | 1 line | `EMBEDDING_DEVICE=cuda:0` (was cpu) |

---

## 13. Quick-start for someone new to the project

```bash
# In the chat UI (running on localhost:8080 via Workbench):
#  1. Click "Set up RAG Backend" — starts chain_server + Milvus
#  2. In the right panel, drag-drop data/documents/curated/ (64 .md files)
#  3. Wait for "Toggle to Use Vector Database" to enable
#  4. Pick inference mode:
#     - Cloud + Mixtral 8x22B (works after non-streaming patch)
#     - Microservice + (NIM model id) (only on L40S+)
#  5. Ask a lesson-plan question (see deck-v10-outline.md §4 for examples)

# To re-curate the demo corpus:
python3 code/scripts/helpers/curate_demo_corpus.py

# To bulk-ingest JSONL directly (skips UI upload, runs inside container):
docker exec project-hybrid-rag $HOME/.conda/envs/api-env/bin/python \
    /project/code/scripts/helpers/bulk_ingest_jsonl.py \
    --jsonl /project/data/sources/revolutioncrossroads/si_collections.jsonl \
    --filter-name "Henry Knox" --max 8
```

---

*This document is the source of truth. When the deck and this disagree, this
wins; the deck and other docs are aspirational positioning that needs to either
be implemented or rephrased as Phase-2/3 framing.*
