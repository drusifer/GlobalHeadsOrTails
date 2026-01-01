import logging

from textual.widgets import RichLog


class TextualLogHandler(logging.Handler):
    """A logging handler that writes to a Textual RichLog widget.

    Also provides emit_message() for direct progress callback usage.
    """

    def __init__(self, rich_log: RichLog):
        super().__init__()
        self.rich_log = rich_log
        self.formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s"
        )

    def emit(self, record):
        try:
            msg = self.format(record)
            # Determine style based on level
            style = ""
            if record.levelno >= logging.ERROR:
                style = "[bold red]"
            elif record.levelno >= logging.WARNING:
                style = "[yellow]"
            elif record.levelno >= logging.INFO:
                style = "[green]"
            elif record.levelno == logging.DEBUG:
                style = "[dim cyan]"

            formatted_msg = f"{style}{msg}[/]" if style else msg

            # Write to the widget (thread-safe call handled by Textual usually,
            # but if we are in a thread we might need call_from_thread.
            # However, RichLog.write is thread-safe in recent Textual versions)
            self.rich_log.write(formatted_msg)
        except Exception:
            self.handleError(record)

    def emit_message(self, message: str):
        """Direct message output for progress callbacks.

        This bypasses the logging framework and writes directly to the RichLog.
        Used by services that need a simple progress_callback(str) interface.
        """
        try:
            # Style as INFO-level progress message
            formatted_msg = f"[green]{message}[/]"
            self.rich_log.write(formatted_msg)
        except Exception:
            pass  # Silently ignore write errors for progress messages
