import pelops.logging.mylogger as mylogger


class ValueRange(object):
    """Utility class that compares a value with a valid range. returns True if OK, False if failed.

    The public method is:
      * valuerange(value)
    """
    _max = None  # maximum value
    _min = None  # minimum value
    _bypass = None  # valuerange returns always true

    _logger = None
    _config = None

    def __init__(self, logger, config):
        self._config = config
        self._logger = mylogger.get_child(logger, self.__class__.__name__)
        self._logger.info("constructor")
        self._logger.debug("max: {}".format(self._config["max"]))
        self._logger.debug("min: {}".format(self._config["min"]))
        self._logger.debug("use-validation: {}".format(self._config["use-validation"]))
        self._max = self._config["max"]
        self._min = self._config["min"]
        self._bypass = not self._config["use-validation"]

    def valuerange(self, value):
        """compares a value with a valid range (min <= value <= max). returns True if OK, False if failed."""
        return self._bypass or (self._min <= value <= self._max)

    def valuerangeMessage(self, value):
        return "{} <= {} <= {}".format(self._min, value, self._max)
