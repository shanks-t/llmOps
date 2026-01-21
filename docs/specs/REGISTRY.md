# Phoenix Prompt Registry Reference

Working document covering Phoenix's prompt management features, APIs, and areas requiring further exploration.

## 1. Overview

Phoenix provides a built-in prompt registry for centralized prompt management:

- **Version control**: Every save creates an immutable version
- **Tagging**: Tag versions for environments (production, staging, dev)
- **SDK access**: Pull prompts at runtime via Python or TypeScript
- **Playground**: Test prompts interactively with different models
- **No proprietary SDK**: Works with native OpenAI, Anthropic, Gemini clients

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Reusability** | Store and load prompts across use cases |
| **Versioning** | Track changes, rollback if needed |
| **Collaboration** | Share prompts across team members |
| **A/B Testing** | Deploy different versions via tags |
| **Audit Trail** | History of all prompt changes |

## 2. Core Features

### 2.1 Prompt Management

Create, store, and modify prompts via UI or SDK:

- **Name**: Human-readable identifier (e.g., "medical-records-summarizer")
- **Messages**: System, user, assistant message templates
- **Variables**: Placeholders like `{patient_id}` for runtime substitution
- **Model config**: Default model, temperature, max_tokens
- **Tools**: Tool/function definitions (for agents)
- **Response format**: JSON schema for structured output

### 2.2 Versioning

Every prompt save creates an immutable version:

```
my-prompt
├── Version 1 (abc123) - Initial version
├── Version 2 (def456) - Updated instructions
├── Version 3 (ghi789) - Added tool definitions  ← [staging]
└── Version 4 (jkl012) - Production ready        ← [production]
```

**Version IDs are immutable**: Once created, a version's content never changes. Safe for production pinning.

### 2.3 Tagging

Tags provide semantic pointers to specific versions:

| Tag | Purpose |
|-----|---------|
| `production` | Live traffic |
| `staging` | Pre-production testing |
| `dev` | Active development |
| `experiment-a` | A/B test variant |

**Moving tags**: Update which version a tag points to without code changes.

```python
# Code always pulls by tag—no version ID in code
prompt = client.prompts.get(prompt_identifier="my-prompt", tag="production")

# To deploy new version: move tag in UI (no code change needed)
```

### 2.4 Playground

Interactive prompt testing environment:

- **Multi-model testing**: Compare GPT-4, Claude, Gemini side-by-side
- **Parameter tuning**: Adjust temperature, max_tokens, etc.
- **Variable substitution**: Test with different input values
- **Span Replay**: Re-run an actual LLM call with modified prompt
- **Save to registry**: Promote playground experiments to versioned prompts

### 2.5 Prompt Learning (Auto-Optimization)

Phoenix can automatically improve prompts based on evaluation feedback:

1. Run prompt over dataset
2. Evaluate outputs with LLM judge
3. Feed evaluation results to optimizer
4. Generate improved prompt version

**Status**: Needs further research on API and workflow.

## 3. SDK API Reference

### 3.1 Installation

```bash
# Python
pip install arize-phoenix-client

# TypeScript
npm install @arizeai/phoenix-client
```

### 3.2 Client Initialization

```python
from phoenix.client import Client

# Default: reads PHOENIX_ENDPOINT and PHOENIX_API_KEY from env
client = Client()

# Explicit configuration
client = Client(
    endpoint="https://app.phoenix.arize.com",
    api_key="your-api-key"
)
```

```typescript
import { Client } from "@arizeai/phoenix-client";

const client = new Client({
  endpoint: "https://app.phoenix.arize.com",
  apiKey: "your-api-key"
});
```

### 3.3 Pulling Prompts

#### By Name (Latest Version)

```python
# Python
prompt = client.prompts.get(prompt_identifier="my-prompt")
```

```typescript
// TypeScript
import { getPrompt } from "@arizeai/phoenix-client/prompts";
const prompt = await getPrompt({ name: "my-prompt" });
```

**Note**: Returns latest version. Use only in development.

#### By Version ID (Immutable)

```python
# Python - pinned to specific version
prompt = client.prompts.get(prompt_version_id="UHJvbXB0VmVyc2lvbjoy")
```

```typescript
// TypeScript
const prompt = await getPrompt({ versionId: "UHJvbXB0VmVyc2lvbjoy" });
```

**Use case**: When you need guaranteed reproducibility.

#### By Tag (Recommended for Production)

```python
# Python
prompt = client.prompts.get(
    prompt_identifier="my-prompt",
    tag="production"
)
```

```typescript
// TypeScript
const prompt = await getPrompt({ 
    name: "my-prompt", 
    tag: "production" 
});
```

**Best practice**: Use tags for environment-based deployment.

### 3.4 Formatting Prompts

Substitute variables at runtime:

```python
# Python
prompt = client.prompts.get(prompt_identifier="my-prompt", tag="production")

# Format with variables
formatted = prompt.format(variables={
    "patient_id": "patient-002",
    "output_format": "JSON"
})

# Use with OpenAI
from openai import OpenAI
oai = OpenAI()
response = oai.chat.completions.create(**formatted)
```

```typescript
// TypeScript
import { getPrompt, toSDK } from "@arizeai/phoenix-client/prompts";
import OpenAI from "openai";

const prompt = await getPrompt({ name: "my-prompt", tag: "production" });

// Convert to OpenAI format
const params = toSDK({
    sdk: "openai",
    prompt,
    variables: { patient_id: "patient-002" }
});

const openai = new OpenAI();
const response = await openai.chat.completions.create(params);
```

### 3.5 SDK Provider Support

| Provider | Python | TypeScript |
|----------|--------|------------|
| OpenAI | Yes | Yes |
| Anthropic | Yes | Yes |
| Google Gemini | Yes | - |
| Vercel AI SDK | - | Yes |

**Cross-provider conversion**: If prompt was saved with one provider, SDK applies best-effort conversion to target provider.

### 3.6 Creating/Updating Prompts via SDK

**Status**: Needs research. UI-based creation is documented, but programmatic creation API needs verification.

```python
# Hypothetical API (needs verification)
client.prompts.create(
    name="my-new-prompt",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "{query}"}
    ],
    model="gpt-4o",
    temperature=0.7
)
```

## 4. Integration Patterns

### 4.1 Basic Integration

```python
from phoenix.client import Client
from google.adk import Agent

client = Client()

# Pull prompt at startup or per-request
prompt = client.prompts.get(
    prompt_identifier="medical-records-agent",
    tag="production"
)

# Extract instruction from prompt
instruction = prompt.format()["messages"][0]["content"]

# Use in agent
agent = Agent(
    name="medical_records_assistant",
    model="gemini-2.0-flash-exp",
    instruction=instruction,
    tools=[fetch_patient_record, save_summary],
)
```

### 4.2 With Caching

```python
from functools import lru_cache
from phoenix.client import Client

client = Client()

@lru_cache(maxsize=10)
def get_prompt_cached(name: str, tag: str, ttl_hash: int):
    """Cache prompts with time-based invalidation."""
    return client.prompts.get(prompt_identifier=name, tag=tag)

def get_prompt(name: str, tag: str, ttl_seconds: int = 300):
    """Get prompt with caching."""
    import time
    ttl_hash = int(time.time() // ttl_seconds)
    return get_prompt_cached(name, tag, ttl_hash)

# Usage
prompt = get_prompt("my-prompt", "production", ttl_seconds=300)
```

### 4.3 With Fallback

```python
from phoenix.client import Client

client = Client()

# Hardcoded fallback prompt
FALLBACK_INSTRUCTION = """
You are a medical records assistant. Summarize patient records accurately.
"""

def get_agent_instruction(prompt_name: str, tag: str) -> str:
    """Get prompt with fallback on failure."""
    try:
        prompt = client.prompts.get(prompt_identifier=prompt_name, tag=tag)
        return prompt.format()["messages"][0]["content"]
    except Exception as e:
        logger.warning(f"Failed to fetch prompt {prompt_name}: {e}")
        return FALLBACK_INSTRUCTION
```

### 4.4 Environment-Based Tags

```python
import os
from phoenix.client import Client

client = Client()

def get_environment_tag() -> str:
    """Map deployment environment to prompt tag."""
    env = os.getenv("DEPLOYMENT_ENV", "dev")
    return {
        "production": "production",
        "staging": "staging",
        "development": "dev",
        "local": "dev",
    }.get(env, "dev")

# Usage
prompt = client.prompts.get(
    prompt_identifier="my-prompt",
    tag=get_environment_tag()
)
```

## 5. Integration with Evaluations

### 5.1 Prompt → Trace → Eval Loop

```
┌─────────────────┐
│ Phoenix Registry│
│   (prompts)     │
└────────┬────────┘
         │ pull prompt
         ▼
┌─────────────────┐
│  GenAI Service  │
│   (agent)       │
└────────┬────────┘
         │ traces
         ▼
┌─────────────────┐
│     Phoenix     │
│  (trace store)  │
└────────┬────────┘
         │ evaluate
         ▼
┌─────────────────┐
│   Evaluators    │
│ (faithfulness)  │
└────────┬────────┘
         │ feedback
         ▼
┌─────────────────┐
│  Iterate on     │
│    Prompt       │
└─────────────────┘
```

### 5.2 Tracking Prompt Version in Traces

Log which prompt version produced each trace:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def run_with_prompt_tracking(prompt_name: str, tag: str, query: str):
    prompt = client.prompts.get(prompt_identifier=prompt_name, tag=tag)
    
    with tracer.start_as_current_span("agent_invocation") as span:
        # Log prompt metadata
        span.set_attribute("prompt.name", prompt_name)
        span.set_attribute("prompt.tag", tag)
        span.set_attribute("prompt.version_id", prompt.id)
        
        # Run agent
        response = run_agent(prompt, query)
        return response
```

### 5.3 Evaluating Prompt Versions

Compare performance across prompt versions:

```python
from phoenix.client import Client
from phoenix.evals import FaithfulnessEvaluator

client = Client()
evaluator = FaithfulnessEvaluator(llm=LLM(provider="openai", model="gpt-4o"))

# Get traces for each prompt version
v1_traces = client.spans.get_spans_dataframe(
    project_identifier="genai-service",
    filter="prompt.version_id == 'version-1'"
)

v2_traces = client.spans.get_spans_dataframe(
    project_identifier="genai-service",
    filter="prompt.version_id == 'version-2'"
)

# Evaluate each
v1_results = evaluator.evaluate_dataframe(v1_traces)
v2_results = evaluator.evaluate_dataframe(v2_traces)

# Compare
print(f"V1 faithfulness: {v1_results['score'].mean():.2%}")
print(f"V2 faithfulness: {v2_results['score'].mean():.2%}")
```

## 6. SDLC Best Practices

### 6.1 Recommended Workflow

```
1. DEVELOP
   └── Create/edit prompt in Playground
   └── Tag as "dev"
   └── Test interactively

2. TEST
   └── Run prompt over test dataset
   └── Evaluate with LLM judges
   └── Fix issues, iterate

3. STAGE
   └── Move "staging" tag to tested version
   └── Deploy to staging environment
   └── Run integration tests

4. RELEASE
   └── Move "production" tag to staged version
   └── Monitor production metrics
   └── Keep previous version for rollback
```

### 6.2 Rollback Strategy

```python
# If issues detected in production:
# 1. Move "production" tag back to previous version (in UI)
# 2. No code deployment needed
# 3. Application automatically uses previous version on next request

# To verify rollback:
prompt = client.prompts.get(prompt_identifier="my-prompt", tag="production")
print(f"Current production version: {prompt.id}")
```

### 6.3 CI/CD Integration

**Approach 1**: Prompt changes managed separately from code

```yaml
# Prompts managed in Phoenix UI
# Code only references by name + tag
# No prompt content in git
```

**Approach 2**: Prompts as code (needs research)

```yaml
# Hypothetical: prompts stored in git, synced to Phoenix
# on-push:
#   - Upload prompts/*.yaml to Phoenix
#   - Update tags based on branch
```

### 6.4 Multi-Environment Setup

| Environment | Tag | Phoenix Instance |
|-------------|-----|------------------|
| Local dev | `dev` | localhost:6006 |
| CI/Test | `dev` | Phoenix Cloud (test space) |
| Staging | `staging` | Phoenix Cloud (prod space) |
| Production | `production` | Phoenix Cloud (prod space) |

## 7. Phoenix OSS vs Arize AX

### Confirmed Feature Parity

| Feature | Phoenix (OSS) | Arize AX |
|---------|---------------|----------|
| Prompt CRUD | Yes | Yes |
| Version history | Yes | Yes |
| Tagging | Yes | Yes |
| Playground | Yes | Yes |
| Python SDK | Yes | Yes |
| TypeScript SDK | Yes | Yes |
| Variable substitution | Yes | Yes |
| Tool definitions | Yes | Yes |
| Response format | Yes | Yes |

### Research Needed

| Feature | Phoenix (OSS) | Arize AX | Status |
|---------|---------------|----------|--------|
| **Programmatic create/update** | Unknown | Unknown | Needs verification |
| **Prompt Learning (auto-optimize)** | Yes (docs mention) | Unknown | Needs API research |
| **RBAC for prompts** | Unknown | Likely | Needs verification |
| **Audit logging** | Unknown | Likely | Needs verification |
| **Caching/CDN** | In progress | Unknown | Needs verification |
| **Prompt diff view** | Unknown | Unknown | Needs verification |
| **Prompt comments/annotations** | Unknown | Unknown | Needs verification |

### Questions to Research

1. **Programmatic API**: Can prompts be created/updated via SDK, or UI-only?

2. **Prompt Learning**: How does the auto-optimization feature work? What's the API?

3. **RBAC**: Can we restrict who can edit production-tagged prompts?

4. **Audit logging**: Is there a history of who changed what and when?

5. **Caching**: Phoenix docs mention caching is "in progress"—what's available now?

6. **Git integration**: Any support for syncing prompts with git repositories?

7. **Approval workflows**: Can we require approval before tagging as production?

## 8. Considerations & Limitations

### 8.1 Network Dependency

Pulling prompts requires network access to Phoenix:

```python
# Risk: If Phoenix is down, prompt fetch fails
# Mitigation: Implement caching + fallback

try:
    prompt = client.prompts.get(...)
except Exception:
    prompt = FALLBACK_PROMPT  # Hardcoded backup
```

### 8.2 Latency

Prompt fetch adds latency to request path:

| Scenario | Latency Impact |
|----------|----------------|
| No caching | +50-200ms per request |
| With caching | +0ms (cache hit) |
| Cache miss | +50-200ms (first request) |

**Recommendation**: Always implement caching for production.

### 8.3 Debugging Complexity

Prompts stored externally adds debugging complexity:

- **Which version was used?** Log `prompt.version_id` in traces
- **What was the actual prompt?** Check Phoenix UI for version content
- **Why did it change?** Check version history in Phoenix

### 8.4 Security Considerations

- **API keys**: Secure Phoenix API key in secrets manager
- **Prompt injection**: Validate user inputs before substitution
- **Sensitive data**: Don't log prompt content with PII

## 9. Open Questions

- [ ] Can prompts be created/updated programmatically via SDK?
- [ ] How does Prompt Learning API work?
- [ ] Is there RBAC for prompt management (restrict production edits)?
- [ ] Is there audit logging for prompt changes?
- [ ] What caching mechanisms are currently available?
- [ ] Can we integrate prompt versioning with git/CI/CD?
- [ ] Is there an approval workflow for production promotions?
- [ ] How to handle prompt migrations between Phoenix instances?

## References

- [Phoenix Prompt Management Docs](https://docs.arize.com/phoenix/prompt-engineering/overview-prompts/prompt-management)
- [Using Prompts in Code](https://docs.arize.com/phoenix/prompt-engineering/how-to-prompts/using-a-prompt)
- [Prompt Playground](https://docs.arize.com/phoenix/prompt-engineering/overview-prompts/prompt-playground)
- [Prompt Learning Tutorial](https://docs.arize.com/phoenix/prompt-engineering/tutorial/optimize-prompts-automatically)
- [arize-phoenix-client Python API](https://arize-phoenix.readthedocs.io/en/latest/)
