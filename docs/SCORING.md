# Risk scoring model

Implementation: [`n8n/code-nodes/compute_score.js`](../n8n/code-nodes/compute_score.js) · Tests: [`tests/code-nodes.test.js`](../tests/code-nodes.test.js) · Prompt: [`n8n-files/maestro/prompt_tprm.txt`](../n8n-files/maestro/prompt_tprm.txt)

## 1. Control rubric (applied by the LLM)

| Score | Meaning |
|---:|---|
| 5 | Fully compliant, evidence verified and current |
| 4 | Compliant, partial evidence or in progress |
| 3 | Partially compliant or no documentary evidence |
| 2 | Not compliant, remediation plan with a date |
| 1 | Not compliant, no remediation plan |
| null | Not enough information in the document |

The prompt forces `null` instead of guesses: *"Extract ONLY information explicitly present in the document."*

## 2. Sections and weights (applied in code)

| Prefix | Section | Weight | Controls |
|---|---|---:|---|
| `s1_` | Information security | 30% | normativa, política, análisis de riesgos, localización, DPO, incidentes, auditoría, formación, vulnerabilidades, IRP, clasificación |
| `s2_` | IAM | 25% | mínimo privilegio, MFA, baja de accesos, PAM, access review |
| `s3_` | Business continuity | 15% | BCP (`rto_horas`/`rpo_horas` are stored as data, not scored) |
| `s4_` | Data protection | 20% | DPA, transferencias internacionales, base legal, TIA, medidas técnicas, acceso remoto, notificación de brechas |
| `s5_` | Cloud | 5% | certificación cloud, CSPM |
| `s6_` | Sub-processors | 5% | subcontrata, cascada, controles a subcontratistas |

```
section_mean = mean(non-null controls)          # null if > 50 % of controls are null
score        = round( Σ section_mean × weight × 20 )   # 0–100
```

## 3. Result

| Condition | Result |
|---|---|
| any section is null | **Evaluación incompleta** |
| score ≥ 80 | **Aprobado** |
| 60 ≤ score < 80 | **Aprobado con condiciones** |
| score < 60 | **Rechazado** |
| any gap with `bloquea_aprobacion: true` | capped at **Rechazado** |

Blocking gaps: no MFA on critical access · no DPA when processing personal data · international transfer without TIA · expired certification · no PAM on tier 1/2 vendors.

The LLM's own `score_total` is kept as `scoring.score_llm` for audit, but it is never used as the result.
