#!/usr/bin/env python3
"""
Report S3 buckets missing lifecycle configuration and suggest lifecycle policies.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import aws_base, ensure_region, shell_json, write_stdout_json


def list_buckets() -> List[Dict[str, Any]]:
    return shell_json(aws_base() + ["s3api", "list-buckets"]).get("Buckets", [])


def bucket_has_lifecycle(name: str, region: str) -> bool:
    try:
        shell_json(["aws", "s3api", "get-bucket-lifecycle-configuration", "--bucket", name, "--output", "json"])
        return True
    except Exception:
        return False


def collect(region: str) -> Dict[str, Any]:
    buckets = list_buckets()
    missing: List[str] = []
    for b in buckets:
        name = b.get("Name")
        if not name:
            continue
        if not bucket_has_lifecycle(name, region):
            missing.append(name)
    return {
        "region": region,
        "totalBuckets": len(buckets),
        "withoutLifecycle": len(missing),
        "buckets": missing,
        "recommendation": {
            "policy": "Transicionar a S3 Standard-IA a 30d; Glacier a 90/180d; expirar temporales.",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    data = collect(args.region or "us-east-1")
    write_stdout_json(data)


if __name__ == "__main__":
    main()
