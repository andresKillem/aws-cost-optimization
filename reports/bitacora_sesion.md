# Bitácora de la sesión y metodología

Este documento resume todo lo que implementé en el proyecto durante esta sesión, cómo se generan los datos y cómo se obtuvieron los hallazgos que ves en el reporte.

## Qué se implementó

- Documentación
  - docs/cost-optimization-guide.md: guía FinOps (medir, optimizar, gobernar, automatizar, KPIs).
- Scripts de recolección y utilidades
  - scripts/common.py: utilidades compartidas (ejecución AWS CLI, paginación, fechas).
  - scripts/collect_report.sh: orquestador que genera JSON en reports/data y ejecuta el análisis.
  - scripts/generate_analysis.py: lee los JSON y genera reports/analysis.txt con cifras reales.
  - Relleno de scripts clave (con paginación y clean code):
    - ec2-idle-detector.py, ebs-volume-optimizer.py, lambda-cost-optimizer.py,
      rds-rightsizing.py, nat-gateway-optimizer.py, logs-retention-optimizer.py,
      s3-lifecycle-optimizer.py, snapshot-cleanup.py, multi-account-costs.py,
      cost-forecasting.py, cost-anomaly-detector.py, ri-recommender.py, savings-plan-calc.py,
      graviton-migration.py, eks-cost-optimizer.py, budget-automation.py, tag-compliance-checker.py.
- Reporte y dashboard
  - reports/index.html + reports/css/styles.css: tablero HTML (robusto, soporta ?mock=1).
  - reports/analysis.txt: análisis en texto plano (se genera automáticamente).
  - reports/sample-data/*: datos de muestra para visualizar sin acceso a AWS (modo `?mock=1`).

## Cómo se generan los datos

1) Exporta credenciales/región (o usa AWS_PROFILE) y ejecuta desde la raíz del proyecto:

```
bash scripts/collect_report.sh
```

2) Este script ejecuta AWS CLI y los scripts Python, escribiendo JSONs en `reports/data/`:

- `identity.json`: `aws sts get-caller-identity`.
- `cost_by_service_90d.json`: `aws ce get-cost-and-usage --granularity DAILY --metrics UnblendedCost --group-by SERVICE` (últimos 90 días).
- `forecast_30d.json`: `aws ce get-cost-forecast --metric UNBLENDED_COST --granularity DAILY`.
- `sp_recommendations.json`: `aws ce get-savings-plans-purchase-recommendation`.
- `ri_ec2_recommendations.json`: `aws ce get-reservation-purchase-recommendation`.
- `ec2_idle.json`: Compute Optimizer (o CE rightsizing fallback).
- `ebs_optimizer.json`: volúmenes sin adjuntar + recomendaciones de CO.
- `lambda_optimizer.json`: inventario Lambda + recomendaciones de CO.
- `rds_rightsizing.json`: CE rightsizing (RDS) + inventario RDS.
- `nat.json`: `describe-nat-gateways` + costo de `AWSNATGateway` en CE.
- `logs_retention.json`: `describe-log-groups` (sin `retentionInDays`).
- `s3_lifecycle.json`: buckets sin lifecycle.
- `ebs_snapshots.json`: snapshots propios > umbral de días.
- `tag_compliance.json`: cumplimiento de tags (EC2, EBS, S3).

3) El script llama a `scripts/generate_analysis.py`, que produce `reports/analysis.txt` consolidando cifras (maneja faltantes con N/A).

4) Para ver el tablero: `cd reports && python3 -m http.server 8010` y abrir `http://localhost:8010`.
   - Sin datos reales, se puede usar `?mock=1` para cargar `reports/sample-data`.

## Cómo se obtuvieron los hallazgos (fuente de cada número)

Resumen de hallazgos (ejemplo de una corrida reciente):

- Top servicios por costo (90 días):
  - Amazon CloudWatch = $35,344.47
  - Amazon Simple Email Service = $16,509.90
  - EC2 - Other = $7,206.88
  - Amazon RDS = $7,199.92
  - AWS Network Firewall = $5,172.26
  - (ver resto en el reporte)
- CloudWatch Logs: 52 de 347 log groups sin retención definida.
- S3 Lifecycle: 0 de 44 buckets sin lifecycle (bien).
- EBS:
  - 6 volúmenes sin adjuntar (candidatos a eliminación/archivar).
  - 0 snapshots > 180 días (bien).
- Tags: 252/252 recursos revisados sin los tags requeridos (CostCenter, Owner, Environment, Application).
- Compute Optimizer:
  - EC2: 0 candidatos (en este muestreo).
  - Lambda: 4 recomendaciones de ajuste.
- NAT Gateways: 0 inventariados.
- Compromisos (SP/RI): 0 recomendaciones en CE con la ventana consultada.

Trazabilidad de cada métrica:

- Top servicios (90d):
  - Archivo: `reports/data/cost_by_service_90d.json`.
  - Lógica: suma por servicio de `ResultsByTime[].Groups[].Metrics.UnblendedCost.Amount`.
- CloudWatch Logs sin retención:
  - Archivo: `reports/data/logs_retention.json`.
  - Campos: `withoutRetention` y `totalLogGroups`.
- S3 Lifecycle:
  - Archivo: `reports/data/s3_lifecycle.json`.
  - Campos: `withoutLifecycle` y `totalBuckets`.
- EBS sin adjuntar y snapshots:
  - Archivos: `reports/data/ebs_optimizer.json` (`unattached`) y `reports/data/ebs_snapshots.json` (`olderThanThreshold`).
- Tags incumplidos:
  - Archivo: `reports/data/tag_compliance.json`.
  - Campos: `checked`, `nonCompliant`.
- Compute Optimizer:
  - Archivos: `reports/data/ec2_idle.json` (campo `count`) y `reports/data/lambda_optimizer.json` (lista `computeOptimizer`).
- NAT Gateways:
  - Archivo: `reports/data/nat.json`.
  - Campos: `totalNatGateways` y último valor en `natServiceCosts[].Total.UnblendedCost.Amount`.
- SP/RI:
  - Archivos: `reports/data/sp_recommendations.json` y `reports/data/ri_ec2_recommendations.json`.
  - Conteo de recomendaciones según presencia en CE.

> Nota: si Cost Explorer/Compute Optimizer no están habilitados o permisos son insuficientes, el recolector deja `{}` para que el tablero siga funcionando y el análisis reporte 0/N/A. Habilitar los servicios mejora la calidad de las cifras.

## Recomendaciones prioritarias (derivadas de los hallazgos)

- CloudWatch/Logs
  - Definir retención 30–90 días según criticidad y exportar a S3 con lifecycle para histórico frío.
  - Ejemplo: `aws logs put-retention-policy --log-group-name <name> --retention-in-days 30`.
- EBS
  - Revisar/eliminar 6 volúmenes sin adjuntar. Base: `aws ec2 describe-volumes --filters Name=status,Values=available`.
  - Considerar snapshot previo y/o archive tier para conservación.
- Tags y Gobernanza
  - Exigir tags obligatorios (CostCenter, Owner, Environment, Application) en CI/IaC y con SCPs.
  - Reparar 252 recursos y automatizar validaciones en pipelines.
- Lambda
  - Aplicar recomendaciones de Compute Optimizer para memoria/timeout y tamaño de paquetes.
- Cost Explorer/Compromisos
  - Si no hay SP/RI, revisar ventana y patrón de consumo; usar Compute SP si hay base on‑demand estable (70–90%).
- CloudWatch (cost driver)
  - Auditar métricas de alta resolución y custom metrics; reducir resolución donde sea viable.
  - Consolidar dashboards/alarms redundantes.

## TODO / pendientes

- Habilitar y verificar permisos para Cost Explorer y Compute Optimizer en todas las cuentas/regiones relevantes.
- Configurar AWS Budgets y Cost Anomaly Detection con notificaciones (Email/Slack/SNS) por cuenta y por servicio crítico.
- Definir y aplicar Tag Policies/Conformance Packs para enforcement de tags requeridos.
- Programar ejecución periódica (EventBridge + CodeBuild/SSM) de `scripts/collect_report.sh` y publicación del reporte.
- Extender cobertura multi‑cuenta vía AWS Organizations (assume role) en `collect_report.sh`.
- Añadir exportación `analysis.md` (Markdown) y CSVs para BI.
- Validar lifecycle en buckets de logs y crear Storage Lens para gobernanza.
- Añadir checks de endpoints privados (S3/DynamoDB) y análisis de egress.

