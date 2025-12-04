"""Logging configuration for the RAG pipeline."""

import logging
import sys


def setup_logger(name: str = "rag_chat") -> logging.Logger:
    """
    Configure and return a logger instance.

    Parameters
    ----------
    name : str
        Logger name identifier.

    Returns
    -------
    logging.Logger
        Configured logger with console output.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()
