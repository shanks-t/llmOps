# LLMOps Demo

Minimal FastAPI example demonstrating the `llmops.instrument()` API for auto-instrumentation of Google ADK.

## Overview

This example shows how to use the llmops SDK with a simple YAML configuration file to automatically instrument Google ADK agents and send traces to Phoenix.

Key features:
- Single `llmops.instrument()` call in FastAPI lifespan
- Configuration via `llmops.yaml`
- Auto-instrumentation of Google ADK
- Traces sent to Phoenix (local Docker backend)

## Prerequisites

1. **Google API Key**: Set your Gemini API key
2. **Phoenix**: Running via Docker

## Setup

### 1. Start Phoenix

From the `llm-observability-sdk/docker/` directory:

```bash
docker-compose up -d phoenix
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

### 3. Install Dependencies

```bash
just install
# or: uv sync
```

### 4. Run the Server

```bash
just run
# or: uv run uvicorn main:app --reload
```

## Usage

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/chat` | POST | Chat with assistant |

### Example Request

```bash
curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "What is the weather in Paris?"}'
```

### Example Response

```json
{
    "message": "What is the weather in Paris?",
    "response": "The weather in Paris is currently Partly Cloudy with a temperature of 18°C and 65% humidity."
}
```

## View Traces

Open Phoenix UI at: http://localhost:6006

You should see traces for:
- LLM calls (Gemini)
- Tool invocations (get_weather, get_time)

## Configuration

The `llmops.yaml` file configures the SDK:

```yaml
service:
  name: "llmops-demo"
  version: "0.1.0"

arize:
  endpoint: "http://localhost:6006/v1/traces"
  project_name: "llmops-demo"

instrumentation:
  google_adk: true
  google_genai: true
```

See [API_SPEC_01.md](../../../docs/api_spec/API_SPEC_01.md) for full configuration options.

## Project Structure

```
llmops_demo/
├── main.py          # FastAPI app with llmops.instrument() in lifespan
├── agents.py        # Google ADK agent with tools
├── llmops.yaml      # SDK configuration
├── pyproject.toml   # Dependencies
├── Justfile         # Task runner
└── README.md        # This file
```
