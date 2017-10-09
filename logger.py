import os
import logging
import logging.handlers
import logging.config

import settings


class CustomFormatter(logging.Formatter):

    default_formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s: '
                                          '%(message)s.', '%Y-%m-%d %H:%M:%S')

    def __init__(self, formats):
        """ formats is a dict { loglevel : logformat } """
        self.formatters = {}
        datefmt = '%Y-%m-%d %H:%M:%S'
        for loglevel in formats:
            self.formatters[loglevel] = logging.Formatter(formats[loglevel], datefmt)

    def format(self, record):
        formatter = self.formatters.get(record.levelno, self.default_formatter)
        return formatter.format(record)


def setup_logger(log_file=settings.LOG_FILE,
                 level=settings.LOG_LEVEL,
                 stdout=settings.LOG_TO_STDOUT):
    handlers = []
    error_format = '%(asctime)s %(levelname)s:%(name)s: %(message)s; (%(filename)s:%(lineno)d).'
    formatter = CustomFormatter({logging.CRITICAL: error_format})
    if log_file:
        log_dir = os.path.dirname(log_file)
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        handlers.append(
            logging.handlers.RotatingFileHandler(log_file,
                                                 encoding='utf8',
                                                 maxBytes=100000000,
                                                 backupCount=5)
        )
    if stdout:
        handlers.append(logging.StreamHandler())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.propagate = False

    for h in handlers:
        h.setFormatter(formatter)
        h.setLevel(level)
        root_logger.addHandler(h)

