import RPi.GPIO as GPIO
import bme280 as bme280_driver  # https://pypi.python.org/pypi/RPi.bme280
from smbus2 import SMBus  # https://pypi.python.org/pypi/smbus2/0.2.0
from copreus.baseclasses.adriver import ADriver
from copreus.baseclasses.apolling import APolling
from copreus.baseclasses.ai2c import AI2C
from copreus.baseclasses.calibratedvalue import CalibratedValue
from copreus.baseclasses.valuerange import ValueRange
from copreus.schema.bme_280 import get_schema
from copreus.baseclasses.aevents import AEvents


class BME_280(ADriver, APolling, AEvents, AI2C):
    # BME280 would result in a name conflict with the above imported driver ...
    """Driver for the BME280 sensor (temperature, humidity, and pressure) with i2c connectivity.

    The driver entry in the yaml file consists of:
      * ADriver entries
        * topics_pub: temperature, humidity, pressure
      * APolling entries
      * i2c entries:
        * port: i2c port
        * address: i2c address
      * CalibratedValue entries in a sub-block named 'calibration_temperature'
      * CalibratedValue entries in a sub-block named 'calibration_humidity'
      * CalibratedValue entries in a sub-block named 'calibration_pressure'
      * ValueRange entries in a sub-block named 'valuerange-temperature'
      * ValueRange entries in a sub-block named 'valuerange-humidity'
      * ValueRange entries in a sub-block named 'valuerange-pressure'

    Example:
    driver:
        poll-interval: 30
        type: bme_280
        port: 1
        address: 0x76
        topics-pub:
            temperature: /bme280/temperature/raw
            humidity: /bme280/humidity/raw
            pressure: /bme280/pressure/raw
        topics-sub:
            poll-now: /bme280/pollnow
        mqtt-translations:
            poll-now: True
        calibration-temperature:
            use-calibration: True
            values:
            # - [ref_value, raw_value]
        calibration-humidity:
            use-calibration: True
            values:
            # - [ref_value, raw_value]
        calibration-pressure:
            use-calibration: True
            values:
            # - [ref_value, raw_value]
        valuerange-humidity:
            use-validation: True
            min: 0
            max: 100
        valuerange-temperature:
            use-validation: True
            min: -10
            max: 50
        valuerange-pressure:
            use-validation: True
            min: 900
            max: 1100
        event-pin:  # trigger for poll_now (optional)
            pin: 21
            flank: falling  # [falling, rising, both]
            topics-pub:  # optional
                button_pressed: /test/button/pressed
                button_state:   /test/button/state
            mqtt-translations:  # optional
                button_pressed: PRESSED
                button_state-open: OPEN
                button_state-closed: CLOSED

    Note: this class is named BME_280 due to a name conflict with the used Adafruit driver named bme280.
    """

    _port = -1  # i2c port
    _address = -1  # i2c address
    _bus = None  # SMBus instance
    _calibrated_t = None  # copreus.baseclasses.CalibratedValue for temperature
    _calibrated_h = None  # copreus.baseclasses.CalibratedValue for humidity
    _calibrated_p = None  # copreus.baseclasses.CalibratedValue for airpressure
    _valuerange_t = None  # copreus.baseclasses.ValueRange for temperature
    _valuerange_h = None  # copreus.baseclasses.ValueRange for humidity
    _valuerange_p = None  # copreus.baseclasses.ValueRange for airpressure
    _event_pin = None  # input pin for poll_now trigger
    _event_flank_rising = None  # trigger poll_now on rising flank
    _event_flank_falling = None  # trigger poll_now on falling flank

    def __init__(self, config, mqtt_client=None, logger=None, i2c_lock=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        ADriver.__init__(self, config, mqtt_client, logger, logger_name=self.__class__.__name__,
                         stdout_log_level=stdout_log_level, no_gui=no_gui,
                         manage_monitoring_agent=manage_monitoring_agent)
        APolling.__init__(self, self._config, self._mqtt_client, self._logger)
        AEvents.__init__(self, self._config, self._logger)
        AI2C.__init__(self, i2c_lock)

        self._port = self._config["port"]
        self._address = self._config["address"]

        self._calibrated_t = CalibratedValue(self._logger, self._config["calibration-temperature"], 1)
        self._calibrated_h = CalibratedValue(self._logger, self._config["calibration-humidity"], 1)
        self._calibrated_p = CalibratedValue(self._logger, self._config["calibration-pressure"], 1)

        self._valuerange_t = ValueRange(self._logger, self._config["valuerange-temperature"])
        self._valuerange_h = ValueRange(self._logger, self._config["valuerange-humidity"])
        self._valuerange_p = ValueRange(self._logger, self._config["valuerange-pressure"])

        self._ui_commands["poll"] = self._cmd_poll

        try:
            self._event_pin = self._config["event-pin"]["pin"]
            if self._config["event-pin"]["flank"] == "rising":
                self._event_flank_rising = True
                self._event_flank_falling = False
            elif self._config["event-pin"]["flank"] == "falling":
                self._event_flank_rising = False
                self._event_flank_falling = True
            elif self._config["event-pin"]["flank"] == "both":
                self._event_flank_rising = True
                self._event_flank_falling = True
            else:
                self._logger.error("BME_280.__init__ - unkown value for 'event-pin.flank' entry: '{}'.".
                                   format(self._config["event-pin"]["flank"]))
                raise ValueError("BME_280.__init__ - unkown value for 'event-pin.flank' entry: '{}'.".
                                 format(self._config["event-pin"]["flank"]))
            # assign both dicts for a variable before calling init methods - this ensures that either both are present
            # or both are missing
            topics_pub = self._config["event-pin"]["topics-pub"]
            mqtt_translations = self._config["event-pin"]["mqtt-translations"]
            self._add_topics_pub(topics_pub)
            self._add_mqtt_translations(mqtt_translations)
            self._add_event(self._event_pin, self._callback_pin)
        except KeyError:
            pass

    def _cmd_poll(self, args):
        """poll - polls the current values from the bme280 and outputs them (temperature, humidity, pressure): POLL"""
        t, h, p = self._get_values()
        print("[{}] temperature: {} °C, humidity: {} %, pressure: {} hPa".format(self._name, t, h, p))
        print("[{}] temperature: {} °C (valid {}); humidity: {} % (valid {}), pressure: {} hPa (valid {})"
              .format(self._name, t, self._valuerange_t.valuerange(t), h, self._valuerange_h.valuerange(h),
                      p, self._valuerange_p.valuerange(p)))

    def _callback_pin(self, channel):
        """The event pins state has changed - should poll_now be executed"""
        state = GPIO.input(self._event_pin)
        self._logger.info("BME_280._callback_pin - received event. pin state: {}.".format(state))
        if not state:
            if self._event_flank_rising:
                self.poll_now()
            self._publish_value(self._topics_pub["button_pressed"], self._mqtt_translations["button_pressed"])
            self._publish_value(self._topics_pub["button_state"], self._mqtt_translations["button_state-closed"])
        else:
            if self._event_flank_falling:
                self.poll_now()
            self._publish_value(self._topics_pub["button_state"], self._mqtt_translations["button_state-open"])

    def _get_values(self):
        """polls the bme280 and returns the calibrated temperature, humidity, and pressure"""
        with self._i2c_lock:
            data = bme280_driver.sample(self._bus, self._address)

        t = self._calibrated_t.value(data.temperature)
        h = self._calibrated_t.value(data.humidity)
        p = self._calibrated_t.value(data.pressure)

        return t, h, p

    def _poll_device(self):
        """APolling._poll_device"""
        t, h, p = self._get_values()

        if self._valuerange_t.valuerange(t):
            self._publish_value(self._topics_pub["temperature"], t)
        else:
            self._logger.warning("temperature out of valid range {}".format(self._valuerange_t.valuerangeMessage(t)))

        if self._valuerange_h.valuerange(h):
            self._publish_value(self._topics_pub["humidity"], h)
        else:
            self._logger.warning("humidity out of valid range {}".format(self._valuerange_h.valuerangeMessage(h)))

        if self._valuerange_p.valuerange(p):
            self._publish_value(self._topics_pub["pressure"], p)
        else:
            self._logger.warning("pressure out of valid range {}".format(self._valuerange_p.valuerangeMessage(p)))

    def _driver_start(self):
        """ADriver._driver_start"""
        self._bus = SMBus(self._port)
        bme280_driver.load_calibration_params(self._bus, self._address)
        self._start_polling()
        if self._event_pin:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._event_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self._register_events()

    def _driver_stop(self):
        """ADriver._driver_stop"""
        self._stop_polling()
        self._bus.close()
        if self._event_pin:
            self._unregister_events()
            GPIO.cleanup(self._event_pin)

    @classmethod
    def _get_schema(cls):
        return get_schema()

    def _runtime_information(self):
        return {}

    def _config_information(self):
        return {}


def standalone():
    """Calls the static method BME_280.standalone()."""
    BME_280.standalone()


if __name__ == "__main__":
    BME_280.standalone()
