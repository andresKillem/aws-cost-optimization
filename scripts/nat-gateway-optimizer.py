#!/usr/bin/env python3
"""
Inventory NAT Gateways and estimate cost hotspots. Suggests S3/DynamoDB gateway endpoints and consolidation.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from common import aws_base, ensure_region, paginate, shell_json, with_region, write_stdout_json


def collect(region: str) -> Dict[str, Any]:
    ngws = paginate(
        with_region(aws_base() + ["ec2", "describe-nat-gateways", "--max-results", "1000"], region),
        result_key="NatGateways",
    )
    # Cost by service (AWSNATGateway) last 30d
    costs: Dict[str, Any] = {}
    try:
        from datetime import date, timedelta

        end = date.today()
        start = end - timedelta(days=30)
        ce = shell_json(
            with_region(
                aws_base()
                + [
                    "ce",
                    "get-cost-and-usage",
                    "--time-period",
                    f"Start={start.isoformat()},End={end.isoformat()}",
                    "--granularity",
                    "MONTHLY",
                    "--metrics",
                    "UnblendedCost",
                    "--filter",
                    '{"Dimensions":{"Key":"SERVICE","Values":["AWSNATGateway"]}}',
                ],
                region,
            )
        )
        costs = ce.get("ResultsByTime", [])
    except Exception:
        costs = {}

    return {
        "region": region,
        "totalNatGateways": len(ngws),
        "items": [
            {
                "NatGatewayId": n.get("NatGatewayId"),
                "State": n.get("State"),
                "SubnetId": n.get("SubnetId"),
                "VpcId": n.get("VpcId"),
                "ConnectivityType": n.get("ConnectivityType"),
                "Tags": n.get("Tags", []),
            }
            for n in ngws
        ],
        "natServiceCosts": costs,
        "recommendations": [
            "Usar Gateway Endpoints para S3/DynamoDB en VPCs con NAT para reducir egress.",
            "Consolidar NAT por AZ y evitar tráfico cross-AZ.",
            "Revisar rutas por defecto y endpoints privados (Interface Endpoints).",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    data = collect(ensure_region(args.region))
    write_stdout_json(data)


if __name__ == "__main__":
    main()
