#!/usr/bin/env python3
"""
Check tag compliance across core services for required keys: CostCenter, Owner, Environment, Application.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import aws_base, ensure_region, paginate, with_region, write_stdout_json

REQUIRED = {"CostCenter", "Owner", "Environment", "Application"}


def missing(required: set, tags: List[Dict[str, str]]) -> List[str]:
    present = {t.get("Key") for t in (tags or [])}
    return sorted(list(required - present))


def ec2_instances(region: str) -> List[Dict[str, Any]]:
    res = paginate(with_region(aws_base() + ["ec2", "describe-instances", "--max-results", "1000"], region), result_key="Reservations")
    items: List[Dict[str, Any]] = []
    for r in res:
        for i in r.get("Instances", []):
            items.append({"id": i.get("InstanceId"), "type": "ec2", "missing": missing(REQUIRED, i.get("Tags", []))})
    return items


def ebs_volumes(region: str) -> List[Dict[str, Any]]:
    vols = paginate(with_region(aws_base() + ["ec2", "describe-volumes", "--max-results", "500"], region), result_key="Volumes")
    return [{"id": v.get("VolumeId"), "type": "ebs", "missing": missing(REQUIRED, v.get("Tags", []))} for v in vols]


def s3_buckets(region: str) -> List[Dict[str, Any]]:
    # S3 tagging via get-bucket-tagging per bucket
    out: List[Dict[str, Any]] = []
    import subprocess, json
    code, stdout = subprocess.getstatusoutput("aws s3api list-buckets --output json")
    if code == 0:
        for b in json.loads(stdout).get("Buckets", []):
            name = b.get("Name")
            if not name:
                continue
            # ignore errors (no tags)
            rc, so = subprocess.getstatusoutput(
                f"aws s3api get-bucket-tagging --bucket {name} --output json 2>/dev/null || echo '{{}}'"
            )
            try:
                tags = json.loads(so).get("TagSet", [])
            except Exception:
                tags = []
            out.append({"id": name, "type": "s3", "missing": missing(REQUIRED, tags)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    region = ensure_region(args.region)
    items = ec2_instances(region) + ebs_volumes(region) + s3_buckets(region)
    non_compliant = [i for i in items if i.get("missing")]
    write_stdout_json({"region": region, "checked": len(items), "nonCompliant": len(non_compliant), "items": non_compliant[:500]})


if __name__ == "__main__":
    main()
