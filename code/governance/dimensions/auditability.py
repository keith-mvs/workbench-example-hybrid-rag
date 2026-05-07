# SPDX-License-Identifier: Apache-2.0
# Modifications copyright (c) 2026 Booz Allen Hamilton — Women in AI Smithsonian Hackathon 2026 prototype.

"""Auditability dimension scorer.

OECD principle: Accountability.

Mechanical checks: presence and integrity of audit-trail elements on a
gpt-rct lesson-generation event. Highest-confidence dimension in the
rubric (mechanical facts only).
"""
from __future__ import annotations


def score(event: dict) -> tuple[float, list[str]]:
    rationale: list[str] = []
    checks: list[bool] = []

    request_id = event.get("request_id", "")
    has_request_id = bool(request_id) and len(str(request_id)) >= 8
    checks.append(has_request_id)
    rationale.append(
        "request_id_present:pass" if has_request_id
        else "request_id_present:fail"
    )

    triad = event.get("triad") or {}
    expected_corpora = {"loc", "nara", "si"}
    triad_corpora = set(triad.keys())
    triad_complete = expected_corpora.issubset(triad_corpora)
    checks.append(triad_complete)
    if triad_complete:
        rationale.append("evidence_triad_complete:pass")
    else:
        missing = sorted(expected_corpora - triad_corpora)
        rationale.append(
            f"evidence_triad_complete:fail:missing_{'-'.join(missing)}"
        )

    # Each retrieved chunk should carry a source_url for citation traceability.
    urls_present = bool(triad) and all(
        bool((c.get("metadata") or {}).get("source_url"))
        for c in triad.values()
    )
    checks.append(urls_present)
    rationale.append(
        "source_urls_present:pass" if urls_present
        else "source_urls_present:fail"
    )

    model = event.get("model") or {}
    model_recorded = bool(model.get("model_id") or model.get("id"))
    checks.append(model_recorded)
    rationale.append(
        "model_id_recorded:pass" if model_recorded
        else "model_id_recorded:fail"
    )

    # Ledger event_id is filled in *after* the ledger writes. If we're being
    # called pre-ledger (e.g. dry-run scoring), this is allowed to be None
    # without failing — but on a real run, ledger.log() backfills it before
    # the response goes back.
    ledger_id = event.get("ledger_event_id")
    ledger_present = ledger_id is not None and len(str(ledger_id)) > 0
    checks.append(ledger_present)
    rationale.append(
        "ledger_event_logged:pass" if ledger_present
        else "ledger_event_logged:fail:will_backfill"
    )

    return sum(checks) / len(checks), rationale
