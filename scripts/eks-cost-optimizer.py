#!/usr/bin/env python3
"""
Summarize EKS clusters and nodegroups; recommend cluster autoscaler, right-sizing, and SP coverage for worker nodes.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import aws_base, ensure_region, paginate, with_region, write_stdout_json


def collect(region: str) -> Dict[str, Any]:
    clusters = paginate(with_region(aws_base() + ["eks", "list-clusters"], region), result_key="clusters")
    details: List[Dict[str, Any]] = []
    for c in clusters:
        # Nodegroups
        ngs = paginate(with_region(aws_base() + ["eks", "list-nodegroups", "--cluster-name", c], region), result_key="nodegroups")
        details.append({"cluster": c, "nodegroups": ngs})
    return {"region": region, "clusters": details, "recommendations": [
        "Habilitar/validar Cluster Autoscaler o Karpenter para burst.",
        "Usar SP Compute para cubrir nodos on-demand base; spot diversificado para burst.",
        "Usar gp3 y tamaño de disco adecuado en nodos; logs con retención explícita.",
    ]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    write_stdout_json(collect(ensure_region(args.region)))


if __name__ == "__main__":
    main()
