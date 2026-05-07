# SPDX-License-Identifier: Apache-2.0
# Modifications copyright (c) 2026 Booz Allen Hamilton — Women in AI Smithsonian Hackathon 2026 prototype.

"""Per-dimension scorers for the gpt-rct OECD rubric.

Each module exposes ``score(event: dict) -> tuple[float, list[str]]``.
The score is in [0, 1]. The rationale list uses the apexlon convention:
``<rule_id>:<status>[:<detail>]`` so aggregation queries can group by
rule ID without parsing prefixes.
"""
from . import auditability, fairness, reproducibility, robustness, transparency

DIMENSIONS = {
    "auditability": auditability,
    "transparency": transparency,
    "robustness": robustness,
    "fairness": fairness,
    "reproducibility": reproducibility,
}
