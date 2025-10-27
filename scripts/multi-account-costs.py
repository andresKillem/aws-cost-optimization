#!/usr/bin/env python3
"""
Cost Explorer aggregation by LinkedAccount and Service for the last N days.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict

from common import aws_base, date_range, ensure_region, shell_json, with_region, write_stdout_json


def costs(region: str, days: int) -> Dict[str, Any]:
    start, end = date_range(days)
    data = shell_json(
        with_region(
            aws_base()
            + [
                "ce",
                "get-cost-and-usage",
                "--time-period",
                f"Start={start},End={end}",
                "--granularity",
                "MONTHLY",
                "--metrics",
                "UnblendedCost",
                "--group-by",
                '{"Type":"DIMENSION","Key":"LINKED_ACCOUNT"}',
                "--group-by",
                '{"Type":"DIMENSION","Key":"SERVICE"}',
            ],
            region,
        )
    )
    return data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()
    write_stdout_json(costs(ensure_region(args.region), args.days))


if __name__ == "__main__":
    main()
