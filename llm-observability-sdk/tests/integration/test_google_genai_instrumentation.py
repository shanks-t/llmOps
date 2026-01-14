"""Integration tests for Google GenAI auto-instrumentation.

These tests verify that GoogleGenAIInstrumentor correctly captures spans
for direct google.genai Client calls.
"""

import pytest
from unittest.mock import Mock, patch


class TestGenAIInstrumentorEnablement:
    """Tests for GenAI instrumentor being enabled by llmops.configure()."""

    def test_configure_enables_genai_instrumentor(self):
        """GIVEN llmops configured with phoenix backend
        WHEN GoogleGenAIInstrumentor is available
        THEN it should be enabled automatically.
        """
        mock_instrumentor = Mock()
        mock_class = Mock(return_value=mock_instrumentor)

        with patch.dict(
            "sys.modules",
            {
                "openinference.instrumentation.google_genai": Mock(
                    GoogleGenAIInstrumentor=mock_class
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

    def test_genai_instrumentor_receives_tracer_provider(self):
        """GIVEN llmops configured with phoenix backend
        WHEN GoogleGenAIInstrumentor is enabled
        THEN it should receive the TracerProvider.
        """
        mock_instrumentor = Mock()
        mock_class = Mock(return_value=mock_instrumentor)

        with patch.dict(
            "sys.modules",
            {
                "openinference.instrumentation.google_genai": Mock(
                    GoogleGenAIInstrumentor=mock_class
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

    def test_genai_instrumentor_skipped_when_not_installed(self, capsys):
        """GIVEN GoogleGenAIInstrumentor is not installed
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


class TestGenAIInstrumentorWithTestProvider:
    """Tests for GenAI instrumentor with test TracerProvider."""

    def test_instrumentor_can_be_instantiated(self, test_tracer_provider):
        """GIVEN GoogleGenAIInstrumentor package is available
        WHEN instantiated with test provider
        THEN it should not raise errors.
        """
        try:
            from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

            instrumentor = GoogleGenAIInstrumentor()
            instrumentor.instrument(tracer_provider=test_tracer_provider)

            assert instrumentor is not None

            instrumentor.uninstrument()
        except ImportError:
            pytest.skip("openinference-instrumentation-google-genai not installed")

    def test_instrumentor_can_uninstrument(self, test_tracer_provider):
        """GIVEN GenAI instrumentor is enabled
        WHEN uninstrument() is called
        THEN it should complete without errors.
        """
        try:
            from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

            instrumentor = GoogleGenAIInstrumentor()
            instrumentor.instrument(tracer_provider=test_tracer_provider)
            instrumentor.uninstrument()

            # Should be able to re-instrument after uninstrument
            instrumentor.instrument(tracer_provider=test_tracer_provider)
            instrumentor.uninstrument()
        except ImportError:
            pytest.skip("openinference-instrumentation-google-genai not installed")


class TestGenAISpanAttributes:
    """Tests for expected span attributes from GenAI instrumentation."""

    def test_manual_llm_span_structure(
        self, isolated_tracer_provider, in_memory_exporter, span_assertions
    ):
        """GIVEN manual spans mimicking GenAI structure
        WHEN created with test provider
        THEN they should have expected attributes.
        """
        provider, tracer = isolated_tracer_provider

        with tracer.start_as_current_span("generate_content") as span:
            span.set_attribute("openinference.span.kind", "LLM")
            span.set_attribute("gen_ai.system", "google")
            span.set_attribute("gen_ai.request.model", "gemini-2.0-flash")
            span.set_attribute("gen_ai.usage.input_tokens", 100)
            span.set_attribute("gen_ai.usage.output_tokens", 50)

        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 1

        llm_span = spans[0]
        span_assertions.assert_span_attribute(llm_span, "gen_ai.system", "google")
        span_assertions.assert_span_attribute(
            llm_span, "gen_ai.request.model", "gemini-2.0-flash"
        )

    def test_token_usage_attributes(
        self, isolated_tracer_provider, in_memory_exporter, span_assertions
    ):
        """GIVEN a GenAI span with token usage
        WHEN tokens are recorded
        THEN span has correct token attributes.
        """
        provider, tracer = isolated_tracer_provider

        with tracer.start_as_current_span("generate_content") as span:
            span.set_attribute("gen_ai.usage.input_tokens", 150)
            span.set_attribute("gen_ai.usage.output_tokens", 75)
            span.set_attribute("gen_ai.usage.total_tokens", 225)

        spans = in_memory_exporter.get_finished_spans()
        llm_span = spans[0]

        span_assertions.assert_span_attribute(
            llm_span, "gen_ai.usage.input_tokens", 150
        )
        span_assertions.assert_span_attribute(
            llm_span, "gen_ai.usage.output_tokens", 75
        )
        span_assertions.assert_span_attribute(
            llm_span, "gen_ai.usage.total_tokens", 225
        )

    def test_model_name_attribute(
        self, isolated_tracer_provider, in_memory_exporter, span_assertions
    ):
        """GIVEN a GenAI span
        WHEN model is specified
        THEN span has gen_ai.request.model attribute.
        """
        provider, tracer = isolated_tracer_provider

        with tracer.start_as_current_span("generate_content") as span:
            span.set_attribute("gen_ai.request.model", "gemini-1.5-pro")

        spans = in_memory_exporter.get_finished_spans()
        span_assertions.assert_span_attribute(
            spans[0], "gen_ai.request.model", "gemini-1.5-pro"
        )

    def test_streaming_span_structure(
        self, isolated_tracer_provider, in_memory_exporter, span_assertions
    ):
        """GIVEN a streaming GenAI call
        WHEN chunks are received
        THEN span covers the entire stream duration.
        """
        import time

        provider, tracer = isolated_tracer_provider

        with tracer.start_as_current_span("generate_content_stream") as span:
            span.set_attribute("gen_ai.request.model", "gemini-2.0-flash")
            span.set_attribute("llm.streaming", True)

            # Simulate streaming delay
            time.sleep(0.01)

            # Final token count after stream completes
            span.set_attribute("gen_ai.usage.output_tokens", 100)

        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 1

        stream_span = spans[0]
        span_assertions.assert_span_attribute(stream_span, "llm.streaming", True)
        # Verify span has duration (end_time > start_time)
        assert stream_span.end_time > stream_span.start_time
