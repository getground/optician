import logging


class Logger:
    def __init__(self, log_file="optician.log", log_to_console=True, log_to_file=True):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file

        self.log_file = log_file
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    def get_logger(self):
        # Check if console handler already exists
        if self.log_to_console and not any(
            isinstance(handler, logging.StreamHandler)
            for handler in self.logger.handlers
        ):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(self.formatter)
            self.logger.addHandler(console_handler)

        # Check if file handler already exists
        if self.log_to_file and not any(
            isinstance(handler, logging.FileHandler) for handler in self.logger.handlers
        ):
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(self.formatter)
            self.logger.addHandler(file_handler)

        return self.logger
