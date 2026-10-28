"""Compare TrustTrace with a naive keyword filter on the bundled scenarios.

Run from the backend directory: ``python benchmark.py``. The baseline is a
deliberately simple denylist over the serialized tool arguments, the kind many
prototypes start with. The scenarios are the project's own, so treat the result
as a regression check rather than a general security measurement.
"""
from __future__ import annotations

import json
import re

from policy.engine import PolicyEngine
from scenarios import SCENARIOS, make_tool_call

KEYWORDS = re.compile(
    r"(?i)ignore (all )?(previous|prior) instructions|drop table|delete from|"
    r"password|api[_ -]?key"
)


def keyword_filter(arguments: dict) -> str:
    return "BLOCK" if KEYWORDS.search(json.dumps(arguments)) else "ALLOW"


def main() -> None:
    engine = PolicyEngine()
    rows = []
    for scenario_id, scenario in SCENARIOS.items():
        call = make_tool_call(scenario_id)
        rows.append(
            (
                scenario["title"],
                scenario["expected_decision"],
                keyword_filter(call.arguments),
                engine.evaluate(call).decision,
            )
        )

    print(f"{'Scenario':36} {'Expected':8} {'Keyword':8} TrustTrace")
    for title, expected, keyword, trusttrace in rows:
        print(f"{title:36} {expected:8} {keyword:8} {trusttrace}")

    attacks = [r for r in rows if r[1] != "ALLOW"]
    benign = [r for r in rows if r[1] == "ALLOW"]
    for name, index in (("Keyword filter", 2), ("TrustTrace", 3)):
        caught = sum(r[index] != "ALLOW" for r in attacks)
        exact = sum(r[index] == r[1] for r in rows)
        false_pos = sum(r[index] != "ALLOW" for r in benign)
        print(
            f"{name}: attacks caught {caught}/{len(attacks)}, "
            f"exact decisions {exact}/{len(rows)}, "
            f"benign false positives {false_pos}/{len(benign)}"
        )


if __name__ == "__main__":
    main()
