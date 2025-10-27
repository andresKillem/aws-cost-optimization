#!/usr/bin/env python3
"""
Detect EC2 instances that appear idle and are candidates for stop/rightsizing.
- Uses Compute Optimizer (if enabled) else falls back to CloudWatch CPU utilization.
- Outputs JSON with candidates and rationale.
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


def collect_with_compute_optimizer(region: str) -> Dict[str, Any]:
    items = paginate(
        with_region(
            aws_base() + ["compute-optimizer", "get-ec2-instance-recommendations", "--max-results", "100"],
            region,
        ),
        result_key="instanceRecommendations",
    )
    candidates: List[Dict[str, Any]] = []
    for rec in items:
        finding = rec.get("finding")  # e.g., Overprovisioned, Underprovisioned, Optimized
        if finding in {"Overprovisioned", "NotOptimized"}:
            inst = {
                "instanceArn": rec.get("instanceArn"),
                "instanceName": rec.get("currentInstanceType"),
                "finding": finding,
                "utilizationMetrics": rec.get("utilizationMetrics", []),
                "recommendationOptions": rec.get("recommendationOptions", [])[:3],
            }
            candidates.append(inst)
    return {"source": "compute-optimizer", "region": region, "count": len(candidates), "candidates": candidates}


def collect_with_cw_cpu(region: str) -> Dict[str, Any]:
    # Lightweight heuristic using CE rightsizing as primary source
    try:
        rr = shell_json(
            with_region(
                aws_base()
                + [
                    "ce",
                    "get-rightsizing-recommendations",
                    "--service",
                    "AmazonEC2",
                    "--filter",
                    "{}",
                ],
                region,
            )
        )
        recs = rr.get("rightsizingRecommendations", [])
        return {"source": "ce-rightsizing", "region": region, "count": len(recs), "candidates": recs[:200]}
    except Exception as e:
        return {"source": "none", "region": region, "error": str(e)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    region = ensure_region(args.region)
    if co_enabled(region):
        data = collect_with_compute_optimizer(region)
    else:
        data = collect_with_cw_cpu(region)
    write_stdout_json(data)


if __name__ == "__main__":
    main()
