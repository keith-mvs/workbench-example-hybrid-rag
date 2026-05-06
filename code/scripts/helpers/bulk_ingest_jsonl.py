"""Bulk-ingest JSONL rows directly into Milvus via chain_server's chains.py.

Bypasses chain_server's HTTP /uploadDocument round-trip entirely: reads JSONL,
constructs LlamaIndex Documents with full metadata (corpus, source_url,
naid/edan_id/lccn, etc.), parses them with SimpleNodeParser, and inserts to
Milvus through the same get_vector_index() the chat path uses.

Must be run inside the Workbench container with the api-env python so the
LlamaIndex / pymilvus / sentence-transformers stack is available:

    docker exec project-hybrid-rag $HOME/.conda/envs/api-env/bin/python \\
        /project/code/scripts/helpers/bulk_ingest_jsonl.py \\
        --jsonl /project/data/sources/revolutioncrossroads/si_collections.jsonl \\
        --filter-name "Henry Knox" --max 8

Flags:
    --jsonl PATH         JSONL file to read (repeatable for multiple files)
    --corpus loc|nara|si Override corpus tag; defaults to inferred from filename
    --filter-name STR    Only ingest rows whose body contains this string
    --max N              Cap rows per JSONL after filtering (0 = unlimited)
    --dry-run            Build documents and print counts but do not insert
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make /project/code importable as a package root
sys.path.insert(0, "/project/code")

from chain_server import chains  # noqa: E402
from llama_index import Document  # noqa: E402
from llama_index.node_parser import SimpleNodeParser  # noqa: E402


CORPUS_FROM_FILENAME = {
    "loc_textract_ocr.jsonl": "loc",
    "loc_newspapers.jsonl": "loc",
    "nara_pension_pdfs.jsonl": "nara",
    "nara_pension_pages.jsonl": "nara",
    "si_collections.jsonl": "si",
    "si_images_labels.jsonl": "si",
}


def _infer_corpus(p: Path, override: str | None) -> str:
    if override:
        return override
    return CORPUS_FROM_FILENAME.get(p.name, "unknown")


def _row_to_document(row: dict, corpus: str) -> Document | None:
    text = (row.get("document") or "").strip()
    if not text:
        return None
    md = row.get("doc_metadata", {}) or {}
    metadata = {
        "corpus": corpus,
        "doc_index": row.get("doc_index"),
    }
    for k in (
        "source_title", "source_url", "doc_id", "naid", "edan_id",
        "lccn", "newspaper_title", "issue_date", "page", "has_textract",
        "num_pages", "pdf_url", "extracted_text_contributor",
        "unit_code", "indexed_dates", "indexed_names",
        "indexed_places", "indexed_topics", "thumbnail",
    ):
        v = md.get(k)
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v[:8])
        metadata[k] = str(v)
    return Document(text=text, metadata=metadata)


def _iter_rows(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--jsonl", action="append", required=True,
                    help="JSONL file to ingest (repeatable)")
    ap.add_argument("--corpus", choices=("loc", "nara", "si"))
    ap.add_argument("--filter-name", action="append", default=[],
                    help="Only rows whose body contains this string (repeatable; OR-joined)")
    ap.add_argument("--max", type=int, default=0,
                    help="Cap rows per JSONL after filtering (0 = unlimited)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    documents: list[Document] = []
    for jsonl in args.jsonl:
        p = Path(jsonl)
        if not p.exists():
            print(f"[skip] {p} not found", file=sys.stderr)
            continue
        corpus = _infer_corpus(p, args.corpus)
        kept = 0
        for row in _iter_rows(p):
            text = row.get("document", "")
            if args.filter_name and not any(
                f.lower() in text.lower() for f in args.filter_name
            ):
                continue
            doc = _row_to_document(row, corpus)
            if doc is None:
                continue
            documents.append(doc)
            kept += 1
            if args.max and kept >= args.max:
                break
        print(f"[{corpus}] {p.name}: {kept} rows queued")

    if not documents:
        print("No rows matched. Nothing to ingest.")
        return 1

    parser = SimpleNodeParser.from_defaults()
    nodes = parser.get_nodes_from_documents(documents)
    print(f"\n{len(documents)} documents -> {len(nodes)} chunks")

    if args.dry_run:
        print("[dry-run] not inserting")
        return 0

    index = chains.get_vector_index()
    index.insert_nodes(nodes)
    print(f"Inserted {len(nodes)} chunks into Milvus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
