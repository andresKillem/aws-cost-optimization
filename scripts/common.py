#!/usr/bin/env python3
"""
Common helpers for AWS CLI based collectors.
- Ultra-light dependency footprint: uses subprocess + json
- Safe pagination: handles --starting-token/NextToken loops
- Clean code: type hints, small functions, clear responsibilities
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _run(cmd: List[str], env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, **(env or {})},
        text=True,
    )
    out, err = proc.communicate()
    return proc.returncode, out, err


def shell_json(cmd: List[str]) -> Dict[str, Any]:
    """
    Executes an AWS CLI command that returns JSON and parses it.
    Raises RuntimeError if the command fails or output is not JSON.
    """
    code, out, err = _run(cmd)
    if code != 0:
        raise RuntimeError(f"Command failed: {' '.join(map(shlex.quote, cmd))}\n{err}")
    try:
        return json.loads(out or '{}')
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from: {' '.join(cmd)}\n{out}\n{e}")


def paginate(cmd: List[str], result_key: str, token_key: str = 'NextToken') -> List[Dict[str, Any]]:
    """
    Paginates AWS CLI v2 commands that support --starting-token and output NextToken.
    Returns a flat list aggregated from pages. Expects each page to have a list under `result_key`.
    """
    items: List[Dict[str, Any]] = []
    starting_token: Optional[str] = None
    while True:
        final_cmd = list(cmd)
        if starting_token:
            final_cmd += ["--starting-token", starting_token]
        page = shell_json(final_cmd)
        page_items = page.get(result_key, [])
        if isinstance(page_items, list):
            items.extend(page_items)
        starting_token = page.get(token_key)
        if not starting_token:
            break
    return items


def date_range(days_back: int) -> Tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days_back)
    return start.isoformat(), end.isoformat()


def default_region() -> str:
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def ensure_region(region: Optional[str]) -> str:
    return region or default_region()


def aws_base() -> List[str]:
    return ["aws", "--output", "json"]


def with_region(cmd: List[str], region: Optional[str]) -> List[str]:
    r = ensure_region(region)
    return cmd + ["--region", r]


def identity() -> Dict[str, Any]:
    return shell_json(aws_base() + ["sts", "get-caller-identity"]) or {}


def write_stdout_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, sort_keys=True, default=str)
    sys.stdout.write("\n")

