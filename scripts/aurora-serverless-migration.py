#!/usr/bin/env python3
"""
Identify Aurora clusters that could migrate to Aurora Serverless v2 based on engine and instance classes.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import aws_base, ensure_region, paginate, with_region, write_stdout_json


def collect(region: str) -> Dict[str, Any]:
    clusters = paginate(with_region(aws_base() + ["rds", "describe-db-clusters"], region), result_key="DBClusters")
    candidates: List[Dict[str, Any]] = []
    for c in clusters:
        engine = c.get("Engine", "")
        if engine and engine.startswith("aurora"):
            # If EngineMode already 'provisioned' and not serverless v2, consider candidate.
            if c.get("EngineMode", "provisioned") == "provisioned":
                candidates.append({
                    "DBClusterIdentifier": c.get("DBClusterIdentifier"),
                    "Engine": engine,
                    "EngineMode": c.get("EngineMode"),
                })
    return {"region": region, "totalClusters": len(clusters), "serverlessV2Candidates": candidates}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    write_stdout_json(collect(ensure_region(args.region)))


if __name__ == "__main__":
    main()
