import logging
from logging.handlers import TimedRotatingFileHandler
import os


class Logger:
    def __init__(
        self,
        log_file="optician.log",
        log_folder="logs",
        log_to_console=True,
        log_to_file=True,
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.log_file = os.path.join(log_folder, log_file)

        if self.log_to_file:
            if not os.path.exists(log_folder):
                os.makedirs(log_folder)

    def get_logger(self):
        # Check if console handler already exists
        if self.log_to_console and not any(
            isinstance(handler, logging.StreamHandler)
            for handler in self.logger.handlers
        ):
            console_formatter = logging.Formatter("%(message)s")
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        # Check if file handler already exists
        if self.log_to_file and not any(
            isinstance(handler, TimedRotatingFileHandler)
            for handler in self.logger.handlers
        ):
            file_formatter = logging.Formatter(
                "[%(asctime)s] - [%(levelname)s] - %(module)s - %(funcName)s -  %(message)s"
            )
            file_handler = TimedRotatingFileHandler(
                filename=self.log_file, when="D", interval=1, backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

        return self.logger
