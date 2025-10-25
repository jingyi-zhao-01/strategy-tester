"""Tests for the observability log module."""

import logging
from unittest.mock import MagicMock, patch

from lib.observability.log import (
    Log,
    _LoggerState,
    _shutdown_otel,
    configure_logging,
)


class TestLoggerState:
    """Test the _LoggerState class."""

    def setup_method(self):
        """Reset logger state before each test."""
        _LoggerState.set_providers(None, None)

    def test_initial_state(self):
        """Test initial state is None."""
        assert _LoggerState.get_logger() is None
        assert _LoggerState.get_otel_provider() is None

    def test_set_providers(self):
        """Test setting providers."""
        mock_logger = MagicMock()
        mock_provider = MagicMock()

        _LoggerState.set_providers(mock_logger, mock_provider)

        assert _LoggerState.get_logger() is mock_logger
        assert _LoggerState.get_otel_provider() is mock_provider

    def test_set_providers_without_otel(self):
        """Test setting providers without OTEL provider."""
        mock_logger = MagicMock()

        _LoggerState.set_providers(mock_logger)

        assert _LoggerState.get_logger() is mock_logger
        assert _LoggerState.get_otel_provider() is None


class TestConfigureLogging:
    """Test the configure_logging function."""

    @patch("lib.observability.log.OTLPLogExporter")
    @patch("lib.observability.log.BatchLogRecordProcessor")
    @patch("lib.observability.log.LoggerProvider")
    @patch("lib.observability.log.Resource")
    def test_configure_logging_with_otel(
        self, mock_resource, mock_provider_class, mock_processor, mock_exporter
    ):
        """Test configure_logging with OTEL enabled."""
        mock_logger = MagicMock()
        mock_provider_instance = MagicMock()
        mock_provider_class.return_value = mock_provider_instance

        with patch("logging.getLogger", return_value=mock_logger):
            result = configure_logging("test-service", enable_otel=True)

            assert result is mock_logger
            mock_logger.setLevel.assert_called_with(logging.INFO)
            mock_logger.addHandler.assert_called()
            mock_provider_class.assert_called_once()
            mock_provider_instance.add_log_record_processor.assert_called_once()

    def test_configure_logging_without_otel(self):
        """Test configure_logging with OTEL disabled."""
        mock_logger = MagicMock()

        with patch("logging.getLogger", return_value=mock_logger):
            result = configure_logging("test-service", enable_otel=False)

            assert result is mock_logger
            mock_logger.setLevel.assert_called_with(logging.INFO)
            mock_logger.addHandler.assert_called()

    @patch("lib.observability.log.OTLPLogExporter", side_effect=Exception("OTEL error"))
    def test_configure_logging_otel_failure(self, mock_exporter):
        """Test configure_logging handles OTEL initialization failure gracefully."""
        mock_logger = MagicMock()

        with patch("logging.getLogger", return_value=mock_logger):
            result = configure_logging("test-service", enable_otel=True)

            assert result is mock_logger
            mock_logger.warning.assert_called_with("Failed to initialize OpenTelemetry: OTEL error")

    def test_configure_logging_custom_params(self):
        """Test configure_logging with custom parameters."""
        mock_logger = MagicMock()

        with patch("logging.getLogger", return_value=mock_logger):
            result = configure_logging(
                service_name="custom-service",
                log_level=logging.DEBUG,
                enable_otel=False,
                log_format="%(levelname)s: %(message)s",
                date_format="%H:%M:%S",
            )

            assert result is mock_logger
            mock_logger.setLevel.assert_called_with(logging.DEBUG)


class TestLogClass:
    """Test the Log class methods."""

    def setup_method(self):
        """Set up test logger."""
        self.mock_logger = MagicMock()
        _LoggerState.set_providers(self.mock_logger)

    def teardown_method(self):
        """Reset logger state."""
        _LoggerState.set_providers(None, None)

    def test_info(self):
        """Test Log.info method."""
        Log.info("Test message")
        self.mock_logger.info.assert_called_with("Test message", stacklevel=2)

    def test_warn(self):
        """Test Log.warn method."""
        Log.warn("Test warning")
        self.mock_logger.warning.assert_called_with("Test warning", stacklevel=2)

    def test_error(self):
        """Test Log.error method."""
        Log.error("Test error")
        self.mock_logger.error.assert_called_with("Test error", stacklevel=2)

    def test_log_methods_with_args_kwargs(self):
        """Test Log methods with additional arguments."""
        Log.info("Test %s", "message", extra={"key": "value"})
        self.mock_logger.info.assert_called_with(
            "Test %s", "message", stacklevel=2, extra={"key": "value"}
        )

    def test_log_methods_with_no_logger(self):
        """Test Log methods when no logger is configured."""
        _LoggerState.set_providers(None)

        # These should not raise exceptions
        Log.info("Test")
        Log.warn("Test")
        Log.error("Test")


class TestShutdownOtel:
    """Test the _shutdown_otel function."""

    def test_shutdown_otel_with_provider(self):
        """Test _shutdown_otel with a provider."""
        mock_provider = MagicMock()
        _LoggerState.set_providers(None, mock_provider)

        _shutdown_otel()

        # We expect a short flush timeout during shutdown
        mock_provider.force_flush.assert_called_with(timeout_millis=1000)
        # We intentionally avoid calling shutdown() during interpreter shutdown
        mock_provider.shutdown.assert_not_called()

    def test_shutdown_otel_without_provider(self):
        """Test _shutdown_otel without a provider."""
        _LoggerState.set_providers(None, None)

        # Should not raise exception
        _shutdown_otel()

    @patch("lib.observability.log._LoggerState.get_otel_provider")
    def test_shutdown_otel_handles_exceptions(self, mock_get_provider):
        """Test _shutdown_otel handles exceptions gracefully."""
        mock_provider = MagicMock()
        mock_provider.force_flush.side_effect = Exception("Flush error")
        mock_get_provider.return_value = mock_provider

        # Should not raise exception
        _shutdown_otel()

        mock_provider.force_flush.assert_called_with(timeout_millis=1000)
        # shutdown should not be called if force_flush fails
        mock_provider.shutdown.assert_not_called()


class TestIntegration:
    """Integration tests for the observability module."""

    def test_full_logging_workflow(self):
        """Test a complete logging workflow."""
        # Configure logging with a mock logger
        mock_logger = MagicMock()
        with patch("logging.getLogger", return_value=mock_logger):
            logger = configure_logging("integration-test", enable_otel=False)

            # Verify logger is set
            assert _LoggerState.get_logger() is logger

            # Test logging methods
            Log.info("Integration test message")
            Log.warn("Integration test warning")
            Log.error("Integration test error")

            # Verify calls were made
            mock_logger.info.assert_called_with("Integration test message", stacklevel=2)
            mock_logger.warning.assert_called_with("Integration test warning", stacklevel=2)
            mock_logger.error.assert_called_with("Integration test error", stacklevel=2)

    def test_logger_propagation_disabled(self):
        """Test that the configured logger has propagation disabled."""
        logger = configure_logging("no-propagation-test", enable_otel=False)

        assert logger.propagate is False

    def test_multiple_configure_calls(self):
        """Test that multiple configure_logging calls work correctly."""
        configure_logging("service1", enable_otel=False)
        logger2 = configure_logging("service2", enable_otel=False)

        # The last call should be the current logger
        assert _LoggerState.get_logger() is logger2
        assert logger2.propagate is False
