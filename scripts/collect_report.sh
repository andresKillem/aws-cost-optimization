#!/usr/bin/env bash
set -euo pipefail

# Collects FinOps data into reports/data using AWS CLI and the Python helpers.
# Requirements: awscli v2, jq, bash. Credentials must be exported in the environment.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$ROOT_DIR/reports/data"
mkdir -p "$DATA_DIR"

region() {
  echo "${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
}

log() { echo "[collect] $*"; }

date_start_end() {
  local days=${1:-90}
  local end start
  end=$(date +%F)
  # macOS BSD date supports -v; fallback to python if unavailable
  if start=$(date -v -"${days}"d +%F 2>/dev/null); then
    :
  else
    start=$(python3 - <<PY
from datetime import datetime, timedelta
print((datetime.utcnow()-timedelta(days=${days})).strftime('%Y-%m-%d'))
PY
)
  fi
  echo "$start" "$end"
}

collect_identity() {
  log "STS caller identity"
  aws sts get-caller-identity --output json >"$DATA_DIR/identity.json" \
    || echo '{}' >"$DATA_DIR/identity.json"
}

collect_costs() {
  log "Cost by service (90d, daily)"
  read -r START END < <(date_start_end 90)
  aws ce get-cost-and-usage \
    --time-period Start="$START",End="$END" \
    --granularity DAILY \
    --metrics UnblendedCost \
    --group-by Type=DIMENSION,Key=SERVICE \
    --output json >"$DATA_DIR/cost_by_service_90d.json" || echo '{}' >"$DATA_DIR/cost_by_service_90d.json"

  log "Cost by account (90d, monthly)"
  aws ce get-cost-and-usage \
    --time-period Start="$START",End="$END" \
    --granularity MONTHLY \
    --metrics UnblendedCost \
    --group-by Type=DIMENSION,Key=LINKED_ACCOUNT \
    --output json >"$DATA_DIR/cost_by_account_90d.json" || echo '{}' >"$DATA_DIR/cost_by_account_90d.json"
}

collect_forecast() {
  log "Cost forecast (30d)"
  local START END
  # Cost Explorer forecasting usually starts on the next UTC day
  if START=$(date -v +1d +%F 2>/dev/null); then :; else START=$(python3 - <<PY
from datetime import datetime, timedelta
print((datetime.utcnow()+timedelta(days=1)).strftime('%Y-%m-%d'))
PY
); fi
  if END=$(date -v +31d +%F 2>/dev/null); then :; else END=$(python3 - <<PY
from datetime import datetime, timedelta
print((datetime.utcnow()+timedelta(days=31)).strftime('%Y-%m-%d'))
PY
); fi
  aws ce get-cost-forecast --metric UNBLENDED_COST \
    --time-period Start="$START",End="$END" \
    --granularity DAILY --output json >"$DATA_DIR/forecast_30d.json" || echo '{}' >"$DATA_DIR/forecast_30d.json"
}

collect_purchase_recs() {
  log "Savings Plans recommendations"
  aws ce get-savings-plans-purchase-recommendation \
    --savings-plans-type COMPUTE_SP --term-in-years ONE_YEAR \
    --payment-option NO_UPFRONT --lookback-period-in-days THIRTY_DAYS \
    --output json >"$DATA_DIR/sp_recommendations.json" || echo '{}' >"$DATA_DIR/sp_recommendations.json"

  log "RI recommendations (EC2)"
  aws ce get-reservation-purchase-recommendation \
    --service "Amazon Elastic Compute Cloud - Compute" --term-in-years ONE_YEAR --payment-option NO_UPFRONT \
    --lookback-period-in-days THIRTY_DAYS --output json >"$DATA_DIR/ri_ec2_recommendations.json" || echo '{}' >"$DATA_DIR/ri_ec2_recommendations.json"
}

collect_services() {
  log "Compute Optimizer / EC2 idle"
  python3 "$ROOT_DIR/scripts/ec2-idle-detector.py" --region "$(region)" >"$DATA_DIR/ec2_idle.json" || echo '{}' >"$DATA_DIR/ec2_idle.json"

  log "EBS optimizer"
  python3 "$ROOT_DIR/scripts/ebs-volume-optimizer.py" --region "$(region)" >"$DATA_DIR/ebs_optimizer.json" || echo '{}' >"$DATA_DIR/ebs_optimizer.json"

  log "Lambda optimizer"
  python3 "$ROOT_DIR/scripts/lambda-cost-optimizer.py" --region "$(region)" >"$DATA_DIR/lambda_optimizer.json" || echo '{}' >"$DATA_DIR/lambda_optimizer.json"

  log "RDS rightsizing"
  python3 "$ROOT_DIR/scripts/rds-rightsizing.py" --region "$(region)" >"$DATA_DIR/rds_rightsizing.json" || echo '{}' >"$DATA_DIR/rds_rightsizing.json"

  log "NAT gateways + service cost"
  python3 "$ROOT_DIR/scripts/nat-gateway-optimizer.py" --region "$(region)" >"$DATA_DIR/nat.json" || echo '{}' >"$DATA_DIR/nat.json"

  log "CloudWatch logs retention"
  python3 "$ROOT_DIR/scripts/logs-retention-optimizer.py" --region "$(region)" >"$DATA_DIR/logs_retention.json" || echo '{}' >"$DATA_DIR/logs_retention.json"

  log "S3 lifecycle"
  python3 "$ROOT_DIR/scripts/s3-lifecycle-optimizer.py" --region "$(region)" >"$DATA_DIR/s3_lifecycle.json" || echo '{}' >"$DATA_DIR/s3_lifecycle.json"

  log "EBS snapshots"
  python3 "$ROOT_DIR/scripts/snapshot-cleanup.py" --region "$(region)" --days 180 >"$DATA_DIR/ebs_snapshots.json" || echo '{}' >"$DATA_DIR/ebs_snapshots.json"

  log "Tag compliance"
  python3 "$ROOT_DIR/scripts/tag-compliance-checker.py" --region "$(region)" >"$DATA_DIR/tag_compliance.json" || echo '{}' >"$DATA_DIR/tag_compliance.json"
}

main() {
  collect_identity
  collect_costs
  collect_forecast
  collect_purchase_recs
  collect_services
  log "Build analysis.txt"
  python3 "$ROOT_DIR/scripts/generate_analysis.py" || true
  log "Done. Data at $DATA_DIR"
}

main "$@"
