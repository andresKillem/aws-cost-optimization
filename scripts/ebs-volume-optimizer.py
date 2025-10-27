#!/usr/bin/env python3
"""
List EBS volumes that are unattached or overprovisioned (via Compute Optimizer when available).
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


def unattached_volumes(region: str) -> List[Dict[str, Any]]:
    vols = paginate(with_region(aws_base() + ["ec2", "describe-volumes", "--max-results", "500"], region), result_key="Volumes")
    return [
        {
            "VolumeId": v.get("VolumeId"),
            "Size": v.get("Size"),
            "VolumeType": v.get("VolumeType"),
            "Iops": v.get("Iops"),
            "Throughput": v.get("Throughput"),
        }
        for v in vols
        if not v.get("Attachments")
    ]


def co_recommendations(region: str) -> List[Dict[str, Any]]:
    items = paginate(
        with_region(aws_base() + ["compute-optimizer", "get-ebs-volume-recommendations", "--max-results", "100"], region),
        result_key="volumeRecommendations",
    )
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    region = ensure_region(args.region)
    data: Dict[str, Any] = {"region": region}
    data["unattached"] = unattached_volumes(region)
    data["computeOptimizer"] = co_recommendations(region) if co_enabled(region) else []
    write_stdout_json(data)


if __name__ == "__main__":
    main()
