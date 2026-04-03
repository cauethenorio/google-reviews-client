"""Click-integrated logging with color formatting."""

import logging
from typing import ClassVar

import click


class ColorFormatter(logging.Formatter):
    """Log formatter that applies click color styles to messages."""

    colors: ClassVar[dict] = {
        "DEBUG": {"fg": "blue"},
        "WARNING": {"fg": "yellow"},
        "ERROR": {"fg": "red"},
        "CRITICAL": {"fg": "red"},
    }

    def formatMessage(self, record):  # noqa: N802
        """Format the log record message with color and indentation."""
        level = record.levelname.upper()

        msg = record.getMessage()

        indentation = getattr(record, "indentation", None)
        msg = "\n".join("  " * (indentation or 0) + x for x in msg.splitlines())

        if level in self.colors:
            prefix = click.style(f"{level}: ", **self.colors[level])
            msg = "\n".join(prefix + x for x in msg.splitlines())

        if indentation == 0:
            msg = f"\n{msg}"

        return msg


class ClickHandler(logging.Handler):
    """Log handler that outputs via click.echo."""

    def emit(self, record):
        """Emit a log record via click.echo."""
        try:
            msg = self.format(record)
            is_error = record.levelname.upper() in [
                "WARNING",
                "ERROR",
                "CRITICAL",
            ]
            click.echo(msg, err=is_error)
        except Exception:  # pragma: no cover
            self.handleError(record)


_default_handler = ClickHandler()
_default_handler.formatter = ColorFormatter()


def configure_logger(logger):
    """Configure a logger to use the click handler."""
    logger.handlers = [_default_handler]
    logger.propagate = False


def add_verbose_option(loggers):
    """Add a ``--verbose`` / ``-v`` flag to the decorated click command.

    Configures each logger's level to DEBUG when the flag is set,
    or INFO otherwise.

    Args:
        loggers: Logger instances to configure.

    """
    for logger in loggers:
        configure_logger(logger)

    def decorator(f):
        def set_level(ctx, param, value):  # noqa:ARG001
            for logger in loggers:
                if value:
                    logger.setLevel(logging.DEBUG)
                else:
                    logger.setLevel(logging.INFO)

            return value

        return click.option(
            "--verbose",
            "-v",
            callback=set_level,
            is_flag=True,
            default=False,
            help="Enables verbose mode.",
        )(f)

    return decorator
