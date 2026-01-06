import os
import logging

class BaseConfig:
    def __init__(self):
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

        logging.basicConfig(level=self.LOG_LEVEL)
        self.logger = logging.getLogger("CONFIG")
