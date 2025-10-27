#!/usr/bin/env python3
"""
List AWS Cost Anomaly Detection monitors and recent anomalies.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from typing import Any, Dict

from common import aws_base, ensure_region, shell_json, with_region, write_stdout_json


def collect(region: str, days: int) -> Dict[str, Any]:
    monitors = shell_json(with_region(aws_base() + ["ce", "list-anomaly-monitors"], region))
    end = date.today()
    start = end - timedelta(days=days)
    monitor_arns = [m.get("MonitorArn", "") for m in monitors.get("AnomalyMonitors", []) if m.get("MonitorArn")]
    anomalies: Dict[str, Any] = {}
    if monitor_arns:
        anomalies = shell_json(
            with_region(
                aws_base()
                + [
                    "ce",
                    "get-anomalies",
                    "--monitor-arn-list",
                    ",".join(monitor_arns),
                    "--date-interval",
                    f"StartDate={start.isoformat()},EndDate={end.isoformat()}",
                ],
                region,
            )
        )
    return {"monitors": monitors, "anomalies": anomalies}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None)
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()
    write_stdout_json(collect(ensure_region(args.region), args.days))


if __name__ == "__main__":
    main()
