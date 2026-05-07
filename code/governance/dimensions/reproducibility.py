# SPDX-License-Identifier: Apache-2.0
# Modifications copyright (c) 2026 Booz Allen Hamilton — Women in AI Smithsonian Hackathon 2026 prototype.

"""Reproducibility dimension scorer.

OECD principles: Accountability + Robustness (cross-cut).

Could a third party re-run this exact lesson generation and get the same
result? Looks for: model id with version, embedding model recorded,
sampling parameters captured, retrieved chunk IDs logged so the same
query can be replayed.
"""
from __future__ import annotations

import re

VERSIONED_MODEL_RE = re.compile(
    r"\b("
    r"mistralai/[\w\-]+-v\d+(\.\d+)?|"
    r"meta/llama[\w\-\.]*-instruct|"
    r"meta/llama-\d+(\.\d+)*[bB]-?[\w\-]*|"
    r"microsoft/phi[\w\-\.]+|"
    r"google/gemma[\w\-]+|"
    r"nvidia/[\w\-]+-\d+[bB]"
    r")\b",
    re.IGNORECASE,
)


def score(event: dict) -> tuple[float, list[str]]:
    rationale: list[str] = []
    checks: list[bool] = []

    model = event.get("model") or {}
    model_id = str(model.get("model_id") or model.get("id") or "")

    # Model id must include a version (mistral/mixtral-8x7b-instruct-v0.1, not just "mistral")
    versioned = bool(VERSIONED_MODEL_RE.search(model_id))
    checks.append(versioned)
    rationale.append(
        f"model_versioned:pass:{model_id}" if versioned
        else f"model_versioned:fail:{model_id or 'missing'}"
    )

    # Embedding model recorded
    embedding_model = str(model.get("embedding_model") or "")
    has_embedder = bool(embedding_model)
    checks.append(has_embedder)
    rationale.append(
        f"embedding_model_recorded:pass:{embedding_model}" if has_embedder
        else "embedding_model_recorded:fail"
    )

    # Sampling params recorded — temperature + top_p at minimum
    has_temp = "temperature" in model or "temp" in model
    has_top_p = "top_p" in model
    sampling_recorded = has_temp and has_top_p
    checks.append(sampling_recorded)
    rationale.append(
        "sampling_params_recorded:pass" if sampling_recorded
        else f"sampling_params_recorded:fail:temp_{has_temp}_top_p_{has_top_p}"
    )

    # Seed presence — allow None but record either way for the audit
    seed_recorded = "seed" in model
    checks.append(seed_recorded)
    rationale.append(
        f"seed_field_present:pass:value_{model.get('seed')}"
        if seed_recorded else "seed_field_present:fail"
    )

    # Each retrieved chunk has a stable identifier (NAID / EDAN id / LCCN)
    triad = event.get("triad") or {}
    ids_present: list[bool] = []
    for chunk in triad.values():
        meta = chunk.get("metadata") or {}
        ids_present.append(bool(
            meta.get("naid") or meta.get("edan_id") or meta.get("lccn")
            or meta.get("doc_id")
        ))
    all_ids = bool(ids_present) and all(ids_present)
    checks.append(all_ids)
    rationale.append(
        "retrieved_chunks_identified:pass" if all_ids
        else f"retrieved_chunks_identified:fail:missing_in_{ids_present.count(False)}_of_{len(ids_present)}"
    )

    return sum(checks) / len(checks), rationale
