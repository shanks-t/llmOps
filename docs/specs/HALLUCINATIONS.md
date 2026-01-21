# Detecting and Preventing Agent Hallucinations

Working document for implementing hallucination detection and prevention in our GenAI service using Arize Phoenix.

## 1. Problem Statement

We observed two distinct failure modes in our medical records summarization agent:

### Failure Mode 1: Skipped Tool Calls
The agent skips required tool calls entirely and fabricates data from its training knowledge.

**Example**: When summarizing patient-002, the agent returned data for "Sadie Schmidt, 73 y/o female" instead of the actual patient "Hung902 Metz686, 1 y/o male". The agent never called `fetch_patient_record()` and invented a completely fictional patient.

**Symptoms**:
- No TOOL spans in the trace
- Response contains plausible-looking but fabricated data
- Citations array is empty or contains fake resource IDs

### Failure Mode 2: Unfaithful Output
The agent calls tools correctly but hallucinates in the final output—adding information not present in the retrieved context.

**Symptoms**:
- TOOL spans present with valid data
- Response contains information not grounded in tool output
- Mix of real and fabricated claims

## 2. Detection with Phoenix/Arize

### 2.1 Detecting Skipped Tool Calls

**Key Insight**: OpenInference span data already captures everything needed—no custom span attributes required.

#### What's Already Captured

| Span Attribute | Description |
|----------------|-------------|
| `llm.tools` | Tools available to the agent |
| `openinference.span.kind` | Span type: AGENT, TOOL, LLM, etc. |
| `tool.name` | Name of tool called |
| `tool.parameters` | Parameters passed to tool |
| Child TOOL spans | Actual tool executions |

#### Detection Approach

1. **Query traces** for AGENT spans
2. **Check for child TOOL spans** matching expected tools
3. **Use evaluator** to judge if tool should have been called

```python
from phoenix.evals import (
    TOOL_CALLING_PROMPT_TEMPLATE,
    TOOL_CALLING_PROMPT_RAILS_MAP,
    llm_classify,
)

# Export spans from Phoenix
client = Client()
df = client.spans.get_spans_dataframe(project_identifier="genai-service")

# Filter to agent spans and check tool usage
agent_spans = df[df["openinference.span.kind"] == "AGENT"]

# Run tool calling evaluator
results = llm_classify(
    dataframe=agent_spans,
    template=TOOL_CALLING_PROMPT_TEMPLATE,
    model=model,
    rails=list(TOOL_CALLING_PROMPT_RAILS_MAP.values()),
    provide_explanation=True
)
```

#### Custom Evaluator: "Should Have Called Tool"

For our specific use case, we can create a targeted evaluator:

```python
TOOL_COMPLIANCE_TEMPLATE = """
You are evaluating whether an agent correctly used available tools.

[Query]: {input}
[Available Tools]: {tools}
[Tools Actually Called]: {tools_called}
[Agent Response]: {output}

The query asks about patient medical records. The agent MUST call 
fetch_patient_record() before generating any patient-specific information.

Respond with:
- "compliant" if the required tool was called before generating the response
- "non_compliant" if the agent generated patient data without calling the tool
- "not_applicable" if the query doesn't require patient data

Explain your reasoning.
"""
```

### 2.2 Detecting Hallucinations (Faithfulness)

**Key Insight**: When tools ARE called, the tool output is the context. It's already captured in the TOOL span—no additional logging needed.

#### FaithfulnessEvaluator

Phoenix provides a pre-built `FaithfulnessEvaluator` for this purpose:

```python
from phoenix.evals import FaithfulnessEvaluator
from phoenix.evals.llm import LLM

faithfulness = FaithfulnessEvaluator(
    llm=LLM(provider="openai", model="gpt-4o")
)

# For each trace, join agent output with tool output (context)
score = faithfulness.evaluate({
    "input": "Summarize patient-002's medical record",
    "output": agent_response,
    "context": tool_output_from_fetch_patient_record
})
# Returns: Score(label="faithful" | "unfaithful", ...)
```

#### Benchmark Performance

| Model | Precision | Recall | F1 |
|-------|-----------|--------|-----|
| GPT-4 | 93% | 72% | 82% |

Tested on HaluEval QA and RAG datasets.

#### Joining Spans for Evaluation

To run faithfulness evaluation, join AGENT spans with their child TOOL spans:

```python
def prepare_faithfulness_data(traces_df):
    """Join agent responses with tool outputs for faithfulness eval."""
    results = []
    
    for trace_id in traces_df["trace_id"].unique():
        trace_spans = traces_df[traces_df["trace_id"] == trace_id]
        
        agent_span = trace_spans[
            trace_spans["openinference.span.kind"] == "AGENT"
        ].iloc[0]
        
        tool_spans = trace_spans[
            trace_spans["openinference.span.kind"] == "TOOL"
        ]
        
        # Get tool output as context
        context = ""
        for _, tool in tool_spans.iterrows():
            if tool["tool.name"] == "fetch_patient_record":
                context = tool["output.value"]  # The FHIR bundle
        
        results.append({
            "input": agent_span["input.value"],
            "output": agent_span["output.value"],
            "context": context,
            "trace_id": trace_id
        })
    
    return pd.DataFrame(results)
```

### 2.3 Evaluation Pipeline Architecture

```
┌─────────────────┐
│  GenAI Service  │
│   (FastAPI)     │
└────────┬────────┘
         │ traces
         ▼
┌─────────────────┐
│     Phoenix     │
│  (trace store)  │
└────────┬────────┘
         │ export spans
         ▼
┌─────────────────┐
│  Eval Pipeline  │──────┐
│  (batch job)    │      │
└────────┬────────┘      │
         │               │ Tool Compliance
         │               │ Faithfulness
         │               │ Custom Evals
         ▼               │
┌─────────────────┐      │
│   Annotations   │◄─────┘
│  (logged back)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Alerting &    │
│   Dashboards    │
└─────────────────┘
```

## 3. Making Agents More Robust

### 3.1 Prompt Engineering with Phoenix Registry

Use Phoenix's built-in prompt management for version control and iteration.

#### Mandatory Tool Language

Update agent instructions to be explicit:

```python
# BEFORE (ambiguous)
instruction = """
WORKFLOW:
1. Use list_patients() to see available patients if needed
2. Use fetch_patient_record(patient_id) to retrieve the FHIR bundle
"""

# AFTER (mandatory)
instruction = """
WORKFLOW:
1. You MUST call fetch_patient_record(patient_id) to retrieve the FHIR bundle
2. DO NOT generate any patient information without first calling this tool
3. If the tool call fails, report the error—do not fabricate data

CRITICAL: Any patient-specific information in your response MUST come from 
the fetch_patient_record() tool output. Generating fictional patient data 
is a serious error.
"""
```

#### Negative Examples

Add explicit "don't do this" examples:

```python
instruction += """
INCORRECT BEHAVIOR (DO NOT DO THIS):
- Generating patient names, conditions, or lab values from memory
- Providing a summary without first calling fetch_patient_record()
- Making up FHIR resource IDs for citations

CORRECT BEHAVIOR:
- Call fetch_patient_record() first
- Extract all information from the returned FHIR bundle
- Cite actual resource IDs from the bundle
"""
```

#### Phoenix Registry Integration

```python
from phoenix.client import Client

client = Client()

# Pull prompt by tag for environment-specific versions
prompt = client.prompts.get(
    prompt_identifier="medical-records-summarizer",
    tag="production"  # or "staging", "dev"
)

# Use in agent definition
medical_records_agent = Agent(
    name="medical_records_assistant",
    model="gemini-2.0-flash-exp",
    instruction=prompt.format()["messages"][0]["content"],
    tools=[list_patients, fetch_patient_record, save_summary],
)
```

### 3.2 Code-Level Guardrails

Add validation in the endpoint before accepting responses.

#### Validate Tool Usage

```python
@app.post("/patients/{patient_id}/summarize")
async def summarize_patient(patient_id: str, request: SummarizeRequest):
    response, tools_used = await run_agent(
        medical_records_agent,
        prompt,
        user_id=request.user_id,
    )
    
    # GUARDRAIL: Verify required tool was called
    if "fetch_patient_record" not in tools_used:
        logger.error(f"Agent skipped fetch_patient_record for {patient_id}")
        
        # Option 1: Retry with explicit instruction
        retry_prompt = f"""
        You MUST call fetch_patient_record("{patient_id}") before responding.
        Do not generate any patient information without this tool call.
        """
        response, tools_used = await run_agent(
            medical_records_agent,
            retry_prompt,
            user_id=request.user_id,
        )
        
        # Option 2: Return error if still no tool call
        if "fetch_patient_record" not in tools_used:
            raise HTTPException(
                status_code=500,
                detail="Agent failed to retrieve patient data"
            )
    
    # Continue with response processing...
```

#### Validate Citation Patterns

```python
def validate_citations(citations: list[dict], tool_output: dict) -> bool:
    """Check that citations reference real resource IDs from the FHIR bundle."""
    # Extract all resource IDs from the FHIR bundle
    valid_ids = set()
    for entry in tool_output.get("entry", []):
        resource = entry.get("resource", {})
        if "id" in resource:
            valid_ids.add(resource["id"])
    
    # Check each citation
    for citation in citations:
        resource_id = citation.get("resource_id")
        if resource_id and resource_id not in valid_ids:
            logger.warning(f"Invalid citation resource_id: {resource_id}")
            return False
    
    return True
```

### 3.3 Structured Output Validation

#### JSON Schema Enforcement

The agent prompt already requires JSON output. Add validation:

```python
from pydantic import BaseModel, validator

class AgentSummaryOutput(BaseModel):
    summary: str
    citations: list[Citation]
    
    @validator("summary")
    def summary_not_empty(cls, v):
        if not v or len(v) < 50:
            raise ValueError("Summary too short or empty")
        return v
    
    @validator("citations")
    def citations_required(cls, v):
        if not v:
            raise ValueError("Citations required but none provided")
        return v

def parse_agent_summary_response(response: str) -> tuple[str, list[dict]]:
    # ... existing parsing logic ...
    
    # Add validation
    try:
        validated = AgentSummaryOutput(summary=summary, citations=citations)
        return validated.summary, [c.dict() for c in validated.citations]
    except ValidationError as e:
        logger.warning(f"Agent output validation failed: {e}")
        return response, []  # Graceful degradation
```

## 4. Implementation Checklist

### Immediate (Code Changes)
- [x] Update `medical_records_agent` prompt with mandatory tool language
- [x] Add `parse_agent_summary_response()` for structured output
- [ ] Add tool usage validation in `summarize_patient` endpoint
- [ ] Add citation validation against tool output

### Short-Term (Evaluation Pipeline)
- [ ] Set up Phoenix prompt registry for agent prompts
- [ ] Create custom "tool compliance" evaluator
- [ ] Configure FaithfulnessEvaluator pipeline
- [ ] Create batch evaluation job (cron or triggered)
- [ ] Log evaluation results back to Phoenix as annotations

### Medium-Term (Monitoring & Alerting)
- [ ] Dashboard for hallucination/compliance rates
- [ ] Alerts for low faithfulness scores
- [ ] Trend analysis over time

## 5. Open Questions / Future Research

| Question | Context | Priority |
|----------|---------|----------|
| Real-time guardrails | Does AX support inline evaluation before response is returned? | High |
| Prompt Learning | Can we auto-optimize prompts based on eval feedback? | Medium |
| Session state | Is `InMemorySessionService` causing context pollution? | Medium |
| Caching | How to cache prompts pulled from Phoenix registry? | Low |

## References

- [Phoenix Evaluation Docs](https://docs.arize.com/phoenix/evaluation)
- [FaithfulnessEvaluator](https://docs.arize.com/phoenix/evaluation/running-pre-tested-evals/hallucinations)
- [Agent Function Calling Eval](https://docs.arize.com/phoenix/evaluation/running-pre-tested-evals/tool-calling-eval)
- [OpenInference Semantic Conventions](https://github.com/Arize-ai/openinference)
