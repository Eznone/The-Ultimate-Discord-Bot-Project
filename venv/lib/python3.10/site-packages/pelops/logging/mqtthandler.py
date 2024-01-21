import logging
import json
import datetime
from pelops.logging.mylogger import get_log_level


def _get_log_level(level):
    """
    Convert the provided string to the corresponding logging level.

    :param level: string
    :return: logging level
    """
    if level.upper() == "CRITICAL":
        level = logging.CRITICAL
    elif level.upper() == "ERROR":
        level = logging.ERROR
    elif level.upper() == "WARNING":
        level = logging.WARNING
    elif level.upper() == "INFO":
        level = logging.INFO
    elif level.upper() == "DEBUG":
        level = logging.DEBUG
    else:
        raise ValueError("unknown value for logger level ('{}').".format(level))
    return level


class MQTTHandler:
    class _MQTTHandler(logging.StreamHandler):
        _topic = None
        _mqtt_client = None
        _gid = None
        _TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # time format string

        def __init__(self, topic, gid, mqtt_client):
            self._topic = topic
            self._mqtt_client = mqtt_client
            self._gid = gid
            logging.StreamHandler.__init__(self)

        def emit(self, record):
            """
            {
              "gid": "copreus-1",
              "timestamp": "1985-04-12T23:20:50.520Z",
              "level": "ERROR",
              "name": "TestLogger.SubLogger",
              "message": "ZeroDivisionError: integer division or modulo by zero"
            }
            """
            msg = self.format(record)
            message = {
                "gid": self._gid,
                "timestamp": datetime.datetime.now().strftime(self._TIME_FORMAT),
                "level": record.levelname,
                "name": record.name,
                "message": msg
            }
            self._mqtt_client.publish(self._topic, json.dumps(message))

    _logger = None
    _handler = None

    def __init__(self, topic, level, gid, mqtt_client, logger, logfilter):
        level = level.upper()
        self._logger = logger
        self._logger.info("MQTTHandler - handler init")
        self._logger.debug("MQTTHandler - level: {} / topic: {}".format(level, topic))
        self._handler = MQTTHandler._MQTTHandler(topic, gid, mqtt_client)
        self._handler.setLevel(_get_log_level(level))
        self._handler.addFilter(logfilter)

    def start(self):
        self._logger.info("MQTTHandler - handler start")
        root = logging.getLogger()
        root.addHandler(self._handler)

    def stop(self):
        root = logging.getLogger()
        root.removeHandler(self._handler)
        self._logger.info("MQTTHandler - handler stop")


class MQTTFilter(logging.Filter):
    _mqtt_logger_name = None
    _min_log_level = None

    def __init__(self, name='', mqtt_logger_name=None, min_log_level=None):
        if mqtt_logger_name is None or mqtt_logger_name=='':
            raise ValueError("mqtt_logger_name must be set")
        if min_log_level is None or min_log_level=='':
            raise ValueError("min_log_level must be set")
        self._mqtt_logger_name = mqtt_logger_name
        self._min_log_level = get_log_level(min_log_level)
        logging.Filter.__init__(self, name)

    def filter(self, record):
        if record.name.startswith(self._mqtt_logger_name):
            if record.levelno < self._min_log_level:
                return False
        return True
