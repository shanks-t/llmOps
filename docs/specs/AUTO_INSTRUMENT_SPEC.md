# Auto-Instrumentation SDK — Prototype Specification

**Version:** 0.1 (Prototype)
**Date:** 2026-01-13
**Status:** Draft

---

## 1. Prototype Goal

**Validate the feasibility** of building an SDK that:

1. Abstracts auto-instrumentation configuration across multiple backends (Phoenix/Arize, MLflow)
2. Provides a single `configure()` call that enables the appropriate backend's auto-instrumentation
3. Works with a test application using **Google ADK**, **Gemini**, and **FastAPI**

### What This Prototype IS

- A minimal SDK that routes to existing auto-instrumentation
- A test harness to validate the approach works end-to-end
- A proof of concept for the unified configuration idea

### What This Prototype IS NOT

- A full-featured SDK (no privacy controls, no manual spans, no custom attributes)
- Production-ready code
- A replacement for existing instrumentors

---

## 2. Test Application Stack

| Component | Purpose |
|-----------|---------|
| **Google ADK** | Agent framework with tools |
| **Gemini** | LLM provider (via Google GenAI) |
| **FastAPI** | Web framework for API endpoints |

The test app will be a simple FastAPI service that exposes an endpoint which runs a Google ADK agent.

---

## 3. Backends to Support

### 3.1 Phoenix (Arize)

Uses OpenInference instrumentors.

**Instrumentors needed:**
- `openinference-instrumentation-google-adk` — Google ADK agent tracing
- `openinference-instrumentation-google-genai` — Gemini/Google GenAI tracing
- `openinference-instrumentation-fastapi` — FastAPI request tracing

**Setup pattern:**
```python
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
from openinference.instrumentation.fastapi import FastAPIInstrumentor

tracer_provider = register(endpoint="http://localhost:6006/v1/traces")
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
FastAPIInstrumentor().instrument(tracer_provider=tracer_provider)
```

**Reference:**
- https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-adk
- https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-genai
- https://pypi.org/project/openinference-instrumentation-fastapi/

### 3.2 MLflow

Uses MLflow's built-in autolog.

**Autologs needed:**
- `mlflow.gemini.autolog()` — Gemini tracing
- (Google ADK may work via Gemini autolog, needs validation)
- FastAPI: MLflow may need OpenTelemetry integration

**Setup pattern:**
```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5001")
mlflow.set_experiment("my-agent")
mlflow.gemini.autolog()
```

**Reference:**
- https://mlflow.org/docs/latest/genai/tracing/index.html
- https://mlflow.org/docs/latest/genai/tracing/integrations/index.html

---

## 4. SDK Public API (Minimal)

```python
import llmops

# Configure backend and enable auto-instrumentation
llmops.configure(
    backend="phoenix",  # or "mlflow"
    endpoint="http://localhost:6006/v1/traces",
    service_name="my-agent-service",
)

# Shutdown (flush spans)
llmops.shutdown()
```

That's the entire API for the prototype.

---

## 5. Package Structure (Simplified)

```
llm-observability-sdk/
├── src/
│   └── llmops/
│       ├── __init__.py          # Exports: configure, shutdown
│       ├── configure.py         # Main configure() function
│       └── backends/
│           ├── __init__.py
│           ├── phoenix.py       # Phoenix/OpenInference setup
│           └── mlflow.py        # MLflow autolog setup
├── tests/
│   └── test_configure.py
├── examples/
│   └── fastapi_adk_app/         # Test application
│       ├── main.py              # FastAPI app with ADK agent
│       └── README.md
└── pyproject.toml
```

---

## 6. Implementation Details

### 6.1 `configure()` Function

```python
def configure(
    *,
    backend: Literal["phoenix", "mlflow"],
    endpoint: str,
    service_name: str = "llmops-app",
) -> None:
    """
    Configure and enable auto-instrumentation.

    Args:
        backend: "phoenix" or "mlflow"
        endpoint: Backend endpoint URL
        service_name: Service name for traces
    """
```

### 6.2 Phoenix Backend

```python
# src/llmops/backends/phoenix.py

def setup(endpoint: str, service_name: str) -> None:
    """Enable Phoenix/OpenInference auto-instrumentation."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource

    # Setup TracerProvider
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Enable instrumentors (fail silently if not installed)
    _try_instrument("openinference.instrumentation.google_adk", "GoogleADKInstrumentor", provider)
    _try_instrument("openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor", provider)
    _try_instrument("openinference.instrumentation.fastapi", "FastAPIInstrumentor", provider)


def _try_instrument(module_path: str, class_name: str, provider) -> None:
    """Try to enable an instrumentor, skip if not installed."""
    try:
        module = __import__(module_path, fromlist=[class_name])
        instrumentor = getattr(module, class_name)()
        instrumentor.instrument(tracer_provider=provider)
    except ImportError:
        pass  # Instrumentor not installed
```

### 6.3 MLflow Backend

```python
# src/llmops/backends/mlflow.py

def setup(endpoint: str, service_name: str) -> None:
    """Enable MLflow auto-instrumentation."""
    import mlflow

    mlflow.set_tracking_uri(endpoint)
    mlflow.set_experiment(service_name)

    # Enable autologs (fail silently if not available)
    _try_autolog("gemini")


def _try_autolog(name: str) -> None:
    """Try to enable an MLflow autolog, skip if not available."""
    import mlflow
    try:
        module = getattr(mlflow, name, None)
        if module and hasattr(module, "autolog"):
            module.autolog()
    except Exception:
        pass
```

---

## 7. Test Application

### 7.1 FastAPI + Google ADK Agent

```python
# examples/fastapi_adk_app/main.py

import llmops
from fastapi import FastAPI
from google.adk import Agent
from google.adk.tools import FunctionTool

# Configure observability BEFORE creating app
llmops.configure(
    backend="phoenix",  # Change to "mlflow" to test that backend
    endpoint="http://localhost:6006/v1/traces",
    service_name="fastapi-adk-demo",
)

app = FastAPI()


def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 22°C"


agent = Agent(
    model="gemini-2.0-flash-exp",
    tools=[FunctionTool(get_weather)],
)


@app.get("/ask")
async def ask(query: str):
    """Ask the agent a question."""
    response = await agent.run(query)
    return {"response": response.text}


@app.on_event("shutdown")
def shutdown():
    llmops.shutdown()
```

### 7.2 Running the Test

```bash
# Terminal 1: Start backends
cd docker && docker-compose up -d

# Terminal 2: Run the app
cd examples/fastapi_adk_app
uvicorn main:app --reload

# Terminal 3: Test
curl "http://localhost:8000/ask?query=What%20is%20the%20weather%20in%20Paris"

# Check traces
open http://localhost:6006  # Phoenix
open http://localhost:5001  # MLflow
```

---

## 8. Dependencies

```toml
[project]
dependencies = [
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-exporter-otlp-proto-http>=1.20.0",
]

[project.optional-dependencies]
phoenix = [
    "openinference-instrumentation-google-adk>=0.1.0",
    "openinference-instrumentation-google-genai>=0.1.0",
    "openinference-instrumentation-fastapi>=0.1.0",
]
mlflow = [
    "mlflow>=2.10.0",
]
test = [
    "fastapi>=0.100.0",
    "uvicorn>=0.20.0",
    "google-adk>=0.1.0",
    "google-genai>=1.0.0",
    "pytest>=8.0",
]
```

---

## 9. Success Criteria

| Criterion | Phoenix | MLflow |
|-----------|---------|--------|
| `configure()` succeeds without error | ☐ | ☐ |
| FastAPI requests appear as traces | ☐ | ☐ |
| Google ADK agent runs appear as traces | ☐ | ☐ |
| LLM calls show model name | ☐ | ☐ |
| Tool calls appear as child spans | ☐ | ☐ |
| Span hierarchy is correct (request → agent → llm/tool) | ☐ | ☐ |

---

## 10. Open Questions to Validate

| # | Question | How to Validate |
|---|----------|-----------------|
| 1 | Does Phoenix GoogleADKInstrumentor capture agent + tool spans? | Run test app, check Phoenix UI |
| 2 | Does MLflow gemini.autolog() work with Google ADK? | Run test app with MLflow backend |
| 3 | Can we switch backends by just changing `configure()` args? | Test both backends with same app |
| 4 | What's the overhead of the instrumentors? | Measure request latency |

---

## 11. Reference Links

### Phoenix / OpenInference
- OpenInference repo: https://github.com/Arize-ai/openinference
- Google ADK instrumentor: https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-adk
- Google GenAI instrumentor: https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-genai
- FastAPI instrumentor: https://pypi.org/project/openinference-instrumentation-fastapi/

### MLflow
- Tracing overview: https://mlflow.org/docs/latest/genai/tracing/index.html
- Automatic tracing: https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/automatic/
- Gemini integration: https://mlflow.org/docs/latest/genai/tracing/integrations/index.html

### Google
- Google ADK: https://github.com/google/adk-python
- Google GenAI SDK: https://github.com/googleapis/python-genai

---

## 12. Out of Scope for Prototype

- Privacy controls / content filtering
- Manual span creation
- Custom attributes / metadata
- Session / user context tracking
- YAML configuration files
- Multi-backend routing (send to both simultaneously)
- Error handling beyond basic try/except

---

**Document Owner:** Platform Team
**Last Updated:** 2026-01-13
