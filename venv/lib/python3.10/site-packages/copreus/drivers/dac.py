from copreus.baseclasses.adriver import ADriver
from copreus.baseclasses.aspi import ASPI
from copreus.baseclasses.calibratedvalue import CalibratedValue
from copreus.schema.dac import get_schema


class DAC(ADriver, ASPI):
    """Driver for ADC (analog-digital-converter) that are connected via spi (e.g. MCP4922).

    The driver entry in the yaml file consists of:
      * ADriver entries
        * topics_sub: raw (=integer value for the dac), volt (=converted and calibrated value)
      * ASPI entries
      * CalibratedValue entries in a sub-block named 'calibration'
      * ADC own entries are
        * maxvalue: maximum value in volt. volt will be normalized towards this value.
        * bit: how many bits are used. typical values are 8, 10, and 12.
        * config_dac: configuration bit-sequence according to datasheet (0 if none)

    Example:
    driver:
        type: dac
        config_dac: 0x3000
        spi:
            pin_cs: 4
            bus: 0
            device: 1
            maxspeed: 500000
        topics-sub:
            raw: /dac/raw
            volt: /dac/volt
        maxvalue: 24
        bit: 12
        calibration:
            use-calibration: True
            values:
            # - [ref_value, raw_value]
              - [0.0, 0.0]
              - [7.23, 6.0]
              - [24, 24]
    """

    _max_value = -1  # maximum value in volt
    _config_dac = -1  # configuration bit sequence according to data sheet
    _max_raw = -1  # 2**bit - 1
    _calibrated_value = None  # copreus.baseclasses.CalibratedValue

    def __init__(self, config, mqtt_client=None, logger=None, spi_lock=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        ADriver.__init__(self, config, mqtt_client, logger, logger_name=self.__class__.__name__,
                         stdout_log_level=stdout_log_level, no_gui=no_gui,
                         manage_monitoring_agent=manage_monitoring_agent)
        ASPI.__init__(self, self._config, self._logger, spi_lock)

        self._config_dac = self._config["config_dac"]

        self._max_value = self._config["maxvalue"]
        self._max_raw = (2 ** int(self._config["bit"]))-1
        self._calibrated_value = CalibratedValue(self._logger, self._config["calibration"],
                                                 self._max_value / float(self._max_raw+1))

        self._ui_commands["write_raw"] = self._cmd_write_raw
        self._ui_commands["write_volt"] = self._cmd_write_volt

    def _cmd_write_volt(self, args):
        """write_volt float_value: write the provided float value (0-{}) to the DAC: WRITE_VOLT 123.4"""\
            .format(self._max_value)

        if len(args) != 1:
            print("wrong number of arguments. expected 'write_raw int_value'")
        else:
            try:
                value = float(args[0])
                if not (0 <= value <= self._max_value):
                    print("value {} not in range 0<=x<={}.".format(value, self._max_value))
                else:
                    raw = self._calibrated_value.raw(value)
                    self._transfer_raw(raw)
                    print("[{}] written volt value {} to dac (raw: {})".format(self._name, value, rae))
            except ValueError:
                print("argument must be a valid float. got '{}'".format(args[0]))

    def _cmd_write_raw(self, args):
        """write_raw int_value: write the provided integer value (0-{}) to the DAC: WRITE_RAW 123"""\
            .format(self._max_raw)

        if len(args) != 1:
            print("wrong number of arguments. expected 'write_raw int_value'")
        elif not args[0].isdigits():
            print("argument must be a valid integer. got '{}'".format(args[0]))
        elif not (0 <= int(args[0]) <= self._max_raw):
            print("value {} not in range 0<=x<={}.".format(int(args[0]), self._max_raw))
        else:
            value = int(args[0])
            self._transfer_raw(value)
            print("[{}] written raw value {} to dac".format(self._name, value))

    def _write_raw(self, msg):
        """on_message handler for topic sub 'raw'."""
        self._logger.info("received message '{}' on topic '{}'.".format(msg, self._topics_sub["raw"]))
        self._transfer_raw(int(msg))

    def _write_volt(self, msg):
        """on_message handler for topic sub 'volt'."""
        self._logger.info("received message '{}' on topic '{}'.".format(msg, self._topics_sub["volt"]))
        volt = float(msg)
        raw = self._calibrated_value.raw(volt)
        self._transfer_raw(raw)

    def _transfer_raw(self, raw):
        """Transfer the raw integer value (0<=value<2**bit) to the dac."""
        output = self._config_dac
        if raw > self._max_raw:
            raw = self._max_raw
        if raw < 0:
            raw = 0
        output |= raw
        buf0 = (output >> 8) & 0xff
        buf1 = output & 0xff
        self._logger.info("sending [{},{}] to dac.".format(buf0, buf1))
        self._transfer([buf0, buf1])

    def _driver_start(self):
        """ADriver._driver_start"""
        self._connect_spi()
        self._mqtt_client.subscribe(self._topics_sub["raw"], self._write_raw)
        self._mqtt_client.subscribe(self._topics_sub["volt"], self._write_volt)

    def _driver_stop(self):
        """ADriver._driver_stop"""
        self._mqtt_client.unsubscribe(self._topics_sub["raw"], self._write_raw)
        self._mqtt_client.unsubscribe(self._topics_sub["volt"], self._write_volt)
        self._disconnect_spi()

    @classmethod
    def _get_schema(cls):
        return get_schema()

    def _runtime_information(self):
        return {}

    def _config_information(self):
        return {}


def standalone():
    """Calls the static method DAC.standalone()."""
    DAC.standalone()


if __name__ == "__main__":
    DAC.standalone()
