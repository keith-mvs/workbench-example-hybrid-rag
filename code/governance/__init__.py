# SPDX-License-Identifier: Apache-2.0
# Modifications copyright (c) 2026 Booz Allen Hamilton — Women in AI Smithsonian Hackathon 2026 prototype.

"""gpt-rct governance module.

Pattern-port (per ADR-011) of apexlon's 5-dimension OECD KPI rubric, adapted
to gpt-rct's lesson-generation context. Apexlon scores compiled-prompt
artifacts; gpt-rct scores the whole lesson-generation **event**:

    LessonEvent {
        essential_question: str,
        grade_band: str,
        duration_minutes: int,
        triad: dict[corpus_tag, dict],     # one chunk per corpus
        lesson_markdown: str,
        model: dict,                        # id, mode, params
        generation_ms: float,
        retrieval_top_k: int,
        request_id: str,
        ledger_event_id: str | None,        # filled by ledger after log()
    }

Each dimension scorer takes the event and returns (score: float, rationale:
list[str]). The composer (`scorer.score_event`) runs all five and emits a
result dict with composite score, per-dimension scores, rationale, and
`needs_human_review` flag.

Public surface:

    from code.governance import scorer, ledger
    from code.governance import RUBRIC_VERSION, WEIGHTS, CONFIDENCE
    result = scorer.score_event(event)
"""
from __future__ import annotations

RUBRIC_VERSION = "gpt-rct-v1.0-2026-05-07"

# Uniform weights for v1; tunable from production data after >=30 days of
# real lesson generations.
WEIGHTS: dict[str, float] = {
    "auditability": 0.20,
    "transparency": 0.20,
    "robustness": 0.20,
    "fairness": 0.20,
    "reproducibility": 0.20,
}

# Empirical confidence per dimension. v1 placeholders mirror apexlon's
# calibration-time bands; recompute against a gpt-rct fixture corpus once
# we have one (RCT-018).
CONFIDENCE: dict[str, float] = {
    "auditability": 0.90,    # mechanical metadata checks
    "transparency": 0.85,    # structural output checks
    "robustness": 0.85,      # threshold-based retrieval + completion checks
    "fairness": 0.55,        # structural sieve only — see Limitations
    "reproducibility": 0.95, # mechanical model/seed/version checks
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "WEIGHTS must sum to 1.0"
assert set(WEIGHTS.keys()) == set(CONFIDENCE.keys()), \
    "WEIGHTS and CONFIDENCE must cover same dimensions"


# Configurable thresholds — surfaced here so the deck can quote them.
ROBUSTNESS_MIN_TOP1_SIMILARITY: float = 0.55
TRANSPARENCY_MIN_LESSON_WORDS: int = 250
TRANSPARENCY_MAX_LESSON_WORDS: int = 1800
TRANSPARENCY_MIN_CITATIONS: int = 2

# Random-sample percentage for needs_human_review on otherwise-clean events.
# Same 5% apexlon uses; deliberate inefficiency that catches blind-spot bias.
RANDOM_SAMPLE_PCT: int = 5
