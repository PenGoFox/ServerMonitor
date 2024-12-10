import logging

def initAndGetLogger(logfile="log.log", loglevel = logging.INFO):
    logger = logging.getLogger("logger")
    logger.setLevel(loglevel)

    logger_file_handler = logging.FileHandler(logfile)
    logger_file_handler.setLevel(loglevel)

    logger_console_handler = logging.StreamHandler()
    logger_console_handler.setLevel(loglevel)

    logger_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    logger_file_handler.setFormatter(logger_formatter)
    logger_console_handler.setFormatter(logger_formatter)

    logger.addHandler(logger_file_handler)
    logger.addHandler(logger_console_handler)

    return logger

def getLogger(logfile="log.log", loglevel = logging.INFO):
    return logging.getLogger("logger")
