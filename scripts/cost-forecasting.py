#!/usr/bin/env python3
"""
Generate a 30/60/90 day cost forecast using Cost Explorer.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from typing import Any, Dict

from common import aws_base, ensure_region, shell_json, with_region, write_stdout_json


def forecast(region: str, days: int) -> Dict[str, Any]:
    start = date.today()
    end = start + timedelta(days=days)
    try:
        data = shell_json(
            with_region(
                aws_base()
                + [
                    "ce",
                    "get-cost-forecast",
                    "--metric",
                    "UNBLENDED_COST",
                    "--time-period",
                    f"Start={start.isoformat()},End={end.isoformat()}",
                    "--granularity",
                    "DAILY",
                ],
                region,
            )
        )
        return data
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()
    write_stdout_json(forecast(ensure_region(args.region), args.days))


if __name__ == "__main__":
    main()
