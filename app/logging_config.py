import logging
import sys
from logging.handlers import RotatingFileHandler

# ── formatter ──────────────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

# ── handlers ───────────────────────────────────────────────────────────────────
file_handler = RotatingFileHandler(
    "app.log",
    maxBytes=5 * 1024 * 1024,   # 5 MB
    backupCount=3,
    encoding="utf-8",
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)   # capture everything in file

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)   # INFO+ to console

# ── root logger ────────────────────────────────────────────────────────────────
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(stream_handler)

# ── app logger ─────────────────────────────────────────────────────────────────
logger = logging.getLogger("mini-commerce")


def get_logger(name: str) -> logging.Logger:
    """Return a child logger scoped to the given module name."""
    return logging.getLogger(f"mini-commerce.{name}")
