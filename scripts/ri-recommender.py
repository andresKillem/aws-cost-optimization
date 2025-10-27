#!/usr/bin/env python3
"""
Fetch RI purchase recommendations via Cost Explorer for EC2/RDS where applicable.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict

from common import aws_base, ensure_region, shell_json, with_region, write_stdout_json


def ce_ri_recommendations(region: str, service: str = "Amazon Elastic Compute Cloud - Compute") -> Dict[str, Any]:
    # Defaults: 1-year, No Upfront, account-scope linked (if org)
    try:
        data = shell_json(
            with_region(
                aws_base()
                + [
                    "ce",
                    "get-reservation-purchase-recommendation",
                    "--service",
                    service,
                    "--lookback-period-in-days",
                    "THIRTY_DAYS",
                    "--term-in-years",
                    "ONE_YEAR",
                    "--payment-option",
                    "NO_UPFRONT",
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
    ap.add_argument("--service", default="AmazonEC2")
    args = ap.parse_args()
    data = ce_ri_recommendations(ensure_region(args.region), args.service)
    write_stdout_json(data)


if __name__ == "__main__":
    main()
