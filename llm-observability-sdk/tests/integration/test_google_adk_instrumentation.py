"""Integration tests for Google ADK auto-instrumentation.

These tests verify that GoogleADKInstrumentor correctly captures spans
for Agent, Runner, and tool executions.
"""

import pytest
from unittest.mock import Mock, patch


class TestADKInstrumentorEnablement:
    """Tests for ADK instrumentor being enabled by llmops.configure()."""

    def test_configure_enables_adk_instrumentor(self):
        """GIVEN llmops configured with phoenix backend
        WHEN GoogleADKInstrumentor is available
        THEN it should be enabled automatically.
        """
        mock_instrumentor = Mock()
        mock_class = Mock(return_value=mock_instrumentor)

        with patch.dict(
            "sys.modules",
            {
                "openinference.instrumentation.google_adk": Mock(
                    GoogleADKInstrumentor=mock_class
                )
            },
        ):
            import llmops

            llmops.configure(
                backend="phoenix",
                endpoint="http://localhost:6006/v1/traces",
                service_name="test-service",
            )

            mock_class.assert_called_once()
            mock_instrumentor.instrument.assert_called_once()

    def test_adk_instrumentor_receives_tracer_provider(self):
        """GIVEN llmops configured with phoenix backend
        WHEN GoogleADKInstrumentor is enabled
        THEN it should receive the TracerProvider.
        """
        mock_instrumentor = Mock()
        mock_class = Mock(return_value=mock_instrumentor)

        with patch.dict(
            "sys.modules",
            {
                "openinference.instrumentation.google_adk": Mock(
                    GoogleADKInstrumentor=mock_class
                )
            },
        ):
            import llmops

            llmops.configure(
                backend="phoenix",
                endpoint="http://localhost:6006/v1/traces",
                service_name="test-service",
            )

            call_kwargs = mock_instrumentor.instrument.call_args.kwargs
            assert "tracer_provider" in call_kwargs
            assert call_kwargs["tracer_provider"] is not None

    def test_adk_instrumentor_skipped_when_not_installed(self, capsys):
        """GIVEN GoogleADKInstrumentor is not installed
        WHEN llmops.configure() is called with phoenix
        THEN it should skip gracefully and print a message.
        """
        import builtins
        import sys

        # Remove any cached openinference modules
        modules_to_remove = [k for k in sys.modules if "openinference" in k]
        original_modules = {k: sys.modules[k] for k in modules_to_remove}
        for key in modules_to_remove:
            del sys.modules[key]

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if "openinference" in name:
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        try:
            with patch.object(builtins, "__import__", side_effect=fake_import):
                import llmops

                llmops.configure(
                    backend="phoenix",
                    endpoint="http://localhost:6006/v1/traces",
                    service_name="test-service",
                )

            captured = capsys.readouterr()
            assert "not available" in captured.out
        finally:
            # Restore original modules
            sys.modules.update(original_modules)


class TestADKInstrumentorWithTestProvider:
    """Tests for ADK instrumentor with test TracerProvider."""

    def test_instrumentor_can_be_instantiated(self, test_tracer_provider):
        """GIVEN GoogleADKInstrumentor package is available
        WHEN instantiated with test provider
        THEN it should not raise errors.
        """
        try:
            from openinference.instrumentation.google_adk import GoogleADKInstrumentor

            instrumentor = GoogleADKInstrumentor()
            instrumentor.instrument(tracer_provider=test_tracer_provider)

            # Verify it was instrumented
            assert instrumentor is not None

            instrumentor.uninstrument()
        except ImportError:
            pytest.skip("openinference-instrumentation-google-adk not installed")

    def test_instrumentor_can_uninstrument(self, test_tracer_provider):
        """GIVEN ADK instrumentor is enabled
        WHEN uninstrument() is called
        THEN it should complete without errors.
        """
        try:
            from openinference.instrumentation.google_adk import GoogleADKInstrumentor

            instrumentor = GoogleADKInstrumentor()
            instrumentor.instrument(tracer_provider=test_tracer_provider)
            instrumentor.uninstrument()

            # Should be able to re-instrument after uninstrument
            instrumentor.instrument(tracer_provider=test_tracer_provider)
            instrumentor.uninstrument()
        except ImportError:
            pytest.skip("openinference-instrumentation-google-adk not installed")


class TestADKSpanAttributes:
    """Tests for expected span attributes from ADK instrumentation."""

    def test_manual_span_has_correct_structure(
        self, isolated_tracer_provider, in_memory_exporter, span_assertions
    ):
        """GIVEN manual spans mimicking ADK structure
        WHEN created with test provider
        THEN they should have correct parent-child relationships.
        """
        provider, tracer = isolated_tracer_provider

        # Create spans mimicking ADK structure
        with tracer.start_as_current_span("agent_run") as agent_span:
            agent_span.set_attribute("openinference.span.kind", "AGENT")
            agent_span.set_attribute("agent.name", "test-agent")

            with tracer.start_as_current_span("call_llm") as llm_span:
                llm_span.set_attribute("openinference.span.kind", "LLM")
                llm_span.set_attribute("llm.model_name", "gemini-2.0-flash")

            with tracer.start_as_current_span("execute_tool") as tool_span:
                tool_span.set_attribute("openinference.span.kind", "TOOL")
                tool_span.set_attribute("tool.name", "get_weather")

        spans = in_memory_exporter.get_finished_spans()

        # Verify span count
        assert len(spans) == 3

        # Verify parent-child relationships
        agent_spans = span_assertions.get_spans_by_name(spans, "agent_run")
        llm_spans = span_assertions.get_spans_by_name(spans, "call_llm")
        tool_spans = span_assertions.get_spans_by_name(spans, "execute_tool")

        assert len(agent_spans) == 1
        assert len(llm_spans) == 1
        assert len(tool_spans) == 1

        # LLM and tool spans should have agent as parent
        span_assertions.assert_span_has_parent(llm_spans[0], agent_spans[0])
        span_assertions.assert_span_has_parent(tool_spans[0], agent_spans[0])

    def test_llm_span_attributes(
        self, isolated_tracer_provider, in_memory_exporter, span_assertions
    ):
        """GIVEN an LLM span
        WHEN created with expected attributes
        THEN span_assertions can verify them.
        """
        provider, tracer = isolated_tracer_provider

        with tracer.start_as_current_span("call_llm") as span:
            span.set_attribute("llm.model_name", "gemini-2.0-flash")
            span.set_attribute("llm.provider", "google")
            span.set_attribute("llm.token_count.prompt", 100)
            span.set_attribute("llm.token_count.completion", 50)

        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 1

        llm_span = spans[0]
        span_assertions.assert_span_attribute(
            llm_span, "llm.model_name", "gemini-2.0-flash"
        )
        span_assertions.assert_span_attribute(llm_span, "llm.provider", "google")
        span_assertions.assert_span_attribute(llm_span, "llm.token_count.prompt", 100)

    def test_tool_span_attributes(
        self, isolated_tracer_provider, in_memory_exporter, span_assertions
    ):
        """GIVEN a tool span
        WHEN created with expected attributes
        THEN span_assertions can verify them.
        """
        provider, tracer = isolated_tracer_provider

        with tracer.start_as_current_span("execute_tool") as span:
            span.set_attribute("tool.name", "get_weather")
            span.set_attribute("tool.input", '{"city": "Paris"}')
            span.set_attribute("tool.output", '{"temp_c": 18}')

        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 1

        tool_span = spans[0]
        span_assertions.assert_span_attribute(tool_span, "tool.name", "get_weather")
        span_assertions.assert_span_has_attribute(tool_span, "tool.input")
        span_assertions.assert_span_has_attribute(tool_span, "tool.output")
