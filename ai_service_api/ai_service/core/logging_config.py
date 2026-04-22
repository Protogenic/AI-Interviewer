import logging
import logging.handlers
import sys


def setup_logging():
    message_format = logging.Formatter(
        fmt="%(levelname)s | %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(message_format)

