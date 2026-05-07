"""File-level vs page-level NARA retrieval comparison harness — RCT-006.

Runs a fixed prompt suite against both Milvus collections:

  - `llamalection`     : the existing curated demo corpus (file-level NARA
                        chunks mixed with LOC + SI). NARA chunks are sliced
                        from `nara_pension_pdfs.jsonl` (one row per whole
                        pension file).
  - `rc_nara_pages`    : the page-level companion built by
                        `ingest_nara_pages.py`. One row per pension page.

For each prompt, records the top-K retrieval results from each collection
(text snippet + score + NAID + page hint) and writes a side-by-side
markdown report. The intended audience is the deck — this is the evidence
that the architectural choice (page-level for citation drill-down,
file-level for context) is principled.

Run inside the container with api-env python:

    docker exec project-hybrid-rag bash -c '
      $HOME/.conda/envs/api-env/bin/python \\
        /project/code/scripts/helpers/study_nara_comparison.py
    '

Output: `data/scratch/hackathon-smithsonian/nara-comparison-study.md`
(also gitignored — strategy-folder material, not engineering code).
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make /project/code importable
sys.path.insert(0, "/project/code")

from chain_server import chains  # noqa: E402
from llama_index import ServiceContext, set_global_service_context  # noqa: E402

DEFAULT_PROMPTS = [
    "What can the petitions and testimonies of Revolutionary-era women tell us about who bore the cost of the war?",
    "How did Revolutionary War service shape a soldier's life decades after the war ended?",
    "What kinds of evidence did widows submit to prove their husbands' service?",
    "What do pension files tell us about Henry Knox's post-war financial circumstances?",
    "Describe a specific example of testimony about Revolutionary War service from a soldier or family member.",
    "What language did pension applicants use to describe their hardship?",
    "How did Revolutionary War soldiers' families demonstrate marriages or family relationships in pension applications?",
]

DEFAULT_OUT = Path(
    "/project/data/scratch/hackathon-smithsonian/nara-comparison-study.md"
)


def _ensure_service_context() -> None:
    embed_model = chains.get_embedding_model()
    sc = ServiceContext.from_defaults(embed_model=embed_model, llm=None)
    set_global_service_context(sc)


def _retrieve(query: str, collection_name: str | None, top_k: int) -> tuple[list[dict], float]:
    started = time.perf_counter()
    index = chains.get_vector_index(collection_name=collection_name)
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

    results: list[dict] = []
    for n in nodes:
        meta = dict(getattr(n.node, "metadata", None) or {})
        text = n.node.get_content() or ""
        # Prefer NARA-specific id fields; fall back to whatever's there
        ident = (meta.get("naid") or meta.get("page") or meta.get("doc_id") or "")
        results.append({
            "score": float(n.score) if getattr(n, "score", None) is not None else None,
            "corpus": meta.get("corpus", "?"),
            "granularity": meta.get("granularity", "file"),  # file-level by default
            "demo_bucket": meta.get("demo_bucket", ""),
            "naid": meta.get("naid", ""),
            "page_hint": meta.get("page", ""),
            "source_title": meta.get("source_title", ""),
            "source_url": meta.get("source_url", ""),
            "ident": str(ident),
            "snippet": text[:360].replace("\n", " ") + ("…" if len(text) > 360 else ""),
        })
    return results, elapsed_ms


def _filter_nara(results: list[dict]) -> list[dict]:
    """When querying llamalection, narrow to NARA chunks for fair comparison."""
    return [r for r in results if r.get("corpus") == "nara"]


def _format_report(prompt_results: list[dict], top_k: int) -> str:
    lines: list[str] = []
    lines.append("# NARA file-level vs page-level — retrieval comparison study")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}Z · "
                 f"top_k={top_k} per collection · embedder=intfloat/e5-large-v2_")
    lines.append("")
    lines.append("**Read this file alongside** `system-design.md` §6 (Evidence Triad) and "
                 "`adr.md` ADR-008 (per-corpus collection split). The point of the study "
                 "is to show that the two granularities serve different stages of the "
                 "lesson workflow — *not* to declare a winner.")
    lines.append("")

    for i, item in enumerate(prompt_results, start=1):
        prompt = item["prompt"]
        lines.append(f"## Prompt {i}")
        lines.append("")
        lines.append(f"> {prompt}")
        lines.append("")

        for label, results, latency in (
            ("File-level (llamalection · NARA-filtered)", item["file_level"], item["file_latency_ms"]),
            ("Page-level (rc_nara_pages)",                item["page_level"], item["page_latency_ms"]),
        ):
            lines.append(f"### {label} — retrieval {latency:.1f} ms")
            lines.append("")
            if not results:
                lines.append("_No results._")
                lines.append("")
                continue
            for j, r in enumerate(results, start=1):
                score = f"{r['score']:.3f}" if r.get("score") is not None else "n/a"
                naid = r.get("naid") or "(no NAID)"
                bucket = r.get("demo_bucket") or "—"
                page_hint = f" · page {r['page_hint']}" if r.get("page_hint") else ""
                lines.append(f"**{j}.** score `{score}` · naid `{naid}`{page_hint} · bucket `{bucket}`")
                if r.get("source_title"):
                    lines.append(f"  _{r['source_title']}_")
                lines.append(f"  {r['snippet']}")
                lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def _format_summary(prompt_results: list[dict]) -> str:
    """One-paragraph headline for the deck."""
    n = len(prompt_results)
    file_avg_score = _avg_top_score([item["file_level"] for item in prompt_results])
    page_avg_score = _avg_top_score([item["page_level"] for item in prompt_results])
    file_avg_lat = _avg([item["file_latency_ms"] for item in prompt_results])
    page_avg_lat = _avg([item["page_latency_ms"] for item in prompt_results])
    naid_overlap = _naid_overlap(prompt_results)
    return (
        f"\n## Summary\n\n"
        f"Across {n} prompts, mean top-1 similarity was "
        f"**{file_avg_score:.3f}** (file-level / llamalection-filtered) vs "
        f"**{page_avg_score:.3f}** (page-level / rc_nara_pages). "
        f"Mean retrieval latency was {file_avg_lat:.1f} ms vs {page_avg_lat:.1f} ms. "
        f"NAID-level overlap between top-K sets was **{naid_overlap:.0%}** — "
        f"interpret as: if both collections surface the *same pension files* but "
        f"different *granularities*, the page-level layer is the citation "
        f"drill-down for the file-level context, not a competitor.\n"
    )


def _avg_top_score(result_lists: list[list[dict]]) -> float:
    scores = [r[0]["score"] for r in result_lists
              if r and r[0].get("score") is not None]
    return sum(scores) / len(scores) if scores else 0.0


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _naid_overlap(prompt_results: list[dict]) -> float:
    overlaps: list[float] = []
    for item in prompt_results:
        f_naids = {r["naid"] for r in item["file_level"] if r["naid"]}
        p_naids = {r["naid"] for r in item["page_level"] if r["naid"]}
        if not f_naids or not p_naids:
            continue
        overlaps.append(len(f_naids & p_naids) / len(f_naids | p_naids))
    return sum(overlaps) / len(overlaps) if overlaps else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--top-k", type=int, default=5, help="Top-K per collection")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output markdown path")
    ap.add_argument("--prompt", action="append",
                    help="Override prompt list (repeatable). Default = built-in suite.")
    ap.add_argument("--no-filter-llamalection", action="store_true",
                    help="Don't NARA-filter the llamalection results (raw triad mix)")
    args = ap.parse_args()

    prompts = args.prompt or DEFAULT_PROMPTS
    print(f"running {len(prompts)} prompts × 2 collections × top-{args.top_k}")

    _ensure_service_context()

    rows: list[dict[str, Any]] = []
    for p in prompts:
        print(f"  q: {p[:80]}{'…' if len(p) > 80 else ''}")
        file_raw, file_ms = _retrieve(p, collection_name=None, top_k=args.top_k)
        if not args.no_filter_llamalection:
            file_raw = _filter_nara(file_raw)[:args.top_k]
        try:
            page_raw, page_ms = _retrieve(p, collection_name="rc_nara_pages",
                                          top_k=args.top_k)
        except Exception as exc:
            print(f"    page-level retrieve failed: {exc}")
            page_raw, page_ms = [], 0.0
        rows.append({
            "prompt": p,
            "file_level": file_raw,
            "file_latency_ms": file_ms,
            "page_level": page_raw,
            "page_latency_ms": page_ms,
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    body = _format_report(rows, args.top_k) + _format_summary(rows)
    out.write_text(body, encoding="utf-8")
    print(f"\nwrote {out} ({len(body)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
