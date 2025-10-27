#!/usr/bin/env python3
"""
List existing AWS Budgets and emit recommended thresholds for a monthly cost budget per account and service.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict

from common import aws_base, ensure_region, paginate, with_region, write_stdout_json


def list_budgets(region: str) -> Dict[str, Any]:
    budgets = paginate(with_region(aws_base() + ["budgets", "describe-budgets"], region), result_key="Budgets")
    return {"budgets": budgets}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    args = ap.parse_args()
    region = ensure_region(args.region)
    data = list_budgets(region)
    data["recommendation"] = {
        "monthlyBudget": "Definir presupuesto mensual por cuenta y por servicio crítico",
        "alerts": ["50%", "80%", "100%"],
    }
    write_stdout_json(data)


if __name__ == "__main__":
    main()
