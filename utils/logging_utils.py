# ──────────────────────────────────────────────────────────────────────────────
# File: utils/logging_utils.py
# -----------------------------------------------------------------------------
import logging
import os

# Ensure the logs directory exists
os.makedirs("logs", exist_ok=True)

_DEF_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"


def get_logger(name: str = "lead_lab") -> logging.Logger:
    """Return a configured logger. Avoids duplicate handlers on repeated imports."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(level)

        fmt = logging.Formatter(_DEF_FORMAT)
        fh = logging.FileHandler("logs/lead_lab.log")
        ch = logging.StreamHandler()

        fh.setFormatter(fmt)
        ch.setFormatter(fmt)

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


# Module-level logger used throughout the project
log = get_logger()





# Module-level logger used across the project
log = get_logger()