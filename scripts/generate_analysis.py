#!/usr/bin/env python3
"""
Generate reports/analysis.txt from JSON files in reports/data.
Robust to missing files; fills N/A gracefully. No external deps.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "reports", "data")
OUT = os.path.join(ROOT, "reports", "analysis.txt")


def jload(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def first_existing(*names: str) -> Optional[Dict[str, Any]]:
    for n in names:
        p = os.path.join(DATA, n)
        if os.path.exists(p):
            return jload(p)
    return None


def cost_by_service_summary(d: Optional[Dict[str, Any]]) -> Dict[str, float]:
    agg: Dict[str, float] = {}
    if not d:
        return agg
    for period in d.get("ResultsByTime", []):
        for g in period.get("Groups", []):
            keys = g.get("Keys", [])
            svc = keys[0] if keys else "Unknown"
            amt = float(g.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", 0.0) or 0.0)
            agg[svc] = agg.get(svc, 0.0) + amt
    return agg


def sum_last_30_days(d: Optional[Dict[str, Any]]) -> float:
    if not d:
        return 0.0
    periods = d.get("ResultsByTime", [])
    last = periods[-30:] if len(periods) > 0 else []
    total = 0.0
    for p in last:
        for g in p.get("Groups", []):
            total += float(g.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", 0.0) or 0.0)
    return total


def sp_summary(d: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not d:
        return {"count": 0, "estimatedSavings": 0.0}
    recs = (d.get("SavingsPlansPurchaseRecommendation", {}).get("SavingsPlansPurchaseRecommendationDetails") or [])
    savings = 0.0
    for r in recs:
        try:
            savings += float(r.get("EstimatedSavingsAmount", 0.0) or 0.0)
        except Exception:
            pass
    return {"count": len(recs), "estimatedSavings": savings}


def ri_summary(d: Optional[Dict[str, Any]]) -> int:
    if not d:
        return 0
    # Different CE shapes; prefer Recommendations
    if isinstance(d.get("Recommendations"), list):
        return len(d.get("Recommendations"))
    if isinstance(d.get("RecommendationSummaries"), list):
        return len(d.get("RecommendationSummaries"))
    return 0


def last_nat_cost(d: Optional[Dict[str, Any]]) -> float:
    if not d:
        return 0.0
    arr = d.get("natServiceCosts", [])
    if arr:
        last = arr[-1]
        try:
            return float(last.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0.0) or 0.0)
        except Exception:
            return 0.0
    return 0.0


def write_report(text: str) -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)


def main() -> None:
    identity = first_existing("identity.json") or {}
    cost_by_service = first_existing("cost_by_service_90d.json")
    forecast = first_existing("forecast_30d.json")
    sp = first_existing("sp_recommendations.json")
    ri = first_existing("ri_ec2_recommendations.json")
    ec2 = first_existing("ec2_idle.json") or {}
    ebs = first_existing("ebs_optimizer.json") or {}
    lam = first_existing("lambda_optimizer.json") or {}
    rds = first_existing("rds_rightsizing.json") or {}
    nat = first_existing("nat.json") or {}
    logs = first_existing("logs_retention.json") or {}
    s3 = first_existing("s3_lifecycle.json") or {}
    snaps = first_existing("ebs_snapshots.json") or {}
    tags = first_existing("tag_compliance.json") or {}

    svc_map = cost_by_service_summary(cost_by_service)
    top = sorted(svc_map.items(), key=lambda kv: kv[1], reverse=True)[:10]
    last30_sum = sum_last_30_days(cost_by_service)
    sp_sum = sp_summary(sp)
    ri_count = ri_summary(ri)

    lines: List[str] = []
    lines.append("AWS Cost Optimization – Informe de Análisis")
    lines.append(f"Fecha: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')}")
    lines.append("")
    lines.append("Resumen ejecutivo")
    lines.append(f"- Cuenta: {identity.get('Account', 'N/A')}")
    lines.append(f"- Gasto estimado últimos 30d: ${last30_sum:,.2f}")
    lines.append(f"- Recomendaciones SP: {sp_sum['count']} (ahorro estimado: ${sp_sum['estimatedSavings']:,.2f})")
    lines.append(f"- Recomendaciones RI (EC2): {ri_count}")
    lines.append(f"- Candidatos EC2 rightsizing: {ec2.get('count', 0)}")
    lines.append(f"- Volúmenes EBS sin adjuntar: {len(ebs.get('unattached', []) )}")
    lines.append(f"- Lambda (Compute Optimizer recs): {len(lam.get('computeOptimizer', []) )}")
    lines.append(f"- RDS rightsizing: {len((rds.get('rightsizing') or {}).get('recommendations', []))}")
    lines.append(f"- NATs: {nat.get('totalNatGateways', 0)} (último costo: ${last_nat_cost(nat):,.2f})")
    lines.append(f"- Log groups sin retención: {logs.get('withoutRetention', 0)}")
    lines.append(f"- Buckets sin lifecycle: {s3.get('withoutLifecycle', 0)}")
    lines.append(f"- Snapshots EBS > umbral: {snaps.get('olderThanThreshold', 0)}")
    lines.append(f"- Recursos sin tags requeridos: {tags.get('nonCompliant', 0)}")
    lines.append("")
    lines.append("Top servicios por costo (90d)")
    if top:
        for name, val in top:
            lines.append(f"- {name}: ${val:,.2f}")
    else:
        lines.append("- Sin datos (habilita Cost Explorer y ejecuta collect_report.sh)")
    lines.append("")
    lines.append("Recomendaciones rápidas (basadas en datos)")
    if ec2.get("count", 0) > 0:
        lines.append("- EC2: aplicar rightsizing en candidatos detectados; evaluar migración a Graviton.")
    if len(ebs.get("unattached", [])) > 0:
        lines.append("- EBS: eliminar volúmenes sin adjuntar y revisar gp2→gp3.")
    if logs.get("withoutRetention", 0) > 0:
        lines.append("- Logs: definir retención explícita (30–90d) y exportar a S3.")
    if s3.get("withoutLifecycle", 0) > 0:
        lines.append("- S3: añadir lifecycle (IA/Glacier) y expirar temporales.")
    if snaps.get("olderThanThreshold", 0) > 0:
        lines.append("- Snapshots: archivar/eliminar snapshots antiguos.")
    if tags.get("nonCompliant", 0) > 0:
        lines.append("- Gobernanza: remediar tags (CostCenter/Owner/Environment/Application).")
    if sp_sum["count"] > 0 or ri_count > 0:
        lines.append("- Compromisos: revisar recomendaciones de SP/RI y definir cobertura 70–90% de base.")
    if nat.get("totalNatGateways", 0) > 0:
        lines.append("- Red: usar Gateway Endpoints (S3/DynamoDB) y consolidar NAT por AZ.")

    write_report("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

