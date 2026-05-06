#!/bin/bash
# Materialize a random sample of RevolutionCrossroads JSONL rows into
# data/documents/{loc,nara,si}/ so upload-docs.sh can ingest them.
# Override the per-dataset sample size with RC_SAMPLE_SIZE.
# Pure-stdlib script: prefer the api-env python inside Workbench, fall back
# to system python3 when running on the host.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$HOME/.conda/envs/api-env/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"
"$PY" "$SCRIPT_DIR/helpers/materialize-rc-sample.py"
