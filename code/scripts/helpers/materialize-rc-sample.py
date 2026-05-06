"""Materialize a random sample of RevolutionCrossroads JSONL rows as .md files.

Reads the three prepared corpora from /project/data/sources/revolutioncrossroads/
and writes a sampled subset of rows as individual markdown files into
/project/data/documents/{loc,nara,si}/, where the existing upload-docs.sh
pipeline will pick them up and feed them through the chain_server -> Milvus
ingest path.

Sample size per dataset is controlled by the RC_SAMPLE_SIZE env var
(default 25). Sampling is seeded for reproducibility.
"""
from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path

# Resolve paths relative to this file so the script works both inside the
# Workbench container (/project/...) and from the host WSL distro.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCES_DIR = PROJECT_ROOT / "data" / "sources" / "revolutioncrossroads"
DOCS_DIR = PROJECT_ROOT / "data" / "documents"
SEED = 42

DATASETS = {
    "loc": {
        "file": "loc_textract_ocr.jsonl",
        "title_keys": ("newspaper_title", "issue_date", "page"),
    },
    "nara": {
        "file": "nara_pension_pdfs.jsonl",
        "title_keys": ("source_title", "naid"),
    },
    "si": {
        "file": "si_collections.jsonl",
        "title_keys": ("source_title", "edan_id"),
    },
}

_slug_re = re.compile(r"[^a-zA-Z0-9._-]+")


def _slug(value: str, max_len: int = 60) -> str:
    s = _slug_re.sub("-", str(value)).strip("-")
    return s[:max_len] or "untitled"


_FRONTMATTER_FIELDS_BY_CORPUS = {
    "loc": ("source_title", "source_url", "doc_id", "lccn",
            "newspaper_title", "issue_date", "page", "has_textract"),
    "nara": ("source_title", "source_url", "doc_id", "naid",
            "num_pages", "pdf_url", "extracted_text_contributor"),
    "si": ("source_title", "source_url", "doc_id", "edan_id", "unit_code",
            "indexed_dates", "indexed_names", "indexed_places", "indexed_topics",
            "thumbnail"),
}


def _yaml_scalar(v) -> str:
    """Emit a value as a safe YAML scalar (always quoted strings to keep parsing trivial)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        v = ", ".join(str(x) for x in v[:8])
    s = str(v).replace("\n", " ").strip()
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _format_doc(row: dict, source_key: str) -> str:
    """Build the markdown: YAML frontmatter (queryable metadata) + body text."""
    body = row.get("document", "").rstrip()
    md = row.get("doc_metadata", {}) or {}

    fm = {
        "corpus": source_key,
        "doc_index": row.get("doc_index"),
    }
    for k in _FRONTMATTER_FIELDS_BY_CORPUS.get(source_key, ()):
        v = md.get(k)
        if v in (None, "", [], {}):
            continue
        fm[k] = v

    fm_lines = ["---"]
    for k, v in fm.items():
        fm_lines.append(f"{k}: {_yaml_scalar(v)}")
    fm_lines.append("---")
    return "\n".join(fm_lines) + "\n\n" + body + "\n"


def _sample(jsonl_path: Path, n: int) -> list[dict]:
    """Reservoir-sample n rows so we don't have to load the whole file."""
    rng = random.Random(SEED)
    reservoir: list[dict] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            row = json.loads(line)
            if i < n:
                reservoir.append(row)
            else:
                j = rng.randint(0, i)
                if j < n:
                    reservoir[j] = row
    return reservoir


def main() -> None:
    sample_size = int(os.environ.get("RC_SAMPLE_SIZE", "25"))
    written_total = 0
    for key, cfg in DATASETS.items():
        src = SOURCES_DIR / cfg["file"]
        if not src.exists():
            print(f"[skip] {src} not found")
            continue
        out_dir = DOCS_DIR / key
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = _sample(src, sample_size)
        # doc_index is per-row and unique within a dataset; doc_id/naid/edan_id
        # may repeat (e.g. doc_id is a stream id shared across rows), so always
        # lead the filename with doc_index and append a readable hint.
        for row in rows:
            md = row.get("doc_metadata", {}) or {}
            idx = row.get("doc_index", "x")
            hint = md.get("naid") or md.get("edan_id") or md.get("lccn") or md.get("source_title") or ""
            suffix = f"_{_slug(hint)}" if hint else ""
            fname = f"{key}_{int(idx):07d}{suffix}.md" if isinstance(idx, int) else f"{key}_{_slug(idx)}{suffix}.md"
            (out_dir / fname).write_text(_format_doc(row, key), encoding="utf-8")
        print(f"[{key}] wrote {len(rows)} files to {out_dir}")
        written_total += len(rows)
    print(f"\nTotal materialized: {written_total} files (sample size {sample_size}/dataset, seed {SEED})")
    print(f"Next: bash /project/code/scripts/upload-docs.sh  (chain_server must be running)")


if __name__ == "__main__":
    main()
