#!/usr/bin/env python3
"""Test trace capture to Phoenix backend."""

import llmops
from opentelemetry import trace

# Configure SDK with Phoenix backend
print("Configuring llmops with Phoenix backend...")
llmops.configure(
    backend="phoenix",
    endpoint="http://localhost:6006/v1/traces",
    service_name="test-trace-capture",
)

# Get a tracer to create manual spans for testing
tracer = trace.get_tracer("test-trace-capture")

print("\nCreating test spans...")

# Create a parent span simulating an agent workflow
with tracer.start_as_current_span("agent-workflow") as workflow_span:
    workflow_span.set_attribute("agent.name", "test-agent")

    # Child span simulating an LLM call
    with tracer.start_as_current_span("llm-call") as llm_span:
        llm_span.set_attribute("gen_ai.system", "test")
        llm_span.set_attribute("gen_ai.request.model", "test-model")
        llm_span.set_attribute("gen_ai.usage.input_tokens", 10)
        llm_span.set_attribute("gen_ai.usage.output_tokens", 20)
        print("  Created LLM span")

    # Child span simulating a tool call
    with tracer.start_as_current_span("tool-call") as tool_span:
        tool_span.set_attribute("tool.name", "get_weather")
        tool_span.set_attribute("tool.input", "Paris")
        tool_span.set_attribute("tool.output", "Sunny, 22C")
        print("  Created tool span")

print("\nFlushing traces...")
llmops.shutdown()

print("\n" + "="*50)
print("Test complete!")
print("View traces at: http://localhost:6006")
print("="*50)
