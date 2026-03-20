import logging
import os
import pathlib
import sys
from typing import Union


def setup_logger(
    level: Union[int, str] = "DEBUG", file: Union[str, pathlib.Path] = "./.logs/dev.log", save: bool = False
) -> logging.Logger:
    LOG_FORMAT = "%(asctime)s [%(levelname)s] - [%(filename)s -> %(funcName)s() -> %(lineno)s] : %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    logger = logging.getLogger()
    logger.setLevel(level)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler_format = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    stream_handler.setFormatter(stream_handler_format)

    logger.addHandler(stream_handler)

    if save:
        file = pathlib.Path(file).absolute()
        path = file.parent

        if not os.path.exists(path):
            os.mkdir(path)

        file_handler = logging.FileHandler(file)
        file_handler_format = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        file_handler.setFormatter(file_handler_format)

        logger.addHandler(file_handler)

    return logger
