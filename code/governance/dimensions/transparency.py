# SPDX-License-Identifier: Apache-2.0
# Modifications copyright (c) 2026 Booz Allen Hamilton — Women in AI Smithsonian Hackathon 2026 prototype.

"""Transparency dimension scorer.

OECD principle: Transparency & Explainability.

Inspects the lesson markdown for: explicit citations, lesson-plan
structure markers, length within sane bounds, and model-pinning visible
to the reader.
"""
from __future__ import annotations

import re

from code.governance import (
    TRANSPARENCY_MAX_LESSON_WORDS,
    TRANSPARENCY_MIN_CITATIONS,
    TRANSPARENCY_MIN_LESSON_WORDS,
)

URL_RE = re.compile(r"https?://[^\s\)]+", re.IGNORECASE)
HEADING_RE = re.compile(r"^#{1,6}\s+\w", re.MULTILINE)
ACTIVITY_MARKER_RE = re.compile(
    r"\b(activity|step|duration|min(?:ute)?s?\b|exit ticket|warm[- ]up|"
    r"observe|read|discuss|analyze|reflect)\b",
    re.IGNORECASE,
)


def score(event: dict) -> tuple[float, list[str]]:
    rationale: list[str] = []
    checks: list[bool] = []

    lesson = (event.get("lesson_markdown") or "").strip()

    # Citations: at least N URLs in the body
    urls = URL_RE.findall(lesson)
    enough_citations = len(urls) >= TRANSPARENCY_MIN_CITATIONS
    checks.append(enough_citations)
    rationale.append(
        f"citations_present:pass:count_{len(urls)}" if enough_citations
        else f"citations_present:fail:count_{len(urls)}"
    )

    # Length within target band — too short = no real lesson, too long = waffle
    word_count = len(lesson.split())
    in_band = (TRANSPARENCY_MIN_LESSON_WORDS <= word_count
               <= TRANSPARENCY_MAX_LESSON_WORDS)
    checks.append(in_band)
    rationale.append(
        f"lesson_length_in_band:pass:words_{word_count}" if in_band
        else f"lesson_length_in_band:fail:words_{word_count}"
    )

    # Structure markers — markdown headings + activity language
    has_headings = bool(HEADING_RE.search(lesson))
    checks.append(has_headings)
    rationale.append(
        "markdown_structure_present:pass" if has_headings
        else "markdown_structure_present:fail"
    )

    activity_hits = len(ACTIVITY_MARKER_RE.findall(lesson))
    has_activity_lang = activity_hits >= 3
    checks.append(has_activity_lang)
    rationale.append(
        f"activity_structure_present:pass:hits_{activity_hits}"
        if has_activity_lang
        else f"activity_structure_present:fail:hits_{activity_hits}"
    )

    # Model id should be specific (versioned), not just "mistral" / "llama"
    model = event.get("model") or {}
    model_id = str(model.get("model_id") or model.get("id") or "").lower()
    is_pinned = bool(re.search(
        r"-v\d|/\w+-\d|instruct-\w|\d+b-instruct", model_id))
    checks.append(is_pinned)
    rationale.append(
        f"model_pinned_specific:pass:{model_id}" if is_pinned
        else f"model_pinned_specific:fail:{model_id or 'missing'}"
    )

    return sum(checks) / len(checks), rationale
