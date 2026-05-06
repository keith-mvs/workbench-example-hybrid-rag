"""Curate a demo-grade subset of the RevolutionCrossroads JSONLs.

Picks rows that mention specific case-bundle veterans (Knox, Wayne, Nathanael
Greene) plus a small thematic slice (widow / pension / petition), writes them
as .md files with YAML frontmatter into a single flat folder
(/project/data/documents/curated/) so the user can drag-drop the whole folder
into the Gradio chat UI's upload widget. The flat layout is deliberate.

The .md frontmatter format matches what code/chain_server/chains.py
(_parse_frontmatter + ingest_docs) now consumes, so once the chain_server has
reloaded, ingested chunks will carry queryable corpus/source_url/id metadata
and retrieve_evidence_triad() will work as designed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# --- Paths (resolve so the script works inside the container or on the host) -
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCES_A = PROJECT_ROOT / "data" / "sources" / "revolutioncrossroads"
SOURCES_B = (
    PROJECT_ROOT
    / "data"
    / "scratch"
    / "hackathon-smithsonian"
    / "data"
    / "rag_ready"
)
OUT_DIR = PROJECT_ROOT / "data" / "documents" / "curated"

# (jsonl filename, corpus tag) — both source dirs are searched.
INPUTS = [
    ("loc_textract_ocr.jsonl", "loc"),
    ("nara_pension_pdfs.jsonl", "nara"),
    ("si_collections.jsonl", "si"),
    ("loc_newspapers.jsonl", "loc"),
    ("nara_pension_pages.jsonl", "nara"),
    ("si_images_labels.jsonl", "si"),
]

# Per-veteran case bundle. First-match wins when a row mentions several.
VETERANS = [
    ("knox", "Henry Knox"),
    ("wayne", "Anthony Wayne"),
    ("ngreene", "Nathanael Greene"),
]

# Thematic catch-all so the home-front / widow / pension lessons have material
# even when no named veteran appears.
THEMES = [
    ("widow", re.compile(r"\bwidow(s|er|s'|'s)?\b", re.I)),
    ("petition", re.compile(r"\bpetition(s|ed|er|ers)?\b", re.I)),
    ("pension", re.compile(r"\bpension(s|er|ers|ary|ed)?\b", re.I)),
]

# Caps to keep the curated set small enough to drag-drop confidently.
PER_VETERAN_PER_CORPUS_CAP = 6
THEME_PER_CORPUS_CAP = 3

# --- Frontmatter writer (mirrors materialize-rc-sample.py) -------------------
_FRONTMATTER_FIELDS_BY_CORPUS = {
    "loc": ("source_title", "source_url", "doc_id", "lccn",
            "newspaper_title", "issue_date", "page", "has_textract"),
    "nara": ("source_title", "source_url", "doc_id", "naid",
             "num_pages", "pdf_url", "extracted_text_contributor"),
    "si": ("source_title", "source_url", "doc_id", "edan_id", "unit_code",
           "indexed_dates", "indexed_names", "indexed_places",
           "indexed_topics", "thumbnail"),
}

_slug_re = re.compile(r"[^a-zA-Z0-9._-]+")


def _slug(value, max_len: int = 50) -> str:
    s = _slug_re.sub("-", str(value)).strip("-")
    return s[:max_len] or "x"


def _yaml_scalar(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        v = ", ".join(str(x) for x in v[:8])
    s = str(v).replace("\n", " ").strip()
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _format_doc(row: dict, corpus: str, bucket: str) -> str:
    body = row.get("document", "").rstrip()
    md = row.get("doc_metadata", {}) or {}
    fm = {
        "corpus": corpus,
        "doc_index": row.get("doc_index"),
        "demo_bucket": bucket,
    }
    for k in _FRONTMATTER_FIELDS_BY_CORPUS.get(corpus, ()):
        v = md.get(k)
        if v in (None, "", [], {}):
            continue
        fm[k] = v
    out = ["---"]
    for k, v in fm.items():
        out.append(f"{k}: {_yaml_scalar(v)}")
    out.append("---")
    return "\n".join(out) + "\n\n" + body + "\n"


def _classify(doc_text: str) -> str | None:
    """Return the bucket name for this row (veteran slug, theme name, or None)."""
    if not doc_text:
        return None
    for slug, full in VETERANS:
        if full.lower() in doc_text.lower():
            return slug
    for slug, pattern in THEMES:
        if pattern.search(doc_text):
            return slug
    return None


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def main() -> None:
    if OUT_DIR.exists():
        for f in OUT_DIR.iterdir():
            if f.is_file() and f.suffix == ".md":
                f.unlink()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # bucket -> corpus -> list[(score, row, source_filename)]
    buckets: dict = {}
    seen: set = set()  # (corpus, doc_index) for dedup across the two source dirs

    for fname, corpus in INPUTS:
        for src_dir in (SOURCES_A, SOURCES_B):
            p = src_dir / fname
            if not p.exists():
                continue
            for row in _iter_jsonl(p):
                idx = row.get("doc_index")
                key = (corpus, idx)
                if key in seen:
                    continue
                bucket = _classify(row.get("document", ""))
                if not bucket:
                    continue
                seen.add(key)
                score = len(row.get("document", ""))  # prefer richer rows
                buckets.setdefault(bucket, {}).setdefault(corpus, []).append(
                    (score, row, fname)
                )

    # Apply caps + write
    is_veteran = {v[0] for v in VETERANS}
    summary = []
    written = 0
    for bucket, by_corpus in buckets.items():
        cap = PER_VETERAN_PER_CORPUS_CAP if bucket in is_veteran else THEME_PER_CORPUS_CAP
        for corpus, items in by_corpus.items():
            items.sort(key=lambda x: -x[0])
            for score, row, fname in items[:cap]:
                md_text = _format_doc(row, corpus, bucket)
                idx = row.get("doc_index", "x")
                meta = row.get("doc_metadata", {}) or {}
                hint = (meta.get("naid") or meta.get("edan_id") or
                        meta.get("lccn") or "")
                fname_out = (
                    f"{corpus}_{bucket}_{idx:07d}_{_slug(hint)}.md"
                    if isinstance(idx, int)
                    else f"{corpus}_{bucket}_{_slug(idx)}_{_slug(hint)}.md"
                )
                (OUT_DIR / fname_out).write_text(md_text, encoding="utf-8")
                written += 1
            summary.append((bucket, corpus, len(items[:cap]), len(items)))

    print(f"\nWrote {written} files to {OUT_DIR}\n")
    print(f"{'bucket':<12} {'corpus':<6} {'kept':>5}  {'available':>10}")
    print("-" * 40)
    for bucket, corpus, kept, total in sorted(summary):
        print(f"{bucket:<12} {corpus:<6} {kept:>5}  {total:>10}")
    print()
    print("Next: drag-drop the curated/ folder into the chat UI's "
          "'Upload Documents Here' widget after clearing the existing "
          "vector DB.")


if __name__ == "__main__":
    main()
