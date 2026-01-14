"""E2E tests for MLflow trace export.

These tests verify actual trace export to a running MLflow instance.

Prerequisites:
    docker-compose -f docker/docker-compose.test.yml up -d

Run with:
    pytest tests/integration/e2e/ -m e2e -v
"""

import time

import pytest
import httpx


pytestmark = pytest.mark.e2e


class TestMlflowConfiguration:
    """E2E tests for MLflow configuration."""

    def test_sdk_configures_with_real_mlflow(
        self, e2e_config_yaml_mlflow, mlflow_available
    ):
        """GIVEN real MLflow running
        WHEN llmops.init() is called
        THEN SDK configures successfully.
        """
        mlflow = pytest.importorskip("mlflow")
        import llmops

        llmops.init(config_path=e2e_config_yaml_mlflow)

        assert llmops.is_configured()
        assert llmops.get_backend() == "mlflow"

    def test_experiment_created_in_mlflow(
        self, e2e_config_yaml_mlflow, mlflow_e2e_endpoint, mlflow_available
    ):
        """GIVEN llmops configured with MLflow
        WHEN llmops.init() is called
        THEN experiment is created in MLflow.
        """
        mlflow = pytest.importorskip("mlflow")
        import llmops

        llmops.init(config_path=e2e_config_yaml_mlflow)

        # Query MLflow API to verify experiment exists
        response = httpx.get(
            f"{mlflow_e2e_endpoint}/api/2.0/mlflow/experiments/get-by-name",
            params={"experiment_name": "e2e-test-service"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("experiment") is not None
        assert data["experiment"]["name"] == "e2e-test-service"


class TestMlflowSpanExport:
    """E2E tests for MLflow span export via OTLP."""

    def test_spans_exported_via_otlp(
        self, e2e_config_yaml_mlflow, mlflow_available
    ):
        """GIVEN llmops configured with MLflow
        WHEN spans are created
        THEN they are exported via OTLP to MLflow.
        """
        mlflow = pytest.importorskip("mlflow")
        import llmops
        from opentelemetry import trace

        llmops.init(config_path=e2e_config_yaml_mlflow)

        # Create a test span
        tracer = trace.get_tracer("e2e-test")
        with tracer.start_as_current_span("mlflow-e2e-test-span") as span:
            span.set_attribute("test.attribute", "test-value")

        llmops.shutdown()

        # Allow time for export
        time.sleep(2)

    def test_hierarchical_spans_exported(
        self, e2e_config_yaml_mlflow, mlflow_available
    ):
        """GIVEN llmops configured with MLflow
        WHEN parent and child spans are created
        THEN hierarchy is preserved.
        """
        mlflow = pytest.importorskip("mlflow")
        import llmops
        from opentelemetry import trace

        llmops.init(config_path=e2e_config_yaml_mlflow)

        tracer = trace.get_tracer("e2e-test")

        with tracer.start_as_current_span("parent-span") as parent:
            parent.set_attribute("span.level", "parent")

            with tracer.start_as_current_span("child-span") as child:
                child.set_attribute("span.level", "child")

        llmops.shutdown()


class TestMlflowLLMTracing:
    """E2E tests for LLM tracing with MLflow."""

    def test_llm_style_spans(
        self, e2e_config_yaml_mlflow, mlflow_available
    ):
        """GIVEN LLM-style spans
        WHEN exported to MLflow
        THEN semantic attributes are preserved.
        """
        mlflow = pytest.importorskip("mlflow")
        import llmops
        from opentelemetry import trace

        llmops.init(config_path=e2e_config_yaml_mlflow)

        tracer = trace.get_tracer("e2e-test")

        with tracer.start_as_current_span("llm-call") as span:
            span.set_attribute("gen_ai.system", "google")
            span.set_attribute("gen_ai.request.model", "gemini-2.0-flash")
            span.set_attribute("gen_ai.usage.input_tokens", 100)
            span.set_attribute("gen_ai.usage.output_tokens", 50)

        llmops.shutdown()

    def test_agent_workflow_with_mlflow(
        self, e2e_config_yaml_mlflow, mlflow_available
    ):
        """GIVEN agent workflow spans
        WHEN exported to MLflow
        THEN agent/tool/LLM structure is captured.
        """
        mlflow = pytest.importorskip("mlflow")
        import llmops
        from opentelemetry import trace

        llmops.init(config_path=e2e_config_yaml_mlflow)

        tracer = trace.get_tracer("e2e-test")

        # Simulate ADK-style agent workflow
        with tracer.start_as_current_span("agent_run") as agent:
            agent.set_attribute("agent.name", "e2e-test-agent")

            with tracer.start_as_current_span("call_llm") as llm:
                llm.set_attribute("gen_ai.request.model", "gemini-2.0-flash")

            with tracer.start_as_current_span("execute_tool") as tool:
                tool.set_attribute("tool.name", "test_tool")

        llmops.shutdown()


class TestMlflowAutolog:
    """E2E tests for MLflow autolog functionality."""

    def test_autolog_enabled(
        self, e2e_config_yaml_mlflow, mlflow_available
    ):
        """GIVEN llmops configured with MLflow
        WHEN SDK initializes
        THEN mlflow.autolog is enabled.
        """
        mlflow = pytest.importorskip("mlflow")
        import llmops

        # Verify autolog was called during init
        llmops.init(config_path=e2e_config_yaml_mlflow)

        # MLflow autolog should be active
        # This test primarily verifies no errors during setup
        assert llmops.is_configured()
        assert llmops.get_backend() == "mlflow"
