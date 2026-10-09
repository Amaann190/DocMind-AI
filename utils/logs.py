import logging
import sys


def setup_logger(log_file: str | None = None, level: int | str = logging.INFO):
    """Log to stdout; optionally add a file when the caller requests one."""
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    logger.propagate = False
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(module)s - %(levelname)s - %(message)s"
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)
    if log_file:
        try:
            handler = logging.FileHandler(log_file)
        except OSError:
            logger.warning("Cannot open the requested log file; logging to stdout only.")
        else:
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    return logger


log = setup_logger()
