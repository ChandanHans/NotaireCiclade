import logging


class PrintLogger:
    """Logger that captures print statements and redirects them to logging."""

    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[
                logging.FileHandler(
                    "output.log", mode="w", encoding="utf-8"
                ),  # Log to this file with UTF-8 encoding
                logging.StreamHandler(),  # Log to console (optional, remove if not needed)
            ],
        )

    def write(self, message):
        if message.rstrip() != "":
            logging.info(message.rstrip())

    def flush(self):
        # This method is a placeholder to comply with the file-like interface.
        pass
