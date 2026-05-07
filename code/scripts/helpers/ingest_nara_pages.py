"""Build the page-level NARA Milvus collection (rc_nara_pages) — RCT-002.

Companion to the file-level NARA chunks already in `llamalection`. Same JSONL
shape (`document` / `doc_index` / `doc_metadata`) but each row is a single
pension-file *page* rather than a whole file. Used by the comparison study
(RCT-006) and as the citation drill-down layer at lesson-build time.

By default we filter to the same case-bundle scope as the demo corpus so the
two collections are comparable apples-to-apples (Knox / Wayne / Nathanael
Greene + widow / petition / pension). Override with --max-rows or
--filter-name "" to widen the scope.

Run inside the Workbench container with the api-env python so e5-large-v2
and pymilvus are available:

    docker exec project-hybrid-rag bash -c '
      cd /project/code &&
      $HOME/.conda/envs/api-env/bin/python \\
        /project/code/scripts/helpers/ingest_nara_pages.py \\
        --max-rows 1500 --batch-size 32
    '

DOES NOT touch the existing `llamalection` collection. Rerunnable; existing
rc_nara_pages rows will get duplicate inserts unless you drop the collection
first (use --drop-first to do that explicitly).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

# Make /project/code importable as a package root
sys.path.insert(0, "/project/code")

from chain_server import chains  # noqa: E402
from llama_index import Document, ServiceContext, set_global_service_context  # noqa: E402
from llama_index.node_parser import SimpleNodeParser  # noqa: E402
from llama_index.vector_stores import MilvusVectorStore  # noqa: E402

DEFAULT_JSONL = Path(
    "/project/data/scratch/hackathon-smithsonian/data/rag_ready/"
    "nara_pension_pages.jsonl"
)
COLLECTION_NAME = "rc_nara_pages"

DEFAULT_FILTERS = (
    "Henry Knox", "Anthony Wayne", "Nathanael Greene",
    "widow", "petition", "pension",
)


def _matches(text: str, filters: tuple[str, ...]) -> str | None:
    """Return the matched filter (lowercased) or None."""
    if not filters:
        return ""  # no-filter mode: include everything
    low = text.lower()
    for f in filters:
        if f.lower() in low:
            return f.lower().replace(" ", "-")
    return None


def _row_to_document(row: dict, demo_bucket: str) -> Document | None:
    text = (row.get("document") or "").strip()
    if not text:
        return None
    md = row.get("doc_metadata", {}) or {}
    metadata: dict = {
        "corpus": "nara",
        "granularity": "page",
        "demo_bucket": demo_bucket or "all",
        "doc_index": str(row.get("doc_index", "")),
    }
    for k in (
        "source_title", "source_url", "doc_id", "naid", "naraURL",
        "logicalDate", "page", "pageURL", "pageObjectId",
        "extractedTextID", "extractedTextDate", "extractedTextContributor",
        "transcriptionID", "transcriptionDate",
    ):
        v = md.get(k)
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v[:8])
        metadata[k] = str(v)
    return Document(text=text, metadata=metadata)


def _ensure_service_context() -> None:
    """Set a global service context with the e5 embedder.

    Inserts via VectorStoreIndex pull `embed_model` from the global service
    context. Standalone scripts don't get one set automatically (only
    chain_server.server does that on import). We set llm=None because ingest
    never calls an LLM.
    """
    embed_model = chains.get_embedding_model()
    sc = ServiceContext.from_defaults(embed_model=embed_model, llm=None)
    set_global_service_context(sc)


def _drop_collection_if_exists(name: str) -> bool:
    try:
        from pymilvus import connections, utility
    except ImportError:
        return False
    config = chains.get_config()
    # config.milvus is e.g. "http://localhost:19530"
    host_port = config.milvus.replace("http://", "").replace("https://", "")
    host, _, port = host_port.partition(":")
    connections.connect(host=host or "localhost", port=port or "19530")
    if name in utility.list_collections():
        utility.drop_collection(name)
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--jsonl", default=str(DEFAULT_JSONL),
                    help=f"JSONL source (default: {DEFAULT_JSONL})")
    ap.add_argument("--max-rows", type=int, default=1500,
                    help="Cap rows after filter (0 = unlimited)")
    ap.add_argument("--filter-name", action="append", default=None,
                    help=("Substring filter (repeatable, OR-joined). Empty "
                          "string disables filtering. Default = case-bundle "
                          "scope."))
    ap.add_argument("--batch-size", type=int, default=32,
                    help="Documents per insert batch")
    ap.add_argument("--drop-first", action="store_true",
                    help="Drop existing rc_nara_pages collection first")
    ap.add_argument("--dry-run", action="store_true",
                    help="Build documents and print counts; do not insert")
    args = ap.parse_args()

    src = Path(args.jsonl)
    if not src.exists():
        print(f"ERROR: {src} not found", file=sys.stderr)
        return 1

    if args.filter_name is None:
        filters = DEFAULT_FILTERS
    elif args.filter_name == [""]:
        filters = ()  # explicit no-filter
    else:
        filters = tuple(args.filter_name)

    if args.drop_first:
        dropped = _drop_collection_if_exists(COLLECTION_NAME)
        print(f"drop_first: {'dropped' if dropped else 'no existing collection'}")

    print(f"reading {src}")
    print(f"filters: {filters or '(none — all rows)'}")
    print(f"max-rows after filter: {args.max_rows or 'unlimited'}")

    matched: list[Document] = []
    bucket_counts: dict[str, int] = {}
    seen = 0
    with src.open("r", encoding="utf-8") as f:
        for line in f:
            seen += 1
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = row.get("document", "")
            bucket = _matches(text, filters)
            if bucket is None:
                continue
            doc = _row_to_document(row, bucket)
            if doc is None:
                continue
            matched.append(doc)
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
            if args.max_rows and len(matched) >= args.max_rows:
                break

    print(f"\nscanned {seen} rows; matched {len(matched)} after filter")
    for b, c in sorted(bucket_counts.items(), key=lambda x: -x[1]):
        print(f"  {b or 'all':<20} {c:>5}")

    if not matched:
        print("nothing to ingest — exiting")
        return 1

    if args.dry_run:
        print("\n[dry-run] not inserting")
        return 0

    print("\nloading embed model + setting service context...")
    _ensure_service_context()

    print(f"connecting to Milvus collection: {COLLECTION_NAME}")
    index = chains.get_vector_index(collection_name=COLLECTION_NAME)
    parser = SimpleNodeParser.from_defaults()

    inserted = 0
    started = time.perf_counter()
    for i in range(0, len(matched), args.batch_size):
        batch = matched[i : i + args.batch_size]
        nodes = parser.get_nodes_from_documents(batch)
        index.insert_nodes(nodes)
        inserted += len(nodes)
        elapsed = time.perf_counter() - started
        rate = inserted / elapsed if elapsed > 0 else 0
        print(f"  inserted {inserted:>5} chunks in {elapsed:>6.1f}s ({rate:.1f}/s)")

    print(f"\ndone — {inserted} chunks in collection {COLLECTION_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
