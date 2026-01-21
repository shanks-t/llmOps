# GenAI Service

A FastAPI service demonstrating Google ADK agents with dual-backend OpenTelemetry observability and local tooling.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FastAPI App                               │
│                            (main.py)                                │
├─────────────────────────────────────────────────────────────────────┤
│  /chat    /travel    /code    /research    /stream                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │        Agents           │
              │      (agents.py)        │
              │  ┌──────┐ ┌──────────┐  │
              │  │ chat │ │  travel  │  │
              │  └──────┘ └──────────┘  │
              │  ┌──────┐ ┌──────────┐  │
              │  │ code │ │ research │  │
              │  └──────┘ └──────────┘  │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │    Google ADK + Gemini   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   OpenTelemetry Tracing  │
              │    (observability.py)    │
              └─────┬─────────────┬─────┘
                    │             │
         ┌──────────▼───┐   ┌────▼──────────┐
         │    Jaeger    │   │     Arize     │
         │ (all spans)  │   │ (GenAI only)  │
         └──────────────┘   └───────────────┘
```

## Project Structure

```
genai_service/
├── main.py           # FastAPI app, lifespan, routes
├── agents.py         # Agent definitions, tools, runner utilities
├── config.py         # GCS configuration for medical records
├── observability.py  # OpenTelemetry setup with dual exporters
├── pyproject.toml    # Dependencies (uv-managed)
├── Justfile          # Task runner commands
├── .env.example      # Environment variable template
├── scripts/
│   └── setup_data.py # Upload Synthea data to GCS
└── synthea_output/   # Generated FHIR patient data (local)
```

### Generate Synthea Output

The `synthea_output/` directory is ignored in git. To generate it locally, download the Synthea jar and run it from this folder:

```bash
java -jar synthea-with-dependencies.jar -p 3 -o synthea_output
```

**GCS Bucket**: `gs://patient-records-genai/` (project: `llmops-genai`)

## Observability

The service uses a **dual-backend** tracing architecture:

| Backend | Receives | Purpose |
|---------|----------|---------|
| **Jaeger** (OTLP) | All spans | Infrastructure observability |
| **Phoenix** (open source) or **Arize AX** (enterprise) | GenAI spans only | LLM-specific monitoring |

GenAI spans are identified by the `openinference.span.kind` attribute and filtered using a custom `OpenInferenceOnlySpanProcessor`.

### GenAI Trace Backend Modes

Configure via `ARIZE_MODE`:

- **`phoenix`** - Open source Phoenix (no auth required)
  ```bash
  ARIZE_MODE=phoenix
  ARIZE_ENDPOINT=http://localhost:6006/v1/traces
  ```

- **`ax`** - Arize AX enterprise (requires auth)
  ```bash
  ARIZE_MODE=ax
  ARIZE_ENDPOINT=https://your-ax-cluster.example.com/v1
  ARIZE_API_KEY=your-api-key
  ARIZE_SPACE_ID=your-space-id
  ```

- **`disabled`** - No GenAI trace export (default)

### Trace Structure

```
invocation [genai_service]     (CHAIN)
└── agent_run [agent_name]     (AGENT)
    └── call_llm               (LLM)
        ├── llm.model_name
        ├── llm.input_messages
        ├── llm.output_messages
        └── llm.token_count.*
```

## Quick Start

```bash
# Install dependencies
just install

# Start Jaeger
just start-jaeger

# Run the service
just run

# Test an endpoint
just chat "What is 2+2?"
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Simple single-turn conversation |
| `/travel` | POST | Multi-tool travel planning agent |
| `/code` | POST | Code generation/explanation/review |
| `/research` | POST | RAG workflow with search + analyze |
| `/stream` | GET | Server-Sent Events streaming |
| `/patients` | GET | List available patients |
| `/patients/{id}/summarize` | POST | Summarize patient record |
| `/patients/{id}/summary` | GET | Get patient summary |
| `/health` | GET | Health check |

## Medical Records Pipeline

A patient record summarization pipeline using synthetic FHIR data stored in GCS.

### Prerequisites

- `gcloud` CLI installed and authenticated
- GCS bucket created (default: `patient-records-genai`)
- Synthea FHIR data generated locally

### Data Flow

```
gs://patient-records-genai/
├── index.json              # Patient index (id, name, age, gender)
├── raw/                    ──▶  GenAI Agent  ──▶  summaries/
│   └── patient-XXX.json         (retrieve,        └── patient-XXX.json
│       (FHIR bundles)            summarize,           (summary + citations)
│                                 cite)
```

### Setup Data

Upload local Synthea data to GCS:

```bash
# Preview what will be uploaded
just setup-data-dry-run

# Upload to GCS
just setup-data
```

This will:
1. Read FHIR bundles from `synthea_output/fhir/`
2. Create `index.json` with patient metadata
3. Upload to `gs://<bucket>/raw/` and `gs://<bucket>/index.json`

### Usage

```bash
# List patients
just patients

# Summarize a patient record
just summarize patient_id="patient-001"

# Get existing summary
just summary patient_id="patient-001"
```

### Available Patient Data

| Patient | Description | Complexity |
|---------|-------------|------------|
| `patient-001` | 20 y/o female | 1,796 resources, 165K lines |
| `patient-002` | 13 y/o male | 76K lines |
| `patient-003` | 1 y/o male | 12K lines |

Each FHIR bundle contains: Observations, Procedures, Conditions, DiagnosticReports, Encounters, MedicationRequests, Immunizations, and more.

### GCS Bucket

```bash
# List patients
gcloud storage cat gs://patient-records-genai/index.json

# View a record
gcloud storage cat gs://patient-records-genai/raw/patient-001.json | head -100
```

## Configuration

Set via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | - | Google API key (required) |
| `SERVICE_NAME` | `genai-service` | Service name in traces |
| `OTEL_ENABLED` | `true` | Enable Jaeger export (all spans) |
| `OTEL_ENDPOINT` | `http://localhost:4318/v1/traces` | OTLP endpoint for Jaeger |
| `OTEL_CONSOLE_DEBUG` | `false` | Print spans to console |
| `ARIZE_MODE` | `disabled` | GenAI trace backend: `phoenix`, `ax`, or `disabled` |
| `ARIZE_ENDPOINT` | - | Endpoint URL (required for `phoenix` and `ax`) |
| `ARIZE_API_KEY` | - | API key (required for `ax` mode only) |
| `ARIZE_SPACE_ID` | - | Space ID (required for `ax` mode only) |
| `GCS_PROJECT_ID` | - | GCP project ID (required for medical records) |
| `GCS_BUCKET_NAME` | - | GCS bucket name (required for medical records) |
| `GCS_RAW_PREFIX` | `raw` | Prefix for raw patient records |
| `GCS_SUMMARIES_PREFIX` | `summaries` | Prefix for patient summaries |
| `GCS_INDEX_FILE` | `index.json` | Patient index filename |

## Justfile Commands

```bash
just --list          # Show all commands

# Quality
just check           # Run lint + typecheck
just lint            # Run ruff linter
just format          # Format code

# Infrastructure
just start-jaeger    # Start Jaeger container
just stop-jaeger     # Stop Jaeger
just status          # Show container status

# Server
just run             # Start the service
just run-debug       # Start with console span output
just run-jaeger-only # Start without Arize

# Examples
just chat "message"
just travel "query"
just code task="generate" prompt="fibonacci"
just research "topic"
just health

# Medical Records
just setup-data          # Upload Synthea data to GCS
just setup-data-dry-run  # Preview upload commands
just patients            # List patients
just summarize patient_id="patient-001"
just summary patient_id="patient-001"
```

## View Traces

- **Jaeger UI**: http://localhost:16686
- **Arize**: https://app.arize.com (when configured)
