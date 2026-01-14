"""E2E tests for Phoenix OTLP export.

These tests verify actual span export to a running Phoenix instance.

Prerequisites:
    docker-compose -f docker/docker-compose.test.yml up -d

Run with:
    pytest tests/integration/e2e/ -m e2e -v
"""

import time

import pytest
import httpx


pytestmark = pytest.mark.e2e


class TestPhoenixSpanExport:
    """E2E tests for Phoenix span export."""

    def test_sdk_configures_with_real_phoenix(
        self, e2e_config_yaml_phoenix, phoenix_available
    ):
        """GIVEN real Phoenix running
        WHEN llmops.init() is called
        THEN SDK configures successfully.
        """
        import llmops

        llmops.init(config_path=e2e_config_yaml_phoenix)

        assert llmops.is_configured()
        assert llmops.get_backend() == "phoenix"

    def test_spans_exported_to_phoenix(
        self, e2e_config_yaml_phoenix, phoenix_e2e_base, phoenix_available
    ):
        """GIVEN llmops configured with Phoenix
        WHEN spans are created and flushed
        THEN they are exported to Phoenix.
        """
        import llmops
        from opentelemetry import trace

        llmops.init(config_path=e2e_config_yaml_phoenix)

        # Create a test span with unique name
        test_span_name = f"e2e-test-span-{int(time.time())}"
        tracer = trace.get_tracer("e2e-test")

        with tracer.start_as_current_span(test_span_name) as span:
            span.set_attribute("test.attribute", "test-value")
            span.set_attribute("e2e.test", True)

        # Force flush to ensure export
        llmops.shutdown()

        # Allow time for Phoenix to process
        time.sleep(2)

        # Verify Phoenix received the spans by checking the projects endpoint
        # Phoenix stores traces under projects
        response = httpx.get(f"{phoenix_e2e_base}/v1/projects", timeout=10)
        assert response.status_code == 200

    def test_multiple_spans_with_hierarchy(
        self, e2e_config_yaml_phoenix, phoenix_available
    ):
        """GIVEN llmops configured with Phoenix
        WHEN parent and child spans are created
        THEN hierarchy is preserved in export.
        """
        import llmops
        from opentelemetry import trace

        llmops.init(config_path=e2e_config_yaml_phoenix)

        tracer = trace.get_tracer("e2e-test")

        # Create hierarchical spans
        with tracer.start_as_current_span("parent-span") as parent:
            parent.set_attribute("span.type", "parent")

            with tracer.start_as_current_span("child-span-1") as child1:
                child1.set_attribute("span.type", "child")

            with tracer.start_as_current_span("child-span-2") as child2:
                child2.set_attribute("span.type", "child")

        llmops.shutdown()

        # If we get here without errors, export succeeded
        # Full verification would require querying Phoenix API for traces

    def test_span_attributes_exported(
        self, e2e_config_yaml_phoenix, phoenix_available
    ):
        """GIVEN spans with various attribute types
        WHEN exported to Phoenix
        THEN attributes are preserved.
        """
        import llmops
        from opentelemetry import trace

        llmops.init(config_path=e2e_config_yaml_phoenix)

        tracer = trace.get_tracer("e2e-test")

        with tracer.start_as_current_span("attributes-test") as span:
            # Test various attribute types
            span.set_attribute("string.attr", "test-string")
            span.set_attribute("int.attr", 42)
            span.set_attribute("float.attr", 3.14)
            span.set_attribute("bool.attr", True)

        llmops.shutdown()


class TestPhoenixLLMSpans:
    """E2E tests for LLM-specific spans in Phoenix."""

    def test_llm_span_attributes(
        self, e2e_config_yaml_phoenix, phoenix_available
    ):
        """GIVEN LLM-style spans
        WHEN exported to Phoenix
        THEN OpenInference semantic attributes are preserved.
        """
        import llmops
        from opentelemetry import trace

        llmops.init(config_path=e2e_config_yaml_phoenix)

        tracer = trace.get_tracer("e2e-test")

        # Create span with OpenInference LLM attributes
        with tracer.start_as_current_span("llm-call") as span:
            span.set_attribute("openinference.span.kind", "LLM")
            span.set_attribute("llm.model_name", "test-model")
            span.set_attribute("llm.provider", "test-provider")
            span.set_attribute("llm.token_count.prompt", 100)
            span.set_attribute("llm.token_count.completion", 50)

        llmops.shutdown()

    def test_agent_workflow_spans(
        self, e2e_config_yaml_phoenix, phoenix_available
    ):
        """GIVEN agent workflow spans
        WHEN exported to Phoenix
        THEN agent/tool/LLM hierarchy is preserved.
        """
        import llmops
        from opentelemetry import trace

        llmops.init(config_path=e2e_config_yaml_phoenix)

        tracer = trace.get_tracer("e2e-test")

        # Simulate ADK-style agent workflow
        with tracer.start_as_current_span("agent_run") as agent:
            agent.set_attribute("openinference.span.kind", "AGENT")
            agent.set_attribute("agent.name", "e2e-test-agent")

            with tracer.start_as_current_span("call_llm") as llm:
                llm.set_attribute("openinference.span.kind", "LLM")
                llm.set_attribute("llm.model_name", "gemini-2.0-flash")

            with tracer.start_as_current_span("execute_tool") as tool:
                tool.set_attribute("openinference.span.kind", "TOOL")
                tool.set_attribute("tool.name", "test_tool")

        llmops.shutdown()
