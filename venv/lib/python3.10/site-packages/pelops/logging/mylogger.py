import sys
import logging
import logging.handlers

# set of scripts to simplify usage of logger

def get_level_name(level):
    """
    Convert the provided string to the corresponding logging level.

    :param level: int
    :return: logging name
    """
    if level == logging.CRITICAL:
        name = "CRITICAL"
    elif level == logging.ERROR:
        name = "ERROR"
    elif level == logging.WARNING:
        name = "WARNING"
    elif level == logging.INFO:
        name = "INFO"
    elif level == logging.DEBUG:
        name = "DEBUG"
    elif level == logging.NOTSET:
        name = "NOTSET"
    else:
        raise ValueError("unknown value for logger level ('{}').".format(level))
    return name


def get_log_level(name):
    """
    Convert the provided string to the corresponding logging level.

    :param name: string
    :return: logging level
    """
    if name.upper() == "CRITICAL":
        level = logging.CRITICAL
    elif name.upper() == "ERROR":
        level = logging.ERROR
    elif name.upper() == "WARNING":
        level = logging.WARNING
    elif name.upper() == "INFO":
        level = logging.INFO
    elif name.upper() == "DEBUG":
        level = logging.DEBUG
    elif name.upper() == "NOTSET":
        level = logging.NOTSET
    else:
        raise ValueError("unknown value for logger level ('{}').".format(name))
    return level


def get_child(logger, logger_name, config=None):
    """
    Create a child logger and optionally apply a different log level

    :param logger: logger instance
    :param logger_name: name for the child logger
    :param config: config yaml structure with at least an "log-level" entry.
    :return:
    """
    child = logger.getChild(logger_name)
    if config is not None:
        try:
            log_level = config["log-level"]
            level = get_log_level(log_level)
            child.setLevel(level)
        except KeyError:
            pass
    return child


def create_logger(config, logger_name):
    """
    Create an logger instance with the provided log level and target file.

    :param config: config yaml structure with at least "log-level" and "log-file" as entries
    :param logger_name: name for the logger to be created
    :return: logger instance
    """
    log_level = config["log-level"]
    level = get_log_level(log_level)

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    root = logging.getLogger()
    if not len(root.handlers):
        try:
            max_bytes = int(config["log-rotation"]["maxbytes"])
            backup_count = int(config["log-rotation"]["backupcount"])
            handler = logging.handlers.RotatingFileHandler(config["log-file"], maxBytes=max_bytes, backupCount=backup_count)
        except KeyError:
            handler = logging.FileHandler(config["log-file"])
        handler.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        root.addHandler(handler)

    return logger


def add_log2stdout_handler(level):
    """
    add a handler to the logger that outputs to the console.

    :param logger: logger instance
    :param level: level in string
    :return:
    """

    if level is not None and level != "":
        log_level = get_log_level(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.addHandler(handler)



