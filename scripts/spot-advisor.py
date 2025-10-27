#!/usr/bin/env python3
"""
Suggest spot diversification by listing recent spot price history for a given instance type.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from common import aws_base, ensure_region, shell_json, with_region, write_stdout_json


def spot_prices(region: str, instance_type: str, days: int = 3) -> Dict[str, Any]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    data = shell_json(
        with_region(
            aws_base()
            + [
                "ec2",
                "describe-spot-price-history",
                "--instance-types",
                instance_type,
                "--product-descriptions",
                "Linux/UNIX",
                "--start-time",
                start.isoformat(),
                "--end-time",
                end.isoformat(),
            ],
            region,
        )
    )
    return data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    ap.add_argument("--type", default="m6g.large")
    args = ap.parse_args()
    write_stdout_json(spot_prices(ensure_region(args.region), args.type))


if __name__ == "__main__":
    main()
