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
├── observability.py  # OpenTelemetry setup with dual exporters
├── pyproject.toml    # Dependencies (uv-managed)
├── Justfile          # Task runner commands
├── .env.example      # Environment variable template
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
| **Arize** (OpenInference) | GenAI spans only | LLM-specific monitoring |

GenAI spans are identified by the `openinference.span.kind` attribute and filtered using a custom `OpenInferenceOnlySpanProcessor`.

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
| `/health` | GET | Health check |

## Medical Records Feature (In Progress)

A patient record summarization pipeline using synthetic FHIR data.

### Data Flow

```
gs://patient-records-genai/
├── raw/                    ──▶  GenAI Agent  ──▶  summaries/
│   └── patient-XXX.json         (retrieve,        └── patient-XXX.json
│       (FHIR bundles)            summarize,           (summary + citations)
│                                 cite)
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

### Next Steps

1. **Add GCS tools** to `agents.py` (`fetch_patient_record`, `save_summary`)
2. **Create `medical_records_agent`** with summarization + citation instructions
3. **Add endpoints** (`POST /patients/{id}/summarize`, `GET /patients/{id}/summary`)
4. **Test pipeline** end-to-end with patient-003 (smallest record)

## Configuration

Set via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | - | Google API key (required) |
| `SERVICE_NAME` | `genai-service` | Service name in traces |
| `OTEL_ENABLED` | `true` | Enable Jaeger export |
| `OTEL_ENDPOINT` | `http://localhost:4318/v1/traces` | OTLP endpoint |
| `ARIZE_ENABLED` | `true` | Enable Arize export |
| `ARIZE_API_KEY` | - | Arize API key |
| `ARIZE_SPACE_ID` | - | Arize space ID |
| `ARIZE_PROJECT_NAME` | `genai-service` | Arize project name |
| `OTEL_CONSOLE_DEBUG` | `false` | Print spans to console |

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
```

## View Traces

- **Jaeger UI**: http://localhost:16686
- **Arize**: https://app.arize.com (when configured)
