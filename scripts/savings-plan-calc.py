#!/usr/bin/env python3
"""
Fetch AWS Savings Plans purchase recommendations (Compute/EC2). Outputs JSON.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict

from common import aws_base, ensure_region, shell_json, with_region, write_stdout_json


def sp_recommendations(region: str, sp_type: str = "COMPUTE_SP") -> Dict[str, Any]:
    try:
        data = shell_json(
            with_region(
                aws_base()
                + [
                    "ce",
                    "get-savings-plans-purchase-recommendation",
                    "--savings-plans-type",
                    sp_type,
                    "--term-in-years",
                    "ONE_YEAR",
                    "--payment-option",
                    "NO_UPFRONT",
                    "--lookback-period-in-days",
                    "THIRTY_DAYS",
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
    ap.add_argument("--type", default="COMPUTE_SP", choices=["COMPUTE_SP", "EC2_INSTANCE_SP"])
    args = ap.parse_args()
    write_stdout_json(sp_recommendations(ensure_region(args.region), args.type))


if __name__ == "__main__":
    main()
