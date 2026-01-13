# LLM Observability SDK (Prototype)

Unified auto-instrumentation SDK for LLM observability.

## Overview

This SDK provides a single `configure()` call that enables auto-instrumentation for your chosen backend (Phoenix or MLflow).

```python
import llmops

llmops.configure(
    backend="phoenix",
    endpoint="http://localhost:6006/v1/traces",
    service_name="my-agent",
)

# Your code runs with auto-instrumentation enabled - no changes needed!
```

## Installation

```bash
# With Phoenix/OpenInference instrumentors
pip install llmops[phoenix]

# With MLflow
pip install llmops[mlflow]
```

## Quick Start

1. **Start a backend:**
   ```bash
   cd docker && docker-compose up -d
   ```

2. **Configure the SDK:**
   ```python
   import llmops

   llmops.configure(
       backend="phoenix",
       endpoint="http://localhost:6006/v1/traces",
       service_name="my-agent",
   )
   ```

3. **Run your app** - traces are captured automatically!

4. **View traces:**
   - Phoenix: http://localhost:6006
   - MLflow: http://localhost:5001

## Supported Frameworks

| Framework | Phoenix | MLflow |
|-----------|---------|--------|
| Google ADK | ✅ | TBD |
| Google GenAI | ✅ | ✅ |
| FastAPI | ✅ | TBD |

## Test Application

See `examples/fastapi_adk_app/` for a complete test application.

## API

```python
# Configure backend
llmops.configure(
    backend="phoenix",  # or "mlflow"
    endpoint="http://localhost:6006/v1/traces",
    service_name="my-service",
)

# Shutdown (flush spans)
llmops.shutdown()
```

That's the entire API!
