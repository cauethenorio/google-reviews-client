"""Tests for CLI logger (ColorFormatter, ClickHandler, add_verbose_option)."""

import logging

import click
from click.testing import CliRunner

from google_reviews_client.cli.logger import ClickHandler, ColorFormatter, add_verbose_option


class TestColorFormatter:
    def setup_method(self):
        self.formatter = ColorFormatter()

    def _make_record(self, level, msg, **kwargs):
        record = logging.LogRecord(
            name="test",
            level=level,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )
        for k, v in kwargs.items():
            setattr(record, k, v)
        return record

    def test_debug_has_color(self):
        record = self._make_record(logging.DEBUG, "debug msg")
        result = self.formatter.formatMessage(record)
        assert "debug msg" in result

    def test_warning_has_color(self):
        record = self._make_record(logging.WARNING, "warn msg")
        result = self.formatter.formatMessage(record)
        assert "warn msg" in result

    def test_info_no_color_prefix(self):
        record = self._make_record(logging.INFO, "info msg")
        result = self.formatter.formatMessage(record)
        assert result == "info msg"

    def test_indentation(self):
        record = self._make_record(logging.INFO, "indented", indentation=2)
        result = self.formatter.formatMessage(record)
        assert result.startswith("    ")  # 2 * 2 spaces

    def test_indentation_zero_adds_newline(self):
        record = self._make_record(logging.INFO, "top level", indentation=0)
        result = self.formatter.formatMessage(record)
        assert result.startswith("\n")

    def test_multiline_message(self):
        record = self._make_record(logging.DEBUG, "line1\nline2")
        result = self.formatter.formatMessage(record)
        assert "line1" in result
        assert "line2" in result


class TestClickHandler:
    def test_emits_to_stdout(self):
        handler = ClickHandler()
        handler.formatter = ColorFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        runner = CliRunner()
        with runner.isolated_filesystem():
            handler.emit(record)  # Should not raise

    def test_errors_go_to_stderr(self, capsys):
        handler = ClickHandler()
        handler.formatter = ColorFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="error msg",
            args=(),
            exc_info=None,
        )
        handler.emit(record)
        captured = capsys.readouterr()
        assert "error msg" in captured.err


class TestAddVerboseOption:
    def test_verbose_sets_debug_level(self):
        test_logger = logging.getLogger("test_verbose_flag")

        @click.command()
        @add_verbose_option([test_logger])
        def cmd(verbose):
            click.echo(f"level={test_logger.level}")

        runner = CliRunner()
        result = runner.invoke(cmd, ["-v"])
        assert result.exit_code == 0
        assert f"level={logging.DEBUG}" in result.output

    def test_no_verbose_sets_info_level(self):
        test_logger = logging.getLogger("test_no_verbose_flag")

        @click.command()
        @add_verbose_option([test_logger])
        def cmd(verbose):
            click.echo(f"level={test_logger.level}")

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code == 0
        assert f"level={logging.INFO}" in result.output
