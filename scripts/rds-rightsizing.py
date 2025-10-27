#!/usr/bin/env python3
"""
Pull RDS rightsizing recommendations from Cost Explorer. If none, lists RDS instances for manual review.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import aws_base, ensure_region, paginate, shell_json, with_region, write_stdout_json


def ce_rds_rightsizing(region: str) -> Dict[str, Any]:
    try:
        data = shell_json(
            with_region(
                aws_base() + [
                    "ce",
                    "get-rightsizing-recommendations",
                    "--service",
                    "AmazonRDS",
                    "--filter",
                    "{}",
                ],
                region,
            )
        )
        return {"source": "ce", "recommendations": data.get("rightsizingRecommendations", [])}
    except Exception as e:
        return {"source": "ce", "error": str(e), "recommendations": []}


def rds_inventory(region: str) -> List[Dict[str, Any]]:
    dbs = paginate(with_region(aws_base() + ["rds", "describe-db-instances"], region), result_key="DBInstances")
    return [
        {
            "DBInstanceIdentifier": d.get("DBInstanceIdentifier"),
            "DBInstanceClass": d.get("DBInstanceClass"),
            "Engine": d.get("Engine"),
            "AllocatedStorage": d.get("AllocatedStorage"),
            "MultiAZ": d.get("MultiAZ"),
        }
        for d in dbs
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    region = ensure_region(args.region)
    ce = ce_rds_rightsizing(region)
    inv = rds_inventory(region)
    write_stdout_json({"region": region, "rightsizing": ce, "inventory": inv})


if __name__ == "__main__":
    main()
