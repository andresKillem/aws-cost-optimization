#!/usr/bin/env python3
"""
List CloudWatch Log Groups without explicit retention and suggest retention policies.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import aws_base, ensure_region, paginate, with_region, write_stdout_json, shell_json


def collect(region: str) -> Dict[str, Any]:
    # Use a large max-items to reduce pagination complexity; CLI v2 supports generic paginator
    groups = shell_json(with_region(aws_base() + ["logs", "describe-log-groups", "--max-items", "10000"], region)).get("logGroups", [])
    missing = [g for g in groups if not g.get("retentionInDays")]
    return {
        "region": region,
        "totalLogGroups": len(groups),
        "withoutRetention": len(missing),
        "candidates": [{"logGroupName": g.get("logGroupName"), "storedBytes": g.get("storedBytes", 0)} for g in missing],
        "recommendation": {
            "defaultRetentionDays": 30,
            "notes": "Aplicar al menos 30-90 días según criticidad; exportar a S3 con ciclo de vida para histórico.",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    region = ensure_region(args.region)
    data = collect(region)
    write_stdout_json(data)


if __name__ == "__main__":
    main()
