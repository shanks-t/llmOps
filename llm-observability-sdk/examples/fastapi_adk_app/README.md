# FastAPI + Google ADK Test Application

This test application validates the llmops SDK auto-instrumentation.

## Prerequisites

1. **Start backends:**
   ```bash
   cd docker && docker-compose up -d
   ```

2. **Set Google API key:**
   ```bash
   export GOOGLE_API_KEY=your-api-key
   ```

3. **Install dependencies:**
   ```bash
   pip install llmops[phoenix] fastapi uvicorn google-adk google-genai
   ```

## Run the Application

### With Phoenix backend (default):
```bash
uvicorn main:app --reload
```

### With MLflow backend:
```bash
LLMOPS_BACKEND=mlflow uvicorn main:app --reload
```

## Test

```bash
# Health check
curl http://localhost:8000/

# Ask the agent
curl "http://localhost:8000/ask?query=What%20is%20the%20weather%20in%20Paris"
curl "http://localhost:8000/ask?query=What%20time%20is%20it%20in%20Tokyo"
```

## View Traces

- **Phoenix:** http://localhost:6006
- **MLflow:** http://localhost:5001

## Expected Trace Hierarchy

```
FastAPI: GET /ask
└── Agent: travel-assistant
    ├── LLM: gemini-2.0-flash-exp (planning)
    ├── Tool: get_weather
    └── LLM: gemini-2.0-flash-exp (response)
```
