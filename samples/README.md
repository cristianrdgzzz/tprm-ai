# Samples

All data here is **synthetic** — fictional vendors created to test the pipeline.

- `anonymization_example.json` — input text and the output of `POST /anonymize` (used by the unit tests).
- `output/assessment_cloudatlas.json` — a real assessment from the pipeline, re-scored with `compute_score.js` (the LLM said 83.5 / Aprobado; with three sections without evidence the computed result is *Evaluación incompleta*).
- `vendor-docs/` — fictional vendor evidence pack (*CloudAtlas*: ISO 27001 certificate, SOC 2 summary, DPA, BCP/DRP, pentest, sub-processors, security questionnaire, cyber-insurance; *TechNova*). Copy them to `n8n-files/input/` to run the pipeline end-to-end.
