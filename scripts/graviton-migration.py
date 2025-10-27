#!/usr/bin/env python3
"""
Suggest EC2 instance families to migrate from x86 to Graviton (ARM) based on instance types.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import aws_base, ensure_region, paginate, with_region, write_stdout_json


def collect(region: str) -> Dict[str, Any]:
    inst = paginate(
        with_region(aws_base() + ["ec2", "describe-instances", "--max-results", "1000"], region),
        result_key="Reservations",
    )
    candidates: List[Dict[str, Any]] = []
    for r in inst:
        for i in r.get("Instances", []):
            itype = i.get("InstanceType", "")
            # crude heuristic: g* are already Graviton; t4g, m6g, c6g, r6g, m7g, c7g, r7g are ARM
            if itype and not itype.startswith(("t4g", "m6g", "c6g", "r6g", "m7g", "c7g", "r7g")):
                candidates.append({
                    "InstanceId": i.get("InstanceId"),
                    "InstanceType": itype,
                    "SuggestedFamily": "m7g/c7g/r7g/t4g (validar compatibilidad ARM)",
                })
    return {"region": region, "candidates": candidates}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    write_stdout_json(collect(ensure_region(args.region)))


if __name__ == "__main__":
    main()
