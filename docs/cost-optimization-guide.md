# AWS Cost Optimization Guide (FinOps Playbook)

Este playbook sintetiza prácticas de FinOps aplicables a AWS para reducir costos, mejorar visibilidad y gobernanza, y sostener eficiencia en el tiempo. Está organizado por dominios: Medir, Optimizar, Gobernar y Automatizar.

## 1) Medir y Asignar Costos

- Etiquetado de costos: estandarizar y requerir `CostCenter`, `Owner`, `Environment`, `Application`. Aplicar en cuentas, OU, y pipelines (shift-left tagging).
- Fuentes de datos: AWS Cost Explorer (CE), Cost & Usage Report (CUR), Compute Optimizer, AWS Budgets, AWS Anomaly Detection, CloudWatch, CloudTrail.
- Segmentación: agrupar por `LINKED_ACCOUNT`, `SERVICE`, `TAG:CostCenter` y `USAGE_TYPE`. Mantener paneles diarios y mensuales.
- Forecast: usar CE `get-cost-forecast` para horizonte 30/60/90 días y sensibilidad a estacionalidad.

## 2) Optimizar Recursos de Cómputo

- Rightsizing EC2: habilitar Compute Optimizer, revisar recomendaciones (vCPU/Memory), familias Graviton (ARM) para ahorro 20–40%. Sustituir t2/t3 por t4g donde aplique.
- Modelos de compra: Savings Plans (Compute/EC2) con cobertura objetivo 70–90% de carga base; RIs para casos específicos (RDS/Aurora/Redshift/ElastiCache/OpenSearch).
- Auto Scaling: políticas basadas en métricas (CPU, request rate, queue depth). Evitar sobreaprovisionamiento.</n+- Spot: workloads tolerantes a interrupciones (batch, CI/CD, render, ML preemptible) con diversidad de tipos/AZ.

## 3) Optimizar Almacenamiento y Datos

- S3: políticas de ciclo de vida (IA/One Zone IA/Glacier), expiración de objetos temporales, replicación selectiva; S3 Storage Lens para gobernanza.
- EBS: eliminar volúmenes sin adjuntar, ajustar tipo (gp3 frente a gp2/io1), bajar provisión IOPS/Throughput no usado. Snapshots antiguos a Archive.
- Logs: retención explícita en CloudWatch Logs; exportar a S3 con ciclo de vida.

## 4) Optimizar Bases de Datos

- RDS/Aurora: rightsizing de instancia y almacenamiento; activar auto-scaling de réplicas de lectura; Aurora Serverless v2 para cargas variables. Programación de apagado en ambientes no productivos.
- Cachear para reducir RDS (ElastiCache). Revisar conexiones y consultas lentas.

## 5) Red y Transferencias

- NAT Gateway: consolidación por AZ, evaluar endpoints privados (S3/DynamoDB) para evitar NAT; revisar tráfico cross-AZ y egress a Internet/CDN.
- Egress: CloudFront para contenidos; DirectConnect si corresponde.

## 6) Gobernanza y Controles Preventivos

- Budgets: por cuenta/servicio/centro de costo, alertas en 50/80/100% del gasto previsto.
- Anomaly Detection: monitores por cuenta y por servicio crítico; triage diario/semanal.
- SCPs: evitar tipos caros por defecto, requerir tags, bloquear regiones no autorizadas.
- Programación de horarios: apagar dev/test por calendario (EventBridge + Lambda + SSM).

## 7) Automatización y Ciclo de Vida

- Pipelines: validación de tags obligatorios en IaC/CI, templates de módulos con defaults eficientes.
- Reconciliación: tareas diarias/semanales que corren detectores (idle, sin tags, sin lifecycle) y abren issues/tickets.
- Inventario: catálogo de servicios habilitados, cuentas y regiones permitidas.

## Métricas Clave (KPIs)

- Costo total por día/mes y por servicio.
- Cobertura y utilización de Savings Plans/RI.
- % de recursos con tags completos requeridos.
- % de buckets con lifecycle activo; % de log groups con retención definida.
- Recursos candidatos a rightsizing/apagado (EC2/RDS/Lambda/EBS).

## Operación

- Cadencia: revisión semanal de deltas y anomalías, mensual de compromisos SP/RI, trimestral de arquitectura de costos.
- Runbooks: playbooks para aplicar recomendaciones con rollback y ventanas de mantenimiento.

## Referencias

- AWS Well-Architected – Cost Optimization Pillar.
- AWS Compute Optimizer, Cost Explorer, CUR, Budgets, Anomaly Detection.
