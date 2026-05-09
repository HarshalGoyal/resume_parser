import logging

class AppLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        
        if not self._logger.handlers:
            self._logger.setLevel(logging.DEBUG)

            handler = logging.StreamHandler()
            file_handler = logging.FileHandler('backend_app.log')
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s'
            )

            handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.addHandler(file_handler)

    def info(self, message: str):
        self._logger.info(message)

    def debug(self, message: str):
        self._logger.debug(message)

    def error(self, message: str):
        self._logger.error(message)

        
