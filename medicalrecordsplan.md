# Medical Records Summarization Plan

## Goal
Implement a medical records summarization pipeline in `llm-observability-sdk/examples/genai_service/` that:
1. Retrieves FHIR patient records from GCS (`raw/`)
2. Uses a GenAI agent to summarize and cite specific sections
3. Saves structured output to GCS (`summaries/`)

This is a POC. Keep the solution simple, explicit, and aligned with the PRD. Run `just` from `llm-observability-sdk/` after any code changes.

---

## Working Directory Context
- Repo root: `/Users/treyshanks/workspace/llmOps`
- Example service: `llm-observability-sdk/examples/genai_service/`
- Mandatory checks: `just` (from `llm-observability-sdk/`)

---

## GCS Data Layout
Local Synthea output and GCS layout should mirror each other:

- Local input: `llm-observability-sdk/examples/genai_service/synthea_output/fhir/*.json`
- GCS raw: `gs://<bucket>/raw/patient-XXX.json`
- GCS summaries: `gs://<bucket>/summaries/patient-XXX.json`
- GCS index: `gs://<bucket>/index.json`

Use `gcloud storage cp` for all uploads. Always include `--project=<GCS_PROJECT_ID>` and fail if the project is not set.

---

## Index Schema (Confirmed)
Create `index.json` as a JSON array. Each entry derives from the `Patient` resource in a bundle.

```json
[
  {
    "id": "patient-003",
    "name": "John A. Doe",
    "gender": "male",
    "birth_date": "2025-01-02",
    "age": 1
  }
]
```

Extraction rules:
- `id`: filename stem (e.g., `patient-003`)
- `Patient` resource: first bundle entry where `resource.resourceType == "Patient"`
- `name`: `Patient.name[0].text` or constructed from `given + family`
- `gender`: `Patient.gender` or `"unknown"`
- `birth_date`: `Patient.birthDate` (ISO date)
- `age`: integer years from `birth_date` to today

---

## File Changes Overview
Create/modify files only under `llm-observability-sdk/examples/genai_service/`:

- Create: `config.py`
- Create: `scripts/setup_data.py`
- Modify: `agents.py`
- Modify: `main.py`
- Modify: `.env.example`
- Modify: `Justfile`
- Modify: `README.md`

---

## Step-by-Step Instructions

### 1) Add config.py
Create `llm-observability-sdk/examples/genai_service/config.py`:
- `GCSConfig` dataclass fields:
  - `project_id` (env: `GCS_PROJECT_ID`, required)
  - `bucket_name` (env: `GCS_BUCKET_NAME`, required)
  - `raw_prefix` (env: `GCS_RAW_PREFIX`, default: `raw`)
  - `summaries_prefix` (env: `GCS_SUMMARIES_PREFIX`, default: `summaries`)
  - `index_file` (env: `GCS_INDEX_FILE`, default: `index.json`)
- `get_config()` cached singleton
- Raise a clear error if required fields are missing

### 2) Add scripts/setup_data.py
Create `llm-observability-sdk/examples/genai_service/scripts/setup_data.py`:
- Inputs
  - Args: `--project`, `--bucket`, `--synthea-dir`, `--dry-run`
  - Defaults from env via `config.get_config()`
  - Validate `GCS_PROJECT_ID` and `GCS_BUCKET_NAME` are provided
- Behavior
  - Read FHIR bundles from `<synthea-dir>/fhir/*.json`
  - Build `index.json` in `examples/genai_service/` (temp file)
  - Upload using `gcloud storage cp --project=<id>`:
    - `synthea_output/fhir/*.json → gs://<bucket>/raw/`
    - `index.json → gs://<bucket>/index.json`
    - `/dev/null → gs://<bucket>/summaries/.keep`
  - Validate uploads with `gcloud storage ls --project=<id>`
  - `--dry-run` prints commands only
- Use Python `subprocess.run(..., check=True)` to execute `gcloud`

### 3) Update agents.py
Modify `llm-observability-sdk/examples/genai_service/agents.py`:
- Add GCS helper tools:
  - `list_patients()`:
    - `gcloud storage cat gs://<bucket>/<index_file>`
    - return parsed list
  - `fetch_patient_record(patient_id)`:
    - `gcloud storage cat gs://<bucket>/<raw_prefix>/<patient_id>.json`
    - return parsed JSON
  - `save_summary(patient_id, summary, citations)`:
    - write JSON to temp file
    - `gcloud storage cp <temp> gs://<bucket>/<summaries_prefix>/<patient_id>.json`
    - return confirmation with GCS path
- Add `medical_records_agent` with required instruction:
  - sections: Demographics, Active Conditions, Procedures/Surgical History, Current Medications, Recent Lab Results (flag abnormals), Imaging Findings
  - every claim must include a citation object
  - tools: list_patients, fetch_patient_record, save_summary

### 4) Update main.py
Modify `llm-observability-sdk/examples/genai_service/main.py`:
- Add models:
  - `PatientInfo`, `PatientListResponse`
  - `SummarizeRequest`
  - `Citation`
  - `SummarizeResponse` (fields: patient_id, summary, citations, output_location)
- Add endpoints:
  - `GET /patients` → returns list from `list_patients()`
  - `POST /patients/{patient_id}/summarize` → runs `medical_records_agent`, saves summary, returns response
  - `GET /patients/{patient_id}/summary` → loads summary from GCS and returns

### 5) Update .env.example
Modify `llm-observability-sdk/examples/genai_service/.env.example`:
Add GCS block:
```
GCS_PROJECT_ID=llmops-genai
GCS_BUCKET_NAME=patient-records-genai
GCS_RAW_PREFIX=raw
GCS_SUMMARIES_PREFIX=summaries
GCS_INDEX_FILE=index.json
```

### 6) Update Justfile
Modify `llm-observability-sdk/examples/genai_service/Justfile`:
- Data setup commands:
  - `setup-data`: `uv run python scripts/setup_data.py`
  - `setup-data-dry-run`: `uv run python scripts/setup_data.py --dry-run`
- Example commands:
  - `patients`: `curl -s http://localhost:8000/patients | jq`
  - `summarize patient_id="patient-003"`: `curl -s -X POST http://localhost:8000/patients/{{patient_id}}/summarize | jq`
  - `summary patient_id="patient-003"`: `curl -s http://localhost:8000/patients/{{patient_id}}/summary | jq`

### 7) Update README.md
Modify `llm-observability-sdk/examples/genai_service/README.md`:
- Add GCS + gcloud requirement for medical records pipeline
- Add setup-data instructions and sample commands
- Update “Medical Records Feature (In Progress)” to reflect new endpoints and `setup-data` script

### 8) Run Checks (Mandatory)
From `llm-observability-sdk/`:
```
just
```
All checks must pass.

---

## Notes
- Keep the implementation minimal and POC-friendly.
- Avoid new abstractions beyond what is necessary.
- Ensure agent instructions require citations for every clinical assertion.
- Use ASCII-only content unless existing files include Unicode.
