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
- [arize-phoenix-otel PyPI](https://pypi.org/project/arize-phoenix-otel/) - Phoenix OpenTelemetry package
- [Phoenix OTEL Reference Documentation](https://arize-phoenix.readthedocs.io/projects/otel/en/latest/) - OTEL integration docs
- [Phoenix register() Source Code](https://github.com/Arize-ai/phoenix/blob/main/packages/phoenix-otel/src/phoenix/otel/otel.py) - Implementation reference

### Python API
- [arize-phoenix-client Python API](https://arize-phoenix.readthedocs.io/en/latest/) - Client library documentation
- [arize-phoenix-evals Python API](https://arize-phoenix.readthedocs.io/projects/evals/en/latest/) - Evaluation library docs

---

## Arize AX (Enterprise Platform)

Arize AX is the production-grade enterprise observability platform for monitoring, debugging, and improving LLM applications and AI Agents at scale.

### Getting Started
- [Arize AX Documentation](https://arize.com/docs/ax) - Main documentation portal
- [Quickstart: Tracing](https://arize.com/docs/ax/quickstarts/quickstart-tracing) - Get tracing integrated in minutes
- [Quickstart: Run First Experiment](https://arize.com/docs/ax/quickstarts/quickstart-run-first-experiment) - Run your first evaluation experiment

### Tracing & Observability
- [Setup Tracing](https://arize.com/docs/ax/observe/tracing/set-up-tracing) - Configure tracing for your application
- [Spans](https://arize.com/docs/ax/observe/tracing/spans) - Understanding span types and attributes
- [Agent Graph & Path](https://arize.com/docs/ax/observe/tracing/agents) - Visualize agent execution flows
- [Add Attributes, Metadata and Tags](https://arize.com/docs/ax/observe/tracing/configure/add-attributes-metadata-and-tags) - Enrich spans with custom data
- [Configure OTEL Tracer](https://arize.com/docs/ax/observe/tracing/configure/customize-auto-instrumentation) - Customize auto-instrumentation
- [Tracing Integrations Overview](https://arize.com/docs/ax/observe/tracing-integrations) - All supported integrations
- [OTel Collector Deployment Patterns](https://arize.com/docs/ax/observe/tracing/configure-tracing-options/otel-collector-deployment-patterns) - Production deployment strategies

### Evaluation
- [Online Evaluations](https://arize.com/docs/ax/evaluate/online-evals) - Real-time evaluation on production data
- [Run Evaluations in the UI](https://arize.com/docs/ax/evaluate/online-evals/run-evaluations-in-the-ui) - Configure evaluators in the dashboard
- [Log Evaluations to Arize](https://arize.com/docs/ax/evaluate/online-evals/log-evaluations-to-arize) - Programmatically attach evaluation results
- [Trace-Level Evaluations](https://arize.com/docs/ax/evaluate/trace-level-evaluations) - Evaluate entire traces end-to-end
- [Human Annotations Overview](https://arize.com/docs/ax/evaluate/human-annotations) - Configure annotation schemas
- [Annotate Spans](https://arize.com/docs/ax/evaluate/human-annotations/annotations) - Add human feedback to spans

### Monitoring & Guardrails
- [Configure Monitors](https://arize.com/docs/ax/observe/production-monitoring/configure-monitors) - Set up production monitoring
- [Programmatically Create Monitors](https://arize.com/docs/ax/machine-learning/machine-learning/how-to-ml/monitors/monitors-api) - Monitor creation via API
- [Guardrails](https://arize.com/docs/ax/observe/guardrails) - Input/output validation and safety

### Prompts
- [Prompt Playground](https://arize.com/docs/ax/prompts/prompt-playground) - Interactive prompt testing
- [Prompt Hub API](https://arize.com/docs/ax/reference/reference/prompt-hub-api) - Programmatic prompt management

### Datasets & Experiments
- [Datasets & Experiments Overview](https://arize.com/docs/ax/develop/datasets-and-experiments) - Systematic testing with curated data
- [Datasets](https://arize.com/docs/ax/develop/datasets) - Create and manage evaluation datasets
- [Export a Dataset](https://arize.com/docs/ax/develop/datasets/export-a-dataset) - Retrieve datasets programmatically

### API Reference
- [Python API Reference](https://arize.com/docs/ax/resources/api-reference/python-reference) - ArizeExportClient and SDK usage

### Self-Hosting
- [On-Premise SDK Usage](https://arize.com/docs/ax/selfhosting/on-premise-sdk-usage) - Configure SDK for self-hosted deployments
- [On-Premise Releases](https://arize.com/docs/ax/selfhosting/on-premise-releases) - Release notes for self-hosted versions

### LLM Provider Integrations
- [OpenAI Tracing](https://arize.com/docs/ax/integrations/llm-providers/openai/openai-tracing) - Auto-instrument OpenAI calls
- [Anthropic Tracing](https://arize.com/docs/ax/integrations/llm-providers/anthropic/anthropic-tracing) - Auto-instrument Anthropic/Claude calls
- [VertexAI Tracing](https://arize.com/docs/ax/integrations/llm-providers/vertexai/vertexai-tracing) - Auto-instrument Google Vertex AI
- [Amazon Bedrock Overview](https://arize.com/docs/ax/integrations/llm-providers/amazon-bedrock) - Bedrock integration overview
- [Amazon Bedrock Tracing](https://arize.com/docs/ax/integrations/llm-providers/amazon-bedrock/amazon-bedrock-tracing) - Auto-instrument Bedrock models
- [Amazon Bedrock Agents Tracing](https://arize.com/docs/ax/integrations/llm-providers/amazon-bedrock/amazon-bedrock-agents-tracing) - Trace Bedrock agent invocations
- [Amazon Bedrock Evals](https://arize.com/docs/ax/integrations/llm-providers/amazon-bedrock/amazon-bedrock-evals) - Use Bedrock models for evaluation

### Agent Framework Integrations
- [Google ADK Tracing](https://arize.com/docs/ax/integrations/python-agent-frameworks/google-adk/google-adk-tracing) - Auto-instrument Google Agent Development Kit
- [LangChain Tracing](https://arize.com/docs/ax/integrations/python-agent-frameworks/langchain/langchain-tracing) - Auto-instrument LangChain applications
- [LangChain.js Tracing](https://arize.com/docs/ax/integrations/frameworks-and-platforms/langchain/langchain-js) - JavaScript/TypeScript LangChain support
- [LlamaIndex Overview](https://arize.com/docs/ax/integrations/python-agent-frameworks/llamaindex) - LlamaIndex integration overview
- [LlamaIndex Tracing](https://arize.com/docs/ax/integrations/python-agent-frameworks/llamaindex/llamaindex-tracing) - Auto-instrument LlamaIndex
- [Guardrails AI Tracing](https://arize.com/docs/ax/integrations/python-agent-frameworks/guardrails-ai/guardrails-ai-tracing) - Trace Guardrails AI validators
- [Pydantic AI Tracing](https://arize.com/docs/ax/integrations/frameworks-and-platforms/pydantic/pydantic-ai-tracing) - Auto-instrument Pydantic AI
- [Agno](https://arize.com/docs/ax/integrations/frameworks-and-platforms/agno) - Agno framework integration

### Cookbooks & Examples
- [Evaluating RAG Retrieval Quality](https://arize.com/docs/ax/cookbooks/evaluation/evaluating-rag) - RAG evaluation best practices
- [Agents Cookbook](https://arize.com/docs/ax/cookbooks/code-examples/applications/agents) - Agent tracing examples

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
2. [Arize AX Setup Tracing](https://arize.com/docs/ax/observe/tracing/set-up-tracing)
3. [OpenInference Instrumentors](https://github.com/Arize-ai/openinference/tree/main/python)
4. [MLflow Automatic Tracing](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/automatic/)

### Understanding Semantic Conventions
1. [OTel GenAI Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/)
2. [OpenInference Semantic Conventions](https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md)
3. [Arize AX Spans](https://arize.com/docs/ax/observe/tracing/spans)
4. [MLflow Trace Concepts](https://mlflow.org/docs/latest/genai/concepts/trace/)

### Implementing Evaluations
1. [Phoenix Evaluation Overview](https://docs.arize.com/phoenix/evaluation)
2. [Arize AX Online Evaluations](https://arize.com/docs/ax/evaluate/online-evals)
3. [Arize AX Trace-Level Evaluations](https://arize.com/docs/ax/evaluate/trace-level-evaluations)
4. [Custom Evaluators Guide](https://docs.arize.com/phoenix/evaluation/how-to-evals/custom-llm-evaluators)
5. [Hallucination Detection](https://docs.arize.com/phoenix/evaluation/running-pre-tested-evals/hallucinations)

### Managing Prompts
1. [Prompt Management](https://docs.arize.com/phoenix/prompt-engineering/overview-prompts/prompt-management)
2. [Arize AX Prompt Playground](https://arize.com/docs/ax/prompts/prompt-playground)
3. [Arize AX Prompt Hub API](https://arize.com/docs/ax/reference/reference/prompt-hub-api)
4. [Using Prompts in Code](https://docs.arize.com/phoenix/prompt-engineering/how-to-prompts/using-a-prompt)

### Production Monitoring
1. [Arize AX Configure Monitors](https://arize.com/docs/ax/observe/production-monitoring/configure-monitors)
2. [Arize AX Guardrails](https://arize.com/docs/ax/observe/guardrails)
3. [Programmatic Monitor Creation](https://arize.com/docs/ax/machine-learning/machine-learning/how-to-ml/monitors/monitors-api)

### Agent Observability
1. [Arize AX Agent Graph & Path](https://arize.com/docs/ax/observe/tracing/agents)
2. [Arize AX Agents Cookbook](https://arize.com/docs/ax/cookbooks/code-examples/applications/agents)
3. [Google ADK Tracing (Arize AX)](https://arize.com/docs/ax/integrations/python-agent-frameworks/google-adk/google-adk-tracing)
4. [LangChain Tracing (Arize AX)](https://arize.com/docs/ax/integrations/python-agent-frameworks/langchain/langchain-tracing)

---

**Last Updated:** 2026-01-22
