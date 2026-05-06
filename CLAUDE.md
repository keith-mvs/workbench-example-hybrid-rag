# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Scope and authoritative references

This project is the **Hybrid RAG** AI Workbench example: a Gradio chat UI in front of a FastAPI/LlamaIndex chain server, backed by Milvus, with three swappable inference modes (NVIDIA API Catalog cloud, local TGI, NIM microservice).

Before diving in, also read:
- `../CLAUDE.md` — workspace-level instructions (this project lives inside a multi-project workspace).
- `../.github/copilot-instructions.md` — the deepest reference for this project: full env-var matrix, mode-switching details, and template patterns. Treat it as canonical when it conflicts with anything below.
- `README.md` — user-facing setup and tutorials (Quickstart, Advanced Tutorials, Troubleshooting).
- `DOCMARK_INTEGRATION.md` and `.env.docmark` — the optional docmark preprocessing add-on (separate from upstream Hybrid RAG).

## How this project runs

There is no Make/uv/poetry orchestrator. AI Workbench owns the lifecycle:

1. `preBuild.bash` installs apt deps, sets timezone, creates `/mnt/docs/`.
2. `postBuild.bash` creates **two conda envs** (`api-env` for `chain_server`, `ui-env` for `chatui`), creates `/mnt/milvus/` and `/data/`, installs git-lfs.
3. Workbench launches the `chat` app via `.project/spec.yaml`:
   `cd /project/code/ && PROXY_PREFIX=$PROXY_PREFIX $HOME/.conda/envs/ui-env/bin/python3 -m chatui` on port 8080.
4. The user clicks **Set up RAG Backend** in the Gradio UI, which spawns the chain server (FastAPI) and Milvus.

Always invoke Python through the matching conda env — the two envs pin **different torch versions** intentionally:

```bash
$HOME/.conda/envs/api-env/bin/python ...   # chain_server side (torch 2.5.0)
$HOME/.conda/envs/ui-env/bin/python ...    # chatui side       (torch 2.1.1)
```

### Common commands

```bash
# Health checks
curl http://localhost:8080/                          # chatui (Gradio)
curl http://localhost:19530/v1/vector/collections    # Milvus
curl http://localhost:9090/info                      # local TGI inference (mode = Local)
curl http://localhost:8000/                          # local NIM (mode = Microservice)

# Document upload / DB ops (run inside Workbench container)
bash /project/code/scripts/upload-docs.sh
bash /project/code/scripts/clear-docs.sh
bash /project/code/scripts/check-database.sh         # waits for Milvus on :19530

# Local TGI inference server (HF model id required, quantization optional)
bash /project/code/scripts/start-local.sh meta-llama/Llama-2-7b-chat-hf none
bash /project/code/scripts/stop-local.sh

# NIM microservice (Mode = Microservice)
docker-compose -f compose.yaml up -d local-nim
docker-compose -f compose.yaml down

# Optional: docmark preprocessing
export DOCMARK_PREPROCESS=true
export DOCMARK_SERVER_URL=http://host.docker.internal:8001   # WSL→Windows host
bash /project/code/scripts/preprocess-docs.sh
```

There is no test suite in this project.

## Architecture: file roles are strict

Don't conflate these — features go in specific places:

| File | Role |
|---|---|
| `code/chain_server/server.py` | FastAPI endpoints (`/generate`, document upload, etc.). Pydantic request models live here. |
| `code/chain_server/chains.py` | LlamaIndex orchestration: embedding model, vector store wiring, query engine, postprocessors. The `set_service_context()` call switches inference modes. |
| `code/chain_server/chat_templates.py` | **Register new model prompt templates here.** Do NOT hardcode prompts in `chains.py`. |
| `code/chain_server/configuration.py` + `configuration_wizard.py` | `@configclass` / `configfield` config with env-var overrides. Add new config knobs here, not as ad-hoc `os.environ` reads scattered through chains. |
| `code/chain_server/nvcf_llm.py` | Cloud (NVIDIA API Catalog) LLM client. |
| `code/chain_server/trt_llm.py` | TensorRT-LLM client (currently commented out in `chains.py`). |
| `code/chatui/__main__.py` + `pages/*.py` | Gradio app entry and page components (`converse.py`, `kb.py`, `info.py`). |
| `code/chatui/chat_client.py` | HTTP client the UI uses to call the chain server. UI does not import chain code directly. |
| `code/chatui/api.py` | FastAPI surface that wraps Gradio for proxy/health. |
| `code/scripts/helpers/` | Standalone Python helpers invoked by the `*.sh` scripts (`docs.py`, `upload-docs.py`, `setup.py`, `docmark_client.py`). |

### Inference modes (runtime-switchable from the UI)

The UI sends `inference_mode` plus mode-specific fields in every `Prompt`:

- **Cloud** — uses `NVIDIA_API_KEY` (Workbench secret). Routes through `nvcf_llm.py`.
- **Local** — Hugging Face TGI on `127.0.0.1:9090`. Started by `code/scripts/start-local.sh`. Needs 12 GB+ VRAM; gated HF models require explicit access and `HUGGING_FACE_HUB_TOKEN`. Cold start downloads ~7 GB for a 7B model.
- **Microservice** — NIM container started by `compose.yaml` on port 8000. Needs 24 GB+ VRAM. The compose service joins network `hybrid-rag` and mounts `/tmp` as the NIM cache.

`compose.yaml`'s `local-nim` service requires `NGC_API_KEY` in its `environment:` block to pull from `nvcr.io`. That key currently lives in the file — treat any change there as touching a secret.

### Storage and paths

- `/data/` — `HUGGINGFACE_HUB_CACHE`. Created by `postBuild.bash`.
- `/mnt/milvus/` — Milvus persistent volume. Created by `postBuild.bash`.
- `/mnt/docs/` — input docs mount. Created by `preBuild.bash`.
- `/project/` — bind-mount of the repo root inside the Workbench container.
- `data/documents/` — `gitignore`d by spec; user-uploaded source docs.

Reference these paths rather than introducing new ones.

## Pitfalls specific to this project

- **`setuptools<71` is pinned in `api-env` on purpose.** `llama-index==0.9.44` imports `pkg_resources`, removed in setuptools ≥ 71. Don't bump setuptools without also upgrading llama_index (which is a non-trivial migration to the new `llama_index.core` namespace).
- **Two torch versions are not a mistake.** `api-env` is on 2.5.0 (sentence-transformers / TGI client compat); `ui-env` is on 2.1.1 (gradio 4.15 compat). Don't unify them.
- **GPU is required** for Local mode; CPU-only is unsupported.
- **Milvus startup races chain_server** — first-start "DB not ready" errors are usually timing; `check-database.sh` is the canonical wait.
- **`variables.env` is committed.** Only commit-safe defaults belong there. Real secrets (`NVIDIA_API_KEY`, `HUGGING_FACE_HUB_TOKEN`, `NGC_API_KEY`) belong in Workbench secrets, not this file. The `local-nim` service in `compose.yaml` is the existing exception — be deliberate about it.
- **Gradio app is mounted under `$PROXY_PREFIX`** when run inside Workbench. Adding routes to `chatui/api.py` requires respecting the prefix (see how `__main__.py` builds it).
- **Docmark integration is optional and off by default** (`DOCMARK_PREPROCESS=false`). It targets a remote MCP server (typically on the Windows host when running in WSL). Don't assume it's available; the upload pipeline must still work without it.
