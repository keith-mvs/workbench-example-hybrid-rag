# SPDX-License-Identifier: Apache-2.0
# Modifications copyright (c) 2026 Booz Allen Hamilton — Women in AI Smithsonian Hackathon 2026 prototype.

"""Robustness dimension scorer.

OECD principle: Robustness, Security, Safety.

Checks that retrieval surfaced something usable, that the LLM didn't
truncate, and that generation latency is within sane bounds.
"""
from __future__ import annotations

import re

from code.governance import ROBUSTNESS_MIN_TOP1_SIMILARITY


def score(event: dict) -> tuple[float, list[str]]:
    rationale: list[str] = []
    checks: list[bool] = []

    triad = event.get("triad") or {}

    # Each corpus has at least one chunk
    triad_nonempty = bool(triad) and all(c for c in triad.values())
    checks.append(triad_nonempty)
    rationale.append(
        "triad_nonempty:pass" if triad_nonempty
        else f"triad_nonempty:fail:got_{len(triad)}_corpora"
    )

    # Top-1 score per corpus crosses the floor
    above_threshold: list[bool] = []
    for corpus_tag, chunk in triad.items():
        score_value = chunk.get("score")
        if score_value is None:
            above_threshold.append(False)
        else:
            above_threshold.append(
                float(score_value) >= ROBUSTNESS_MIN_TOP1_SIMILARITY
            )
    all_above = bool(above_threshold) and all(above_threshold)
    checks.append(all_above)
    rationale.append(
        f"retrieval_above_floor:pass:floor_{ROBUSTNESS_MIN_TOP1_SIMILARITY}"
        if all_above
        else f"retrieval_above_floor:fail:floor_{ROBUSTNESS_MIN_TOP1_SIMILARITY}"
    )

    # Lesson content present (not None, not empty, not error placeholder)
    lesson = (event.get("lesson_markdown") or "").strip()
    has_content = len(lesson) >= 200 and "ERR" not in lesson[:40].upper()
    checks.append(has_content)
    rationale.append(
        "lesson_completed:pass" if has_content
        else f"lesson_completed:fail:len_{len(lesson)}"
    )

    # Activity-duration sum check — if the lesson lists durations like "5 min",
    # the sum should approximately match duration_minutes. Skip if no
    # durations are parseable.
    requested = int(event.get("duration_minutes") or 0)
    durations = [int(m) for m in re.findall(r"\((\d{1,3})\s*min", lesson)]
    if durations and requested > 0:
        total = sum(durations)
        within_tolerance = abs(total - requested) <= max(5, requested * 0.15)
        checks.append(within_tolerance)
        rationale.append(
            f"durations_sum_matches:pass:total_{total}_target_{requested}"
            if within_tolerance
            else f"durations_sum_matches:fail:total_{total}_target_{requested}"
        )
    else:
        # No durations parseable — neither pass nor fail; don't add a check
        rationale.append("durations_sum_matches:skip:no_durations_parsed")

    # Generation latency sane (< 5 min — anything more than that is broken)
    gen_ms = float(event.get("generation_ms") or 0)
    latency_sane = 0 < gen_ms < 5 * 60 * 1000
    checks.append(latency_sane)
    rationale.append(
        f"generation_latency_sane:pass:ms_{int(gen_ms)}" if latency_sane
        else f"generation_latency_sane:fail:ms_{int(gen_ms)}"
    )

    return sum(checks) / len(checks), rationale
