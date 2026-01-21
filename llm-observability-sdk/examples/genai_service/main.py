"""
GenAI Service - FastAPI with Google ADK and OpenTelemetry Instrumentation

Dual-backend observability:
- Infrastructure traces → Jaeger (OTLP)
- GenAI traces → Arize (OpenInference)

Run:
    cd examples/genai_service
    uv run uvicorn main:app --reload

View traces:
    Jaeger: http://localhost:16686
    Arize: https://app.arize.com
"""

from __future__ import annotations

import json
import logging
import os
import re
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)

from agents import (  # noqa: E402
    chat_agent,
    code_agent,
    list_patients,
    medical_records_agent,
    research_agent,
    run_agent,
    save_summary,
    stream_agent_response,
    travel_agent,
)
from observability import setup_opentelemetry, shutdown_opentelemetry  # noqa: E402

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: str
    response: str


class TravelRequest(BaseModel):
    query: str
    user_id: str = "default_user"


class TravelResponse(BaseModel):
    query: str
    response: str
    tools_used: list[str]


class CodeRequest(BaseModel):
    task: str  # "generate", "explain", or "review"
    prompt: str
    language: str = "python"


class CodeResponse(BaseModel):
    task: str
    prompt: str
    response: str


class ResearchRequest(BaseModel):
    topic: str
    depth: str = "standard"  # "quick", "standard", or "deep"


class ResearchResponse(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    key_findings: list[str]


# Patient models for medical records pipeline
class PatientInfo(BaseModel):
    id: str
    name: str
    gender: str
    birth_date: str
    age: int


class PatientListResponse(BaseModel):
    patients: list[PatientInfo]


class SummarizeRequest(BaseModel):
    user_id: str = "default_user"


class Citation(BaseModel):
    section: str
    resource_type: str
    resource_id: str
    excerpt: str


class SummarizeResponse(BaseModel):
    patient_id: str
    summary: str
    citations: list[Citation]
    output_location: str


# =============================================================================
# HELPERS
# =============================================================================


def parse_agent_summary_response(response: str) -> tuple[str, list[dict]]:
    """Extract summary and citations from agent's JSON response.

    The agent should return a JSON object with 'summary' and 'citations' fields.
    This function handles both raw JSON and JSON wrapped in markdown code blocks.

    Args:
        response: The raw response text from the agent.

    Returns:
        Tuple of (summary_text, citations_list).
        Falls back to (response, []) if parsing fails.
    """
    text = response.strip()

    # Try to extract JSON from markdown code block if present
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if json_match:
        text = json_match.group(1).strip()

    try:
        data = json.loads(text)
        summary = data.get("summary", "")
        citations = data.get("citations", [])

        if not summary:
            # JSON parsed but no summary field - use raw response
            logger.warning("Parsed JSON but 'summary' field is empty or missing")
            return response, []

        return summary, citations
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse agent response as JSON: {e}")
        return response, []


# =============================================================================
# APP & LIFESPAN
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize OpenTelemetry on startup, flush traces on shutdown."""
    tracer_provider = setup_opentelemetry()
    yield
    shutdown_opentelemetry(tracer_provider)


app = FastAPI(
    title="GenAI Service",
    description="LLM workflow patterns with dual-backend observability",
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# ROUTES
# =============================================================================


@app.get("/")
async def root():
    """Service information."""
    return {
        "service": "GenAI Service",
        "version": "1.0.0",
        "observability": {
            "otel_enabled": os.getenv("OTEL_ENABLED", "true").lower() == "true",
            "otel_endpoint": os.getenv("OTEL_ENDPOINT", "http://localhost:4318/v1/traces"),
            "arize_enabled": os.getenv("ARIZE_ENABLED", "true").lower() == "true",
        },
        "endpoints": {
            "POST /chat": "Simple conversation",
            "POST /travel": "Multi-tool travel agent",
            "POST /code": "Code generation/explanation/review",
            "POST /research": "RAG workflow",
            "GET /stream": "SSE streaming",
            "GET /patients": "List available patients",
            "POST /patients/{patient_id}/summarize": "Summarize patient record",
            "GET /patients/{patient_id}/summary": "Get patient summary",
        },
    }


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "google_api_key": "configured" if os.getenv("GOOGLE_API_KEY") else "missing",
        "arize_configured": bool(os.getenv("ARIZE_API_KEY") and os.getenv("ARIZE_SPACE_ID")),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Simple single-turn LLM conversation."""
    response, _ = await run_agent(chat_agent, request.message)
    return ChatResponse(message=request.message, response=response)


@app.post("/travel", response_model=TravelResponse)
async def travel(request: TravelRequest):
    """Multi-tool travel planning agent."""
    response, tools_used = await run_agent(
        travel_agent,
        request.query,
        user_id=request.user_id,
    )
    return TravelResponse(
        query=request.query,
        response=response,
        tools_used=list(set(tools_used)),
    )


@app.post("/code", response_model=CodeResponse)
async def code(request: CodeRequest):
    """Code generation, explanation, and review."""
    task_prompts = {
        "generate": f"Generate {request.language} code for: {request.prompt}",
        "explain": f"Explain this {request.language} code: {request.prompt}",
        "review": f"Review this {request.language} code for bugs and improvements: {request.prompt}",
    }
    prompt = task_prompts.get(request.task, request.prompt)
    response, _ = await run_agent(code_agent, prompt)
    return CodeResponse(task=request.task, prompt=request.prompt, response=response)


@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    """Sequential multi-step research workflow (RAG pattern)."""
    depth_instructions = {
        "quick": "Provide a brief overview with 2-3 key points.",
        "standard": "Provide a comprehensive summary with key findings and sources.",
        "deep": "Provide an exhaustive analysis covering all aspects, nuances, and implications.",
    }

    prompt = f"""Research the following topic: {request.topic}

    Depth level: {request.depth}
    Instructions: {depth_instructions.get(request.depth, depth_instructions["standard"])}

    Use the search_knowledge_base tool to find information, then analyze and synthesize your findings.
    Structure your response with: Summary, Key Findings (as bullet points), and Sources."""

    response, tools_used = await run_agent(research_agent, prompt)

    sources = ["search_knowledge_base"] if "search_knowledge_base" in tools_used else []
    key_findings = [line.strip() for line in response.split("\n") if line.strip().startswith("-")][
        :5
    ]

    return ResearchResponse(
        topic=request.topic,
        summary=response,
        sources=sources,
        key_findings=key_findings if key_findings else ["See summary for details"],
    )


@app.get("/stream")
async def stream(prompt: str = Query(..., description="The prompt for streaming response")):
    """Streaming response via Server-Sent Events."""
    return StreamingResponse(
        stream_agent_response(chat_agent, prompt),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# =============================================================================
# PATIENT ROUTES (Medical Records Pipeline)
# =============================================================================


@app.get("/patients", response_model=PatientListResponse)
async def get_patients():
    """List all available patients from GCS index."""
    try:
        patients_data = list_patients()
        patients = [PatientInfo(**p) for p in patients_data]
        return PatientListResponse(patients=patients)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list patients: {e}") from e


@app.post("/patients/{patient_id}/summarize", response_model=SummarizeResponse)
async def summarize_patient(patient_id: str, request: SummarizeRequest):
    """Summarize a patient's medical record using the medical records agent."""
    prompt = f"""Summarize the medical record for patient {patient_id}.

    Follow these steps:
    1. Fetch the patient record using fetch_patient_record("{patient_id}")
    2. Create a comprehensive clinical summary with all required sections
    3. Include citations for every clinical assertion
    4. Save the summary using save_summary()

    Return the summary and citations as JSON."""

    response, tools_used = await run_agent(
        medical_records_agent,
        prompt,
        user_id=request.user_id,
    )

    # Parse structured data from agent response
    summary, citations_data = parse_agent_summary_response(response)

    # Convert citation dicts to Citation models (with validation)
    citations = []
    for c in citations_data:
        try:
            citations.append(Citation(**c))
        except Exception:
            # Skip malformed citations
            logger.warning(f"Skipping malformed citation: {c}")

    # Ensure summary is saved to GCS
    output_location = f"gs://patient-records-genai/summaries/{patient_id}.json"
    if "save_summary" not in tools_used:
        try:
            result = save_summary(patient_id, summary, citations_data)
            output_location = result.get("location", output_location)
        except Exception as e:
            logger.warning(f"Failed to save summary to GCS: {e}")

    return SummarizeResponse(
        patient_id=patient_id,
        summary=summary,
        citations=citations,
        output_location=output_location,
    )


@app.get("/patients/{patient_id}/summary")
async def get_patient_summary(patient_id: str):
    """Get a previously generated patient summary from GCS."""
    import json
    import subprocess

    from config import get_config

    try:
        config = get_config()
        uri = f"{config.summaries_uri}/{patient_id}.json"
        cmd = ["gcloud", "storage", "cat", uri, f"--project={config.project_id}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        summary_data = json.loads(result.stdout)
        return summary_data
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=404, detail=f"Summary not found for patient {patient_id}"
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary: {e}") from e
