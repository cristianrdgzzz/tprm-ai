# Informe Técnico — TPRM-AI

**Sistema local de análisis automatizado de riesgo de proveedores (Third-Party Risk Management)**
**Stack principal:** Kali Linux · Docker Compose · n8n · Presidio (modificado) · PostgreSQL 16 · Qdrant · OpenRouter (LLM)

**Fecha:** 1 de julio de 2026
**Versión:** 1.0
**Estado del proyecto:** En desarrollo — pipeline principal operativo end-to-end; capa RAG en construcción.

> Este documento describe la **arquitectura actual** del sistema tal como está construida a la fecha, no la arquitectura objetivo final. Cada componente indica explícitamente si está *implementado*, *en diseño/en progreso* o *trabajo futuro*. Donde la información no consta en la documentación de origen se marca como **[A definir]**.

---

## 1. Resumen técnico

TPRM-AI es un sistema automatizado de evaluación de riesgo de proveedores que se ejecuta **íntegramente en local** sobre una máquina Kali Linux mediante Docker Compose. El pipeline ingiere documentos de seguridad de proveedores (PDFs nativos o escaneados), extrae su texto, **anonimiza los datos personales y sensibles** con una versión modificada de Microsoft Presidio adaptada al español empresarial, envía únicamente el texto anonimizado a un modelo de lenguaje (LLM) para la evaluación TPRM, **desanonimiza** el resultado con un mapa reversible y persiste la ficha del proveedor y su puntuación en PostgreSQL, generando además un inventario en CSV.

La orquestación de todo el flujo se realiza con **n8n** (v2.22.6 self-hosted). La anonimización se expone como una **API REST FastAPI** que envuelve el módulo Presidio modificado. El análisis de riesgo lo realiza el modelo `meta-llama/llama-3.3-70b-instruct:free` a través de **OpenRouter**, que es el único componente externo a la infraestructura local y que **solo recibe texto anonimizado**. La persistencia central es **PostgreSQL 16**; **Qdrant** actúa como base de datos vectorial para una capa de recuperación aumentada (RAG) actualmente **en construcción**, apoyada en un servicio local de *embeddings* (`text-embeddings-inference` con `intfloat/multilingual-e5-large`).

El sistema mantiene un principio de diseño transversal: los datos personales reales nunca abandonan la máquina. Todo lo que sale hacia el LLM externo va anonimizado, y la reversión a datos reales se hace dentro de n8n con el mapa de entidades generado por Presidio.

---

## 2. Arquitectura del sistema

Diagrama general de la arquitectura actual. Los servicios entre corchetes son contenedores Docker en la red interna `tprm-ai_default`. Los puertos se indican como `host:contenedor`.

```
                             HOST: Kali Linux  (Docker Compose · red tprm-ai_default)
 ┌───────────────────────────────────────────────────────────────────────────────────────────┐
 │                                                                                             │
 │   Carpeta de entrada                                                                        │
 │   ./n8n-files/input/*.pdf                                                                   │
 │          │                                                                                  │
 │          ▼                                                                                  │
 │   ┌──────────────────────────────────────┐                                                 │
 │   │  n8n  [tprm_n8n]  5678:5678           │   Orquestador del pipeline                      │
 │   │  ─ NODO1 Scheduled / NODO2 ReadFiles  │                                                 │
 │   │  ─ Extract PDF ─ IF (texto/escaneado) │                                                 │
 │   │  ─ Switch ─ Merge "PDF"               │                                                 │
 │   └───────┬───────────────────┬───────────┘                                                 │
 │           │ (escaneado)       │ (texto extraído)                                            │
 │           ▼                   │                                                             │
 │   ┌───────────────┐           │                                                             │
 │   │ ocr-api       │           │      OCR de imágenes (Tesseract + FastAPI)                  │
 │   │ [ocr_api]     │           │      + contenedor tesseract [tesseract]                     │
 │   │ 8000:8000     │           │                                                             │
 │   └───────────────┘           │                                                             │
 │                               ▼                                                             │
 │        HTTP POST  http://presidio_anonymizer:3000/anonymize                                 │
 │   ┌──────────────────────────────────────────────┐                                         │
 │   │ presidio-anonymizer (custom)                  │  Anonimización PII español              │
 │   │ [presidio_anonymizer] 5002:3000               │  FastAPI + Presidio modificado          │
 │   │ analyzer (spaCy es_core_news_md) + anonymizer │  → {anonymized_text, mapping}           │
 │   └───────────────┬────────────────────────────────┘                                        │
 │                   │ anonymized_text + mapping                                               │
 │        ┌──────────┴───────────────────────────┐                                             │
 │        │ (Rama A: trazabilidad)               │ (Rama B: análisis IA)                       │
 │        ▼                                      ▼                                             │
 │  ┌───────────────────────────┐        ┌───────────────────────────────┐                    │
 │  │ PostgreSQL [tprm_postgres]│        │  Lee Prompt + convertir_a_json │                    │
 │  │ 5432:5432                 │        │  (prompt + texto anonimizado)  │                    │
 │  │ tabla anonymized_documents│        └───────────────┬───────────────┘                    │
 │  │ + UPSERT mínimo vendors   │                        │  HTTP POST (Bearer API key)         │
 │  └───────────────────────────┘                        ▼                                     │
 │                                              ═══════════════════════   (ÚNICO SALTO EXTERNO)│
 │                                              OpenRouter  (cloud)                             │
 │                                              meta-llama/llama-3.3-70b-instruct:free          │
 │                                              recibe SOLO texto anonimizado                   │
 │                                              ═══════════════════════                         │
 │                                                       │  JSON TPRM (con placeholders)        │
 │                                                       ▼                                      │
 │                                              ┌───────────────────────────┐                  │
 │                                              │ limpiar_json + desanonimizar│                 │
 │                                              │ (Code JS, mapping en memoria)│                │
 │                                              └───────────────┬───────────┘                  │
 │                                                       │  JSON con datos reales               │
 │                                                       ▼                                      │
 │                                              ┌───────────────────────────┐                  │
 │                                              │ PostgreSQL UPSERT vendors  │                  │
 │                                              │ (COALESCE) → SELECT vendors│                  │
 │                                              │ → CSV inventario_vendors   │                  │
 │                                              └───────────────────────────┘                  │
 │                                                                                             │
 │   ── Capa RAG (EN CONSTRUCCIÓN) ────────────────────────────────────────────────────────   │
 │   ┌──────────────────────────────┐        ┌──────────────────────────────┐                 │
 │   │ embedding-api [tprm_embedding]│  HTTP  │ Qdrant [tprm_qdrant] 6333:6333│                 │
 │   │ 8080:80  TEI cpu-1.6          │───────▶│ colecciones:                  │                 │
 │   │ multilingual-e5-large (1024d) │        │  vendors_docs · vendors_assess.│                │
 │   └──────────────────────────────┘        └──────────────────────────────┘                 │
 │                                                                                             │
 └───────────────────────────────────────────────────────────────────────────────────────────┘
```

**Protocolos y puertos (según docker-compose.yml actual):**

- Comunicación interna entre contenedores por **nombre de servicio** en la red `tprm-ai_default` (p. ej. n8n llama a `http://presidio_anonymizer:3000`, `http://embedding-api:80`, `http://qdrant:6333`).
- Los puertos publicados hacia el host (`localhost`) son los de la columna izquierda de cada mapeo `host:contenedor`.
- El LLM es la **única** salida a Internet del flujo de datos, vía HTTPS a `https://openrouter.ai/api/v1/chat/completions`.

---

## 3. Stack tecnológico

| Tecnología | Versión | Rol en el sistema | Decisión de arquitectura |
|---|---|---|---|
| Kali Linux | [A definir] | Host de toda la infraestructura | Entorno de trabajo/pruebas del desarrollador; hibernación deshabilitada para procesos largos |
| Docker Compose | (v3.9 en compose; atributo `version` marcado como obsoleto) | Orquestación y aislamiento de todos los servicios | Mantiene el sistema reproducible y 100% local; una sola red interna |
| n8n | 2.22.6 (self-hosted) | Orquestador del pipeline (ingesta, llamadas HTTP, lógica, persistencia) | Automatización low-code; mismo motor conecta OCR, Presidio, LLM y PostgreSQL |
| PostgreSQL | 16 | Base de datos central (proveedores, documentos anonimizados) y backend interno de n8n | Fuente de verdad y trazabilidad RGPD; base única `tprm_ai` compartida con n8n |
| Presidio (Microsoft, **modificado**) | Fork del repo oficial | Anonimización de PII en español con reconocedores propios y mapa reversible | Los reconocedores oficiales daban muchos falsos positivos/negativos en español; se desarrolló un stack custom |
| spaCy | modelo `es_core_news_md` | Motor NLP en español dentro de Presidio | Requisito para NER en español |
| FastAPI + Uvicorn | [A definir] | Expone Presidio (`/anonymize`, `/health`) y el OCR como API REST | Presidio no traía servidor REST propio; se envolvió con FastAPI |
| Tesseract (OCR) | imagen `tesseractshadow/tesseract4re` + `pytesseract` | OCR de PDFs escaneados e imágenes | Extracción de texto cuando el PDF no lleva capa de texto |
| OpenRouter (LLM) | modelo `meta-llama/llama-3.3-70b-instruct:free` | Análisis TPRM y generación del JSON de evaluación | Modelo potente y gratuito para pruebas; **solo recibe texto anonimizado** |
| Qdrant | imagen `qdrant/qdrant` | Base de datos vectorial para RAG | Ya estaba en el stack; se reutiliza para contexto histórico (en construcción) |
| text-embeddings-inference (TEI) | `ghcr.io/huggingface/text-embeddings-inference:cpu-1.6` | Servicio local de *embeddings* | Coherencia con filosofía self-hosted; sin coste ni latencia externa |
| Modelo de embeddings | `intfloat/multilingual-e5-large` (1024 dimensiones) | Vectorización de texto en español para RAG | Buen rendimiento en español técnico/empresarial |
| pdfminer.six / PyMuPDF | [A definir] | Extracción de texto de PDFs | `pdfminer` usado en pruebas de Presidio |
| Python | 3.11 (imagen base de la API custom) | Desarrollo de reconocedores y servidor de anonimización | Lenguaje nativo de Presidio |
| Git / GitHub | — | Control de versiones del proyecto | Repositorio privado obligado por credenciales en el compose |

> Nota de evolución (usar versión más reciente): la documentación de contexto inicial menciona **Ollama** como LLM local. En las decisiones más recientes del proyecto se optó por **OpenRouter** (`llama-3.3-70b-instruct`), justificado porque el texto ya va anonimizado. La arquitectura actual **no usa Ollama**.

---

## 4. Descripción de componentes

#### n8n (orquestador)
**Tecnología:** n8n 2.22.6 self-hosted (`n8nio/n8n`, contenedor `tprm_n8n`).
**Función:** Ejecuta el pipeline completo: disparador programado / lectura de ficheros, extracción de PDF, decisión texto vs. escaneado, llamada a Presidio, ramificación (trazabilidad + análisis), llamada a OpenRouter, desanonimización con nodos Code, y persistencia/exportación.
**Configuración relevante (variables de entorno):** `TZ=Europe/Madrid`; backend en PostgreSQL (`DB_TYPE=postgresdb`, `DB_POSTGRESDB_HOST=postgres`, `DB_POSTGRESDB_PORT=5432`, `DB_POSTGRESDB_DATABASE=tprm_ai`, `DB_POSTGRESDB_USER=tprm`); `N8N_FILESYSTEM_ALLOWLIST=/files`; `N8N_ENABLE_FILE_WATCHER=true`; `N8N_NODES_INCLUDE=n8n-nodes-base.executeCommand` (habilita el nodo *Execute Command*, deshabilitado por defecto desde n8n 2.0). Volúmenes: `./n8n:/home/node/.n8n` y `./n8n-files:/home/node/.n8n-files`.
**Integración:** habla por HTTP con Presidio, OpenRouter y (en RAG) embedding-api y Qdrant; y por conector nativo con PostgreSQL. Depende de `postgres` y `qdrant`.
**Nota:** n8n crea sus propias tablas internas en la misma base `tprm_ai` (`agent_*`, `chat_hub_*`, `execution_*`, etc.). Conviven con las tablas del proyecto.

#### presidio-anonymizer (custom)
**Tecnología:** Imagen construida a medida (`python:3.11-slim` + FastAPI + Uvicorn) que instala en modo editable `presidio-analyzer` y `presidio-anonymizer` desde `presidio_mod/`, y descarga `es_core_news_md`. Contenedor `presidio_anonymizer`, puerto `5002:3000`.
**Función:** API REST que analiza y anonimiza texto en español. Un único servicio contiene **analyzer y anonymizer**: `POST /anonymize` recibe `{text, language}` y devuelve `{anonymized_text, mapping}`; `GET /health` devuelve estado.
**Configuración relevante:** El `server.py` inicializa `NlpEngineProvider` con spaCy español, `AnalyzerEngine(supported_languages=["es"])` y `MappingAnonymizerEngine()`. El código fuente se monta como **volumen** (`./presidio_mod/presidio-analyzer:/app/presidio-analyzer` y equivalente para anonymizer) para permitir edición en vivo sin reconstruir la imagen (basta `docker compose restart`).
**Integración:** invocado por n8n en `http://presidio_anonymizer:3000/anonymize`.
**Nota:** en el compose actual solo existe este servicio custom. El antiguo `presidio-analyzer` con imagen oficial de Microsoft (`mcr.microsoft.com/presidio-analyzer`, puerto `5001:3000`) fue retirado del compose; puede aparecer como contenedor huérfano (`presidio_analyzer`) residual de fases anteriores.

##### Presidio modificado — reconocedores y motor
El fork de Presidio incorpora, para español empresarial:

- **`EsSpanishCompanyRecognizer`** (entidad `COMPANY`): detecta empresas con sufijo legal (S.L., S.A., S.L.U., S.A.U.). Rechaza acrónimos, patrones de nº de certificado del tipo `^[A-Z]{2}[-/][A-Z0-9]` (p. ej. `ES-SI-27001-45879`) y exige mínimo de tokens en *title case*.
- **`EsSpanishOrganizationRecognizer`** (entidad `COMPANY`): detecta certificadoras/organizaciones multi-token (p. ej. "SGS ICS Iberia"). Configurado con `require_context=True` y `EntityScore(base=0.0, with_context=0.75)` para no disparar sin contexto; recorta prefijos de contexto ("Certificado por ", etc.), rechaza spans con salto de línea, >60 caracteres, primeros tokens de frase comunes, etc.
- **`EsSpanishPersonRecognizer`** (entidad `PERSON`): nombres en español. *Detección de PERSON incompleta — ver limitaciones.*
- **`EsSpanishLocationRecognizer`** (entidad `LOCATION`).
- Reconocedores de apoyo: NIF/NIE→CIF, IBAN, teléfono, email, además de los recognizers estándar de Presidio.
- **`tprm_anonymizer_utils.py`**: canalización `prepare_analyzer_results()` = `filter_corrupt_spans()` (rechaza spans con `\n`/`\r`, >80 caracteres o >6 tokens) → `filter_denylisted_entities()` (denylist de acrónimos técnicos: `iso, mfa, bcp, rpo, rto, sla, scc, tia, dpo, aws, gdpr, nif, cif, iban, saas, rgpd, soc, siem, kpi, api, erp, crm, pii, phi`) → `deduplicate_overlapping()` (resuelve solapes conservando el de mayor score).
- **`MappingAnonymizerEngine`** + operador **`PlaceholderCounter`**: sustituye cada entidad por `<TIPO_NNN>` (p. ej. `<COMPANY_001>`) y construye un mapa reversible `{ "COMPANY_001": "TechNova Solutions S.L", ... }`. El valor almacenado en el mapa se limpia de prefijos de contexto; el texto de salida reemplaza el span completo.

#### ocr-api / tesseract
**Tecnología:** `ocr-api` es un servicio FastAPI (`build ./ocr-api`, contenedor `ocr_api`, `8000:8000`) con `pytesseract` + Pillow, endpoint `POST /ocr` que recibe una imagen y devuelve `{text}`. Adicionalmente un contenedor `tesseract` (`tesseractshadow/tesseract4re`) monta `./n8n-files:/files` para OCR de PDFs.
**Función:** extraer texto de documentos escaneados o imágenes cuando el PDF no tiene capa de texto.
**Integración:** rama FALSE del nodo IF de n8n (documento escaneado).

#### OpenRouter (LLM)
**Tecnología:** servicio cloud; modelo `meta-llama/llama-3.3-70b-instruct:free`. **No forma parte de Docker.**
**Función:** analizar el documento anonimizado y devolver el JSON de evaluación TPRM (vendor, certificaciones, scoring 1-5 por control, gaps, campos_pendientes, resumen_ejecutivo).
**Configuración relevante:** `POST https://openrouter.ai/api/v1/chat/completions` con cabecera `Authorization: Bearer <API_KEY>` y `Content-Type: application/json`; cuerpo con `model` y `messages`. El prompt se separó en `system` (instrucciones, rúbrica, pesos, plantilla JSON) y `user` (documento anonimizado). El prompt maestro reside en `prompt_tprm.txt` con el marcador `[EL DOCUMENTO SE AÑADIRÁ AQUÍ]`.
**Integración:** recibe **solo** texto anonimizado; nunca ve datos personales reales. Limitación operativa: el plan gratuito impone rate limits (observado ~20 peticiones/día).

#### PostgreSQL
**Tecnología:** `postgres:16`, contenedor `tprm_postgres`, `5432:5432`. Base de datos `tprm_ai`, usuario `tprm`.
**Función:** persistir la ficha maestra de proveedores (`vendors`) y el backup anonimizado con mapa reversible (`anonymized_documents`). Backend de n8n.
**Configuración relevante:** volumen `./postgres:/var/lib/postgresql/data`; restricción `UNIQUE` en `vendors.company_name` (clave del UPSERT). Ver modelo de datos en §6.
**Integración:** con n8n (conector nativo y como backend), y con los workflows de RAG (lectura para backfill).

#### Qdrant + embedding-api (RAG — en construcción)
**Tecnología:** `qdrant/qdrant` (contenedor `tprm_qdrant`, `6333:6333`) y `text-embeddings-inference:cpu-1.6` (contenedor `tprm_embedding`, `8080:80`) con `intfloat/multilingual-e5-large`.
**Función:** almacenar vectores del texto anonimizado (colección `vendors_docs`) y de las evaluaciones (colección `vendors_assessments`) para enriquecer el prompt con contexto histórico.
**Configuración relevante:** ambas colecciones creadas con `size: 1024` y `distance: Cosine`. Chunking de 400 palabras con 50 de solape y prefijo `passage:` requerido por el modelo E5. Se fijó `HF_ENDPOINT=https://huggingface.co` y se usó la imagen `cpu-1.6` para resolver fallos de descarga del modelo.
**Integración:** invocados por workflows de n8n. **Estado:** infraestructura y colecciones creadas (implementado); ingesta y consulta RAG en el workflow principal aún **en construcción**.

---

## 5. Modelo de datos (PostgreSQL — base `tprm_ai`)

### 5.1 Tablas del proyecto

**`vendors`** — tabla maestra del proveedor y su evaluación. Es la pieza central del sistema; su `id` actúa como clave de relación.

| Columna | Tipo | Notas |
|---|---|---|
| id | integer (serial) | PK |
| company_name | text | **UNIQUE** (clave del UPSERT) |
| cif | text | |
| country | text | |
| tier | integer | |
| current_risk | text | resultado de riesgo / "Evaluación incompleta" |
| overall_score | integer | puntuación total (a menudo null, ver limitaciones) |
| certifications | text[] | |
| cert_expiry | date | insertado con `TO_DATE(..., 'DD/MM/YYYY')` |
| dpo_nombre | text | |
| dpo_email | text | |
| summary | text | resumen ejecutivo del LLM |
| created_at | timestamp | `CURRENT_TIMESTAMP` |
| updated_at | timestamp | `CURRENT_TIMESTAMP` / `NOW()` en update |
| tipo_servicio | text | añadida posteriormente |
| dpo_tipo | text | añadida posteriormente |
| localizacion_datos | text | añadida posteriormente |
| subcontratistas | jsonb | añadida posteriormente |
| certificaciones | jsonb | añadida posteriormente |
| scoring | jsonb | scoring completo por control, añadida posteriormente |
| campos_pendientes | jsonb | añadida posteriormente |

**`anonymized_documents`** — backup de trazabilidad RGPD por documento.

| Columna | Tipo | Notas |
|---|---|---|
| id | integer (serial) | PK (no debe enviarse en el INSERT; se autogenera) |
| file_name | text | nombre del PDF de origen |
| anonymized_text | text | texto con placeholders |
| entity_mapping | jsonb | mapa reversible `{placeholder: valor_real}` |
| created_at | timestamp | `CURRENT_TIMESTAMP` |
| vendor_id | integer | **FK → vendors(id)** (añadida en fase RAG); índice `idx_anonymized_vendor` |

**`documents`** *(creada, no integrada en el flujo actual)*: `id, vendor_id (FK→vendors), document_type, file_name, extracted_text, ai_summary, score, resultado, processed_at`.

**`risks`**, **`calendar_events`**, **`audit_log`** *(creadas, no integradas)*: todas con `vendor_id` FK → `vendors(id)`. Se evaluó eliminarlas pero se decidió conservarlas ("de momento no borremos nada").

### 5.2 Diagrama de relaciones

```
                         ┌───────────────────────────────┐
                         │            vendors            │
                         │  id (PK)                      │
                         │  company_name (UNIQUE)        │
                         │  tier · current_risk          │
                         │  overall_score · cert_expiry  │
                         │  dpo_nombre · dpo_email        │
                         │  scoring (jsonb)              │
                         │  certificaciones (jsonb)      │
                         │  campos_pendientes (jsonb)    │
                         │  subcontratistas (jsonb)      │
                         │  summary · created/updated_at │
                         └───────────────┬───────────────┘
                                         │ id
          ┌──────────────────────┬───────┼───────────────┬──────────────────┐
          │ FK vendor_id         │       │               │                  │
          ▼                      ▼       ▼               ▼                  ▼
 ┌───────────────────┐  ┌─────────────┐ ┌──────────┐ ┌──────────────┐ ┌───────────┐
 │anonymized_documents│  │  documents  │ │  risks   │ │calendar_events│ │ audit_log │
 │ id (PK)           │  │  (no usada) │ │(no usada)│ │  (no usada)  │ │ (no usada)│
 │ file_name         │  └─────────────┘ └──────────┘ └──────────────┘ └───────────┘
 │ anonymized_text   │
 │ entity_mapping    │        (Además: tablas internas de n8n en la misma base:
 │ vendor_id (FK) ───┘         agent_*, chat_hub_*, execution_*, … — no del proyecto)
 └───────────────────┘
```

### 5.3 Colecciones Qdrant (RAG — en construcción)

```
Qdrant (tprm_qdrant)
├── vendors_docs          size=1024  distance=Cosine
│     payload: vendor_id, document_id, file_name, chunk_index, chunk_text
└── vendors_assessments   size=1024  distance=Cosine
      payload: vendor_id, tier, score, assessment_text
```

> El **`entity_mapping` nunca se vectoriza ni se envía a Qdrant** — es dato sensible y reside únicamente en PostgreSQL. A Qdrant solo van el texto anonimizado (vectorizado) y metadatos administrativos como *payload*.

---

## 6. Flujos de datos

### 6.1 Flujo de ingesta y anonimización (implementado)

```
Paso 1: NODO1 Scheduled / NODO2 Read Files from Disk lee PDFs de /home/node/.n8n-files/input
   → Paso 2: Extract PDF intenta obtener la capa de texto
   → Paso 3: IF "¿tiene texto o es escaneado?"
        · texto      → se usa el texto extraído
        · escaneado  → OCR (ocr-api / Tesseract) → texto
   → Paso 4: Switch + Merge "PDF" (combina texto extraído + metadatos binarios del fichero)
   → Paso 5: HTTP POST a presidio_anonymizer:3000/anonymize  { text, language: "es" }
   → Resultado: { anonymized_text, mapping }
```

Internamente, Presidio ejecuta: `extract_text` → `analyzer.analyze` (spaCy es + reconocedores custom) → `prepare_analyzer_results` (filtro de spans corruptos → denylist → deduplicación) → `anonymize_with_mapping` (operador PlaceholderCounter) → texto anonimizado + mapa.

### 6.2 Flujo de trazabilidad (Rama A — implementado)

```
Presidio (anonymized_text + mapping)
   → Code JS "buscar company para vendor_id": extrae del mapping la COMPANY con sufijo legal (S.L./S.A.)
   → PostgreSQL UPSERT mínimo en vendors:
        INSERT INTO vendors (company_name) VALUES ('...')
        ON CONFLICT (company_name) DO UPDATE SET company_name = EXCLUDED.company_name
        RETURNING id;
   → PostgreSQL INSERT en anonymized_documents:
        file_name       = $('PDF').item.binary.data.fileName
        anonymized_text = $('PRESIDIO').item.json.anonymized_text
        entity_mapping  = JSON.stringify($('PRESIDIO').item.json.mapping)
        vendor_id       = id devuelto por el UPSERT
        (el campo id NO se envía: es SERIAL autogenerado)
```

Este UPSERT mínimo se ejecuta una vez por documento (procesamiento por lotes con la query usando expresiones `$json`) para asignar el `vendor_id` correcto a cada registro.

### 6.3 Flujo de análisis TPRM con IA (Rama B — implementado)

```
Presidio (anonymized_text + mapping)
   → Lee Prompt (lee /home/node/.n8n-files/maestro/prompt_tprm.txt)
   → convertir_a_json (Code JS): prompt.replace('[EL DOCUMENTO SE AÑADIRÁ AQUÍ]', anonymized_text)
        y separa messages en role:"system" (instrucciones) + role:"user" (documento)
   → HTTP Request a OpenRouter (llama-3.3-70b-instruct:free)  ← recibe SOLO texto anonimizado
   → limpiar_json (Code JS): elimina fences ```json y hace JSON.parse
   → desanonimizar (Code JS): recorre el JSON y sustituye <COMPANY_001> etc.
        usando $('PRESIDIO').item.json.mapping (mapa en memoria de n8n, no PostgreSQL)
   → PostgreSQL UPSERT completo en vendors con COALESCE (respeta valores existentes) RETURNING id
   → PostgreSQL SELECT * FROM vendors ORDER BY company_name
   → Convert to File (CSV) → Write File /home/node/.n8n-files/maestro/inventario_vendors.csv
```

Puntos clave de este flujo:

- **Anonimización efectiva:** el LLM solo ve placeholders; la reversión a datos reales ocurre después, en local.
- **UPSERT con COALESCE:** `campo = COALESCE(EXCLUDED.campo, vendors.campo)` — solo sobrescribe si el valor nuevo no es null, preservando datos buenos ya registrados.
- **Fechas:** el LLM devuelve `DD/MM/YYYY`; se convierten con `TO_DATE(..., 'DD/MM/YYYY')` para columnas `date`.
- **Salida JSON del LLM:** el modelo tiende a envolver la respuesta en markdown; el nodo `limpiar_json` la sanea antes de `JSON.parse`.

### 6.4 Flujo de recuperación aumentada / RAG (en construcción)

Diseño previsto (fases implementadas parcialmente):

```
[Fase 1 ✅] vendor_id añadido a anonymized_documents (FK + índice)
[Fase 2 ✅] embedding-api operativo (TEI + multilingual-e5-large, /embed → vector 1024)
[Fase 3 ✅] colecciones Qdrant vendors_docs y vendors_assessments creadas
[Fase 4 ⏳] workflow "RAG - Ingesta Documentos" (backfill):
      SELECT anonymized_documents → Chunking (400/50, prefijo "passage:")
      → embedding-api → Qdrant PUT vendors_docs/points
[Fase 5 ⬜] workflow "RAG - Ingesta Assessments": vendors → texto → embedding → vendors_assessments
[Fase 6 ⬜/diseño] integración en el pipeline principal:
      Presidio → embedding → Qdrant SEARCH docs (top 5) + assessments (top 3)
      → PostgreSQL SELECT vendors (estado actual del proveedor)
      → Code JS construye prompt enriquecido:
           [instrucciones] + [estado actual en BD] + [contexto RAG] + [documento a evaluar]
      → OpenRouter
```

La consulta RAG la orquesta n8n (el LLM no accede a bases de datos por sí mismo): n8n busca en Qdrant lo relevante y lo inyecta en el prompt junto con el estado actual del proveedor en `vendors` (para no repetir datos ya conocidos). *Estado: diseñado; los nodos de embedding/insert se estaban depurando (p. ej. escapar `\n` con `JSON.stringify` en el cuerpo del HTTP).* 

---

## 7. Seguridad y privacidad

**Anonimización previa a cualquier salida externa (implementado).** El principio rector es que los datos personales reales nunca salen de la máquina. Presidio anonimiza el documento **antes** de enviarlo al LLM, de modo que OpenRouter solo procesa placeholders (`<COMPANY_001>`, `<EMAIL_001>`, `<LOCATION_001>`, etc.). Esto preserva el propósito de la anonimización: si se anonimiza y luego se enviara todo el mapa a la IA externa, se anularía la protección.

**Reversión local y trazable.** La desanonimización se realiza dentro de n8n con nodos Code, usando el mapa de entidades en memoria de la ejecución. Adicionalmente, cada documento guarda su `anonymized_text` y su `entity_mapping` en `anonymized_documents` como **backup y evidencia de auditoría RGPD** (permite reconstruir el original y demostrar qué se procesó). El mapa **no** se usa en el flujo en vivo ni se envía a Qdrant.

**Aislamiento por diseño.** Toda la infraestructura corre en local sobre Docker Compose en una red interna. La **única** conexión externa del flujo de datos es la llamada HTTPS a OpenRouter, que recibe datos ya anonimizados.

**Marco de evaluación.** El análisis TPRM se alinea con **ISO 27001, ENS y RGPD**: rúbrica 1-5 por control, pesos por sección (Seguridad de la información 30%, IAM 25%, Continuidad 15%, Protección de datos 20%, Nube 5%, Subcontratistas 5%), umbrales de resultado (≥80 Aprobado; 60-79 Aprobado con condiciones; <60 Rechazado; "Evaluación incompleta" si faltan datos) y *gaps* que bloquean la aprobación (sin MFA en accesos críticos, sin DPA con acceso a datos personales, transferencia internacional sin TIA, certificación expirada, sin PAM en tier 1/2).

**Puntos de atención de seguridad conocidos (pendientes):**

- Las **credenciales están en texto plano** en `docker-compose.yml` (p. ej. `POSTGRES_PASSWORD`), por lo que el repositorio Git debe ser **privado**; se recomienda migrar a `.env`/secretos.
- La **API key de OpenRouter** viaja en la cabecera `Authorization`; conviene externalizarla a credenciales de n8n.
- El nº de certificado (`ES-SI-27001-45879`) **no se anonimiza** actualmente (se decidió no tratarlo como entidad).
- La detección de **PERSON** es incompleta (ver §9), lo que implica que algún nombre puede no anonimizarse.

---

## 8. Despliegue y operación

**Puesta en marcha (Docker Compose).**

```bash
cd ~/tprm-ai
docker compose up -d            # levanta todos los servicios
docker compose up -d --build presidio-anonymizer   # reconstruye la API de Presidio
docker compose restart presidio-anonymizer         # recarga tras editar presidio_mod (volumen montado)
docker compose down             # detiene todo (los volúmenes conservan los datos)
```

**Verificaciones de salud.**

```bash
curl http://localhost:5002/health            # Presidio → {"status":"ok"}
curl http://localhost:8080/health            # embedding-api → 200 (cuerpo vacío es normal en TEI)
curl http://localhost:6333/collections       # Qdrant → lista de colecciones
docker exec -it tprm_postgres psql -U tprm -d tprm_ai -c "\dt" -P pager=off
```

**Prueba rápida de anonimización.**

```bash
curl -X POST http://localhost:5002/anonymize \
  -H "Content-Type: application/json" \
  -d '{"text": "Empresa: TechNova Solutions S.L. - Contacto: dpo@technova.eu"}'
# → {"anonymized_text":"Empresa: <COMPANY_001>. - Contacto: <EMAIL_001>","mapping":{...}}
```

**Operación de PostgreSQL (nota importante).** Ejecutar sentencias multilínea pegándolas en `psql` interactivo provoca errores por *bracketed paste*; se recomienda `docker exec ... psql ... -c "<sentencia en una línea>"` o *here-doc* con `-i`.

**Estructura de carpetas del proyecto.**

```
tprm-ai/
├── docker-compose.yml
├── n8n/                          → datos internos de n8n
├── n8n-files/
│   ├── input/                    → PDFs entrantes
│   ├── processed/                → PDFs procesados
│   ├── vendors/                  → carpeta por proveedor (uso futuro)
│   └── maestro/
│       ├── prompt_tprm.txt       → prompt maestro TPRM
│       └── inventario_vendors.csv → inventario generado
├── ocr-api/                      → API OCR (Tesseract + FastAPI): app.py, Dockerfile
├── presidio-anonymizer-custom/   → Dockerfile + server.py (API REST)
├── presidio_mod/                 → código fuente Presidio modificado (montado como volumen)
│   ├── presidio-analyzer/…/spanish_enterprise/  → reconocedores custom ES
│   └── presidio-anonymizer/…/operators/         → MappingAnonymizerEngine / PlaceholderCounter
├── postgres/                     → volumen PostgreSQL
└── qdrant/                       → volumen Qdrant
```

**Control de versiones.** Repositorio Git en `~/tprm-ai` con `.gitignore` que excluye `postgres/`, `qdrant/`, `n8n/`, `n8n-files/`, `*.pdf`, salidas y `.env`. Los workflows de n8n **no** se versionan automáticamente (viven en PostgreSQL); se exportan a JSON manualmente para guardarlos. Se eliminó un `.git` embebido en `presidio_mod/` para evitar submódulos.

---

## 9. Limitaciones conocidas y trabajo futuro

**Limitaciones actuales (implementadas parcialmente o con defectos conocidos):**

- **Detección de PERSON incompleta:** nombres como "Laura Martín Gómez" no se anonimizan de forma fiable. Conocido y en backlog.
- **Asignación incorrecta de `vendor_id`:** Presidio a veces marca como `COMPANY_001` una persona u otra organización en lugar del proveedor principal (p. ej. "SGS ICS Iberia", "Pascual Rivas", "Javier Molina"), lo que produce `vendor_id` erróneos en algunos documentos. Depende de mejorar el reconocedor; marcado como error controlado.
- **Scoring automático no consolidado:** `score_total` y `resultado` quedan a menudo `null`; el cálculo ponderado por sección aún no se computa de forma determinista en n8n.
- **Nº de certificado sin anonimizar** (`ES-SI-27001-45879`).
- **Duplicados por nombre de fichero:** un mismo PDF procesado dos veces genera dos filas en `anonymized_documents` (falta control de idempotencia).
- **Rate limits del LLM gratuito** en OpenRouter (≈20 peticiones/día observadas).
- **Tablas `documents`, `risks`, `calendar_events`, `audit_log` creadas pero sin integrar** en el flujo.

**En diseño / en progreso:**

- **Capa RAG con Qdrant:** infraestructura y colecciones listas (Fases 1-3 ✅); ingesta/backfill (Fase 4) en depuración; assessments (Fase 5) e integración en el prompt principal con contexto histórico y estado del proveedor (Fase 6) pendientes/diseñadas.
- **Inyección del estado actual del proveedor en el prompt** (para no reevaluar datos ya conocidos), diseñada dentro de la Fase 6.

**Trabajo futuro previsto:**

- *Few-shot examples* en el prompt para mejorar la calidad de la evaluación.
- Cálculo automático y determinista del scoring y del resultado.
- Excel individual por proveedor (además del inventario CSV maestro).
- Integración de `risks` y `audit_log` (hallazgos críticos y registro de auditoría con hora de entrada y cambios).
- Endurecimiento de secretos (mover credenciales y API key fuera del compose).
- Migración futura del almacenamiento de ficheros a SharePoint/OneDrive.

---

## 10. Estado actual y próximos pasos

**El proyecto no está terminado.** A la fecha de este informe, el sistema tiene el **pipeline principal operativo de extremo a extremo** y una **capa RAG en construcción**.

**Implementado y funcionando hoy:**

- Ingesta de PDFs (con rama de OCR para escaneados) y anonimización en español con Presidio modificado y mapa reversible.
- Envío de solo texto anonimizado al LLM (OpenRouter, Llama 3.3 70B) y obtención del JSON de evaluación TPRM.
- Desanonimización post-IA en n8n y persistencia en PostgreSQL (`vendors` con UPSERT+COALESCE; `anonymized_documents` con backup y `vendor_id`).
- Generación del inventario `inventario_vendors.csv`.
- Infraestructura RAG desplegada: `embedding-api` (TEI + multilingual-e5-large) y colecciones Qdrant `vendors_docs` / `vendors_assessments`.
- Control de versiones en GitHub (repo privado).

**En progreso / diseñado, no productivo:**

- Backfill e ingesta RAG (Fases 4-5) y su integración en el workflow principal (Fase 6), incluida la inyección del estado del proveedor en el prompt.

**Defectos abiertos que condicionan la calidad:**

- Detección de PERSON y asignación de `vendor_id` a mejorar; scoring total sin consolidar; sin anonimizar nº de certificado; posibles duplicados por fichero.

**Próximos pasos recomendados (orden sugerido):**

1. Cerrar la ingesta RAG (Fases 4-6) y validar el prompt enriquecido end-to-end.
2. Corregir la detección de PERSON y la lógica de identificación del proveedor principal (`vendor_id`).
3. Implementar el cálculo determinista del scoring y `resultado`.
4. Añadir *few-shot* al prompt y, después, contexto histórico vía Qdrant.
5. Endurecer secretos (credenciales y API key fuera del compose).
6. Integrar `risks`/`audit_log` y generar el Excel individual por proveedor.

---

*Documento generado a partir de la síntesis de las tres conversaciones de diseño del proyecto (tprm1, tprm2, tprm3). Refleja el estado del sistema a 1 de julio de 2026. Los elementos marcados **[A definir]** no constan en la documentación de origen.*
