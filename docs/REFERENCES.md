# External References

A curated collection of documentation links for libraries, semantic conventions, and tools used in this project.

---

## OpenTelemetry

### Specifications & Semantic Conventions
- [GenAI Spans Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/) - Defines standard span attributes for generative AI operations
- [GenAI Events Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-events/) - Defines standard event attributes for GenAI
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/) - OpenTelemetry Protocol specification
- [OTel Trace SDK Specification](https://opentelemetry.io/docs/specs/otel/trace/sdk/) - Tracing SDK specification
- [Library Guidelines](https://opentelemetry.io/docs/specs/otel/library-guidelines/) - API vs SDK separation design pattern

### Python SDK
- [OpenTelemetry Python Trace API](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html) - Python tracing API documentation
- [set_tracer_provider() Race Condition Issue](https://github.com/open-telemetry/opentelemetry-python/issues/2181) - Known issue with multiple provider setup

---

## Arize Phoenix

### Core Documentation
- [Phoenix Documentation](https://arize.com/docs/phoenix) - Main Phoenix documentation
- [Phoenix GitHub Repository](https://github.com/Arize-ai/phoenix) - Source code and examples

### Evaluation
- [Phoenix Evaluation Overview](https://docs.arize.com/phoenix/evaluation) - LLM-as-judge evaluation capabilities
- [Pre-Built Evaluators](https://docs.arize.com/phoenix/evaluation/running-pre-tested-evals) - Battle-tested evaluators (faithfulness, relevance, etc.)
- [Hallucination Detection (FaithfulnessEvaluator)](https://docs.arize.com/phoenix/evaluation/running-pre-tested-evals/hallucinations) - Detecting unfaithful outputs
- [Tool Calling Eval](https://docs.arize.com/phoenix/evaluation/running-pre-tested-evals/tool-calling-eval) - Evaluating agent tool selection
- [Custom LLM Evaluators Guide](https://docs.arize.com/phoenix/evaluation/how-to-evals/custom-llm-evaluators) - Building custom evaluators
- [Evaluation Benchmarks (GitHub)](https://github.com/Arize-ai/phoenix/tree/main/tutorials/evals) - Benchmark tutorials

### Prompt Management
- [Prompt Management Overview](https://docs.arize.com/phoenix/prompt-engineering/overview-prompts/prompt-management) - Version control and tagging
- [Using Prompts in Code](https://docs.arize.com/phoenix/prompt-engineering/how-to-prompts/using-a-prompt) - SDK integration
- [Prompt Playground](https://docs.arize.com/phoenix/prompt-engineering/overview-prompts/prompt-playground) - Interactive testing
- [Prompt Learning Tutorial](https://docs.arize.com/phoenix/prompt-engineering/tutorial/optimize-prompts-automatically) - Auto-optimization

### OTEL Integration
- [arize-phoenix-otel source](https://pypi.org/project/arize-phoenix-otel/) - Phoenix OpenTelemetry package
- [Phoenix OTEL Reference Documentation](https://arize-phoenix.readthedocs.io/projects/otel/en/latest/) - OTEL integration docs
- [Phoenix register() Source Code](https://github.com/Arize-ai/phoenix/blob/main/packages/phoenix-otel/src/phoenix/otel/otel.py) - Implementation reference

### Python API
- [arize-phoenix-client Python API](https://arize-phoenix.readthedocs.io/en/latest/) - Client library documentation
- [arize-phoenix-evals Python API](https://arize-phoenix.readthedocs.io/projects/evals/en/latest/) - Evaluation library docs

### Arize AX (Enterprise)
- [Arize AX OpenTelemetry Integration](https://arize.com/docs/ax/integrations/opentelemetry/opentelemetry-arize-otel) - Enterprise OTEL setup

---

## OpenInference

OpenInference is the semantic convention standard used by Arize Phoenix.

### Specification
- [OpenInference GitHub Repository](https://github.com/Arize-ai/openinference) - Main repository
- [OpenInference Semantic Conventions](https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md) - Full attribute specification
- [OpenInference Python Packages](https://github.com/Arize-ai/openinference/tree/main/python) - Python instrumentation packages

### Instrumentors
- [Google ADK Instrumentor](https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-adk) - Auto-instrumentation for Google ADK
- [Google GenAI Instrumentor](https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-google-genai) - Auto-instrumentation for Google GenAI SDK
- [FastAPI Instrumentor](https://pypi.org/project/openinference-instrumentation-fastapi/) - FastAPI request tracing
- [OpenInference Instrumentation Base](https://pypi.org/project/openinference-instrumentation/) - Base instrumentation package

---

## MLflow

### Tracing Documentation
- [MLflow Documentation](https://mlflow.org/docs/latest/) - Main MLflow documentation
- [MLflow Tracing Overview](https://mlflow.org/docs/latest/genai/tracing/index.html) - GenAI tracing features
- [Manual Tracing Guide](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/manual-tracing/) - Manual instrumentation
- [Automatic Tracing](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/automatic/) - Auto-instrumentation setup
- [Trace Concepts](https://mlflow.org/docs/latest/genai/concepts/trace/) - Core tracing concepts
- [Tracing Integrations](https://mlflow.org/docs/latest/genai/tracing/integrations/index.html) - Supported libraries
- [Google ADK Integration](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/google-adk/) - ADK-specific setup

### Source Code
- [MLflow GitHub Repository](https://github.com/mlflow/mlflow) - Source code

---

## Google AI

### Agent Development Kit (ADK)
- [Google ADK Python](https://github.com/google/adk-python) - Agent Development Kit SDK

### GenAI SDK
- [Google GenAI Python SDK](https://github.com/googleapis/python-genai) - Gemini API client

---

## Development Tools

### Package Management
- [UV Documentation](https://docs.astral.sh/uv/) - Fast Python package manager
- [Just Task Runner](https://github.com/casey/just) - Command runner for project tasks

### Pre-commit Hooks
- [Prek Documentation](https://prek.j178.dev/) - Fast pre-commit replacement
- [Prek Installation](https://prek.j178.dev/installation/) - Setup instructions

### Containers
- [Docker](https://www.docker.com/) - Container platform
- [Docker Compose Documentation](https://docs.docker.com/compose/) - Multi-container orchestration

---

## Quick Reference by Use Case

### Setting Up Auto-Instrumentation
1. [Phoenix OTEL Reference](https://arize-phoenix.readthedocs.io/projects/otel/en/latest/)
2. [OpenInference Instrumentors](https://github.com/Arize-ai/openinference/tree/main/python)
3. [MLflow Automatic Tracing](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/automatic/)

### Understanding Semantic Conventions
1. [OTel GenAI Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/)
2. [OpenInference Semantic Conventions](https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md)
3. [MLflow Trace Concepts](https://mlflow.org/docs/latest/genai/concepts/trace/)

### Implementing Evaluations
1. [Phoenix Evaluation Overview](https://docs.arize.com/phoenix/evaluation)
2. [Custom Evaluators Guide](https://docs.arize.com/phoenix/evaluation/how-to-evals/custom-llm-evaluators)
3. [Hallucination Detection](https://docs.arize.com/phoenix/evaluation/running-pre-tested-evals/hallucinations)

### Managing Prompts
1. [Prompt Management](https://docs.arize.com/phoenix/prompt-engineering/overview-prompts/prompt-management)
2. [Using Prompts in Code](https://docs.arize.com/phoenix/prompt-engineering/how-to-prompts/using-a-prompt)

---

**Last Updated:** 2026-01-22
