import pelops.logging.mylogger as mylogger
from enum import Enum


class _CalibrationMethod(Enum):
    NO = 0,
    OFFSET = 1,
    TWO_POINTS = 2,


class CalibratedValue(object):
    """Utility class that takes a value returns a calibrated value.

    Two calibration methods are implemented:
      0. the list calibration_data is empty - the value is returned unchanged.
      1. the list contains exactly one pair - the value is applied with the resulting offset.
      2. the list contains several pairs - the two neighboring (left and right) pairs are selected and the value
      accordingly changed and returned. (this needs an ordered list)

    Additionally a conversion factor can be provided. For example, when using an 12bit DAC for a voltage range of 0-24V
    the conversion factor is 2**12 steps / 24 V = 170.6 steps/V.

    There are two public methods:
      * value(raw) - use it to calibrate measurements. E.g. ADC
      * raw(value) - use it to convert a set point to the value for the device. E.g. DAC
    """
    _calibration_data = None  # ordered list of tuples [[ref_value, raw_value], ...]
    _conversion_factor = -1  # conversion factor
    _method = 0  # internal flag [0,1,2] - is set in __init__ and stores which calibration method should be used
    _offset_value = -1  # internal variable - stores pre-calculated offset for method 1

    _col_ref = 0  # position of reference value in tuple
    _col_raw = 1  # position of raw value in tuple

    _logger = None
    _config = None

    def __init__(self, logger, config, conversion_factor=1):
        self._config = config
        self._logger = mylogger.get_child(logger, self.__class__.__name__)
        self._logger.info("constructor")
        self._logger.debug("calibration_data: ".format(self._config["values"]))
        self._logger.debug("conversion_factor: ".format(conversion_factor))

        self._conversion_factor = conversion_factor
        self._calibration_data = self._config["values"]  # [[ref_value, raw_value], ...]

        if self._calibration_data is None or len(self._calibration_data) <= 0:
            self._method = _CalibrationMethod.NO
        elif len(self._calibration_data) == 1:
            self._method = _CalibrationMethod.OFFSET
            self._offset_value = self._calibration_data[0][self._col_raw] - self._calibration_data[0][self._col_ref]
        else:
            self._method = _CalibrationMethod.TWO_POINTS

        if not self._config["use-calibration"]:
            self._method = _CalibrationMethod.NO

        self._logger.info("method is set to: ".format(self._method))

    def _corrected(self, value, flip=False):
        """Returns the corrected value. Invokes the correction method according to _method.

        flip is used to change correction direction:
          * False: raw->value
          * True: value->raw"""
        if self._method == _CalibrationMethod.NO:
            value = self._no_calib(value)
        elif self._method == _CalibrationMethod.OFFSET:
            value = self._offset(value, flip)
        elif self._method == _CalibrationMethod.TWO_POINTS:
            value = self._two_points(value, flip)
        else:
            self._logger.error("don't know what to do with method id = {}.".format(self._method))
            raise ValueError("don't know what to do with method id = {}.".format(self._method))
        return value

    def _no_calib(self, value):
        """returns the unchanged value"""
        return value

    def _offset(self, value, flip):
        """Add/substract _offset_value"""
        if flip:
            value -= self._offset_value
        else:
            value += self._offset_value
        return value

    def _two_points(self, value, flip):
        """Select the surrounding calibration data points and interpolate the calibration value."""
        if flip:
            cref = self._col_raw
            craw = self._col_ref
        else:
            craw = self._col_raw
            cref = self._col_ref

        pos = 1
        while pos < len(self._calibration_data)-1:
            if value <= self._calibration_data[pos][craw]:
                break
            pos = pos + 1

        reflow = self._calibration_data[pos - 1][cref]
        rawlow = self._calibration_data[pos - 1][craw]
        refhigh = self._calibration_data[pos][cref]
        rawhigh = self._calibration_data[pos][craw]

        refrange = refhigh - reflow
        rawrange = rawhigh - rawlow
        corrected = (((value - rawlow) * refrange) / rawrange) + reflow
        return corrected

    def value(self, raw):
        """Convert raw measurements into calibrated values. If use_calibration is set to False the unchanged raw value
        is returned (for calibration/testing)."""
        value = raw * self._conversion_factor
        value = self._corrected(value, False)
        return value

    def raw(self, value):
        """Convert raw measurements into calibrated values. If use_calibration is set to False the unchanged raw value
        is returned (for calibration/testing)."""
        value = self._corrected(value, True)
        raw = value / self._conversion_factor
        return int(raw)
