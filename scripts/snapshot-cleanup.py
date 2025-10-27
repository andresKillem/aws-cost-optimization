#!/usr/bin/env python3
"""
List EBS snapshots older than a threshold (default 90 days) that are candidates for archival/cleanup.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from common import aws_base, ensure_region, paginate, with_region, write_stdout_json


def collect(region: str, days: int) -> Dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    snaps = paginate(
        with_region(aws_base() + ["ec2", "describe-snapshots", "--owner-ids", "self", "--max-results", "1000"], region),
        result_key="Snapshots",
    )
    old = [
        {
            "SnapshotId": s.get("SnapshotId"),
            "StartTime": s.get("StartTime"),
            "VolumeId": s.get("VolumeId"),
            "VolumeSize": s.get("VolumeSize"),
            "StorageTier": s.get("StorageTier"),
        }
        for s in snaps
        if s.get("StartTime") and datetime.fromisoformat(str(s["StartTime"]).replace("Z", "+00:00")) < cutoff
    ]
    return {"region": region, "thresholdDays": days, "totalSnapshots": len(snaps), "olderThanThreshold": len(old), "candidates": old[:500]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()
    data = collect(ensure_region(args.region), args.days)
    write_stdout_json(data)


if __name__ == "__main__":
    main()
