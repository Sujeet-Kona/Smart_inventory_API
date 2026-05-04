import logging


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger that prints timestamped messages to the console.
    Call this at the top of any file where you want to log events.

    Example:
        logger = get_logger("items")
        logger.info("Item created", extra={"item_id": 5})
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
