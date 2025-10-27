#!/usr/bin/env python3
"""
Summarize Lambda functions and highlight high memory or low utilization functions (using Compute Optimizer when available).
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import aws_base, ensure_region, paginate, shell_json, with_region, write_stdout_json


def co_enabled(region: str) -> bool:
    try:
        res = shell_json(with_region(aws_base() + ["compute-optimizer", "get-enrollment-status"], region))
        return res.get("status") in {"Active", "Pending"}
    except Exception:
        return False


def lambda_inventory(region: str) -> List[Dict[str, Any]]:
    fns = paginate(with_region(aws_base() + ["lambda", "list-functions"], region), result_key="Functions")
    return [
        {
            "FunctionName": f.get("FunctionName"),
            "MemorySize": f.get("MemorySize"),
            "Timeout": f.get("Timeout"),
            "Runtime": f.get("Runtime"),
            "LastModified": f.get("LastModified"),
        }
        for f in fns
    ]


def co_lambda_recs(region: str) -> List[Dict[str, Any]]:
    try:
        recs = paginate(
            with_region(aws_base() + ["compute-optimizer", "get-lambda-function-recommendations", "--max-results", "100"], region),
            result_key="lambdaFunctionRecommendations",
        )
    except Exception:
        recs = []
    return recs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    region = ensure_region(args.region)
    data: Dict[str, Any] = {"region": region, "inventory": lambda_inventory(region)}
    data["computeOptimizer"] = co_lambda_recs(region) if co_enabled(region) else []
    write_stdout_json(data)


if __name__ == "__main__":
    main()
