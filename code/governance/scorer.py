# SPDX-License-Identifier: Apache-2.0
# Modifications copyright (c) 2026 Booz Allen Hamilton — Women in AI Smithsonian Hackathon 2026 prototype.

"""Composer for the gpt-rct OECD KPI rubric.

Reads a lesson-generation event, calls each dimension scorer, assembles a
result dict with composite score + per-dimension scores + rationale +
needs_human_review flag. Pure function — no side effects, no I/O.

Usage:

    from code.governance import scorer
    result = scorer.score_event(event)
    # result == {
    #   "rubric_version": "gpt-rct-v1.0-2026-05-07",
    #   "scores": {auditability: 1.0, transparency: 0.8, ...},
    #   "composite": 0.94,
    #   "rationale": {auditability: ["..."], ...},
    #   "confidence": {...},
    #   "needs_human_review": False,
    #   "errors": []
    # }
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from code.governance import (
    CONFIDENCE,
    RANDOM_SAMPLE_PCT,
    RUBRIC_VERSION,
    WEIGHTS,
)
from code.governance.dimensions import DIMENSIONS

SENSITIVE_KEYWORDS = re.compile(
    r"\b(black|white|asian|hispanic|latino|jewish|muslim|christian|"
    r"gay|lesbian|trans|gender|race|ethnicity|religion)\b",
    re.IGNORECASE,
)


def _needs_human_review(event: dict, scores: dict[str, float]) -> bool:
    text = (event.get("essential_question") or "") + "\n" + \
           (event.get("lesson_markdown") or "")
    if SENSITIVE_KEYWORDS.search(text):
        return True
    if scores.get("fairness", 1.0) < 0.6:
        return True
    request_id = event.get("request_id") or ""
    seed = (str(request_id) + RUBRIC_VERSION).encode()
    if int(hashlib.sha256(seed).hexdigest(), 16) % 100 < RANDOM_SAMPLE_PCT:
        return True
    return False


def score_event(event: dict) -> dict:
    """Score a lesson-generation event against the 5-dimension OECD rubric.

    `event` is a dict with at least: essential_question, triad, lesson_markdown,
    model, generation_ms, request_id (and optionally ledger_event_id).
    """
    scores: dict[str, float] = {}
    rationale: dict[str, list[str]] = {}
    errors: list[dict] = []

    for name, module in DIMENSIONS.items():
        try:
            score_value, rat = module.score(event)
            scores[name] = round(float(score_value), 3)
            rationale[name] = rat
        except Exception as exc:  # pylint:disable=broad-exception-caught
            scores[name] = 0.0
            rationale[name] = [f"scorer_raised:{type(exc).__name__}"]
            errors.append({"dimension": name, "error": str(exc)})

    composite = sum(WEIGHTS[d] * scores[d] for d in scores)

    return {
        "rubric_version": RUBRIC_VERSION,
        "scorer": "deterministic-v1",
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "scores": scores,
        "composite": round(composite, 3),
        "weights": dict(WEIGHTS),
        "confidence": dict(CONFIDENCE),
        "rationale": rationale,
        "needs_human_review": _needs_human_review(event, scores),
        "errors": errors,
    }
