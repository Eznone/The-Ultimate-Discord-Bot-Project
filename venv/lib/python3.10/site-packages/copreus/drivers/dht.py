import RPi.GPIO as GPIO
import Adafruit_DHT
from copreus.baseclasses.adriver import ADriver
from copreus.baseclasses.apolling import APolling
from copreus.baseclasses.calibratedvalue import CalibratedValue
from copreus.baseclasses.valuerange import ValueRange
from copreus.schema.dht import get_schema
from copreus.baseclasses.aevents import AEvents


class DHT(ADriver, APolling, AEvents):
    """Driver for the DHT temperature/humidity sensor family.

    The driver entry in the yaml file consists of:
      * ADriver entries
        * topics_pub: temperature, humidity
      * APolling entries
      * CalibratedValue entries in a sub-block named 'calibration_temperature'
      * CalibratedValue entries in a sub-block named 'calibration_humidity'
      * ValueRange entries in a sub-block named 'valuerange-temperature'
      * ValueRange entries in a sub-block named 'valuerange-humidity'
      * DHT entries
        * pin: gpio @ raspberry
        * sensor-type: DHT11, DHT22, AM2302

    Example:
    driver:
        type: dht
        sensor-type: DHT22
        poll-interval: 30
        pin: 26
        topics-pub:
            temperature: /dht22/temperature/raw
            humidity: /dht22/humidity/raw
        topics-sub:
            poll-now: /dht22/pollnow
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
        valuerange-humidity:
            use-validation: True
            min: 0
            max: 100
        valuerange-temperature:
            use-validation: True
            min: -10
            max: 50
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
    """

    _pin = -1  # gpio pin id
    _sensor_type = None  # sensor type (one of the values in dict _sensor_type_list)
    _sensor_type_list = {  # list of valid sensor types. the sensor-type entry in yaml must be one of the keys.
        "DHT11": Adafruit_DHT.DHT11,
        "DHT22": Adafruit_DHT.DHT22,
        "AM2302": Adafruit_DHT.AM2302,
    }
    _calibrated_t = None  # copreus.baseclasses.CalibratedValue for temperature
    _calibrated_h = None  # copreus.baseclasses.CalibratedValue for humidity
    _validate_t = None  # copreus.baseclasses.ValueRange for temperature
    _validate_h = None  # copreus.baseclasses.ValueRange for humidity
    _event_pin = None  # input pin for poll_now trigger
    _event_flank_rising = None  # trigger poll_now on rising flank
    _event_flank_falling = None  # trigger poll_now on falling flank

    def __init__(self, config, mqtt_client=None, logger=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        ADriver.__init__(self, config, mqtt_client, logger, logger_name=self.__class__.__name__,
                         stdout_log_level=stdout_log_level, no_gui=no_gui,
                         manage_monitoring_agent=manage_monitoring_agent)
        APolling.__init__(self, self._config, self._mqtt_client, self._logger)
        AEvents.__init__(self, self._config, self._logger)

        self._pin = self._config["pin"]

        if self._config["sensor-type"] not in self._sensor_type_list.keys():
            self._logger.error("Wrong parameter. Value for 'sensor-type': {} is not in list of accepted values {}.".
                               format(self._config["sensor-type"], self._sensor_type_list.keys()))
            raise ValueError("Wrong parameter. Value for 'sensor-type': {} is not in list of accepted values {}.".
                             format(self._config["sensor-type"], self._sensor_type_list.keys()))
        self._sensor_type = self._sensor_type_list[self._config["sensor-type"]]

        self._calibrated_t = CalibratedValue(self._logger, self._config["calibration-temperature"], 1)
        self._calibrated_h = CalibratedValue(self._logger, self._config["calibration-humidity"], 1)

        self._validate_t = ValueRange(self._logger, self._config["valuerange-temperature"])
        self._validate_h = ValueRange(self._logger, self._config["valuerange-humidity"])

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
                self._logger.error("DHT.__init__ - unkown value for 'event-pin.flank' entry: '{}'.".
                                   format(self._config["event-pin"]["flank"]))
                raise ValueError("DHT.__init__ - unkown value for 'event-pin.flank' entry: '{}'.".
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
        """poll - polls the current values from the [DHT11|DHT22|AM2302] and displays temperature and humidity: POLL"""
        t, h = self._get_values()
        print("[{}] temperature: {} °C (valid {}); humidity: {} % (valid {})".format(self._name, t,
                                                                                     self._validate_t.valuerange(t), h,
                                                                                     self._validate_h.valuerange(h)))

    def _callback_pin(self, channel):
        """The event pins state has changed - should poll_now be executed"""
        state = GPIO.input(self._event_pin)
        self._logger.info("DHT._callback_pin - received event. pin state: {}.".format(state))
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
        """polls the DHT and returns the calibarted temperature and humidity"""
        humidity, temperature = None, None
        while humidity is None or temperature is None:
            humidity, temperature = Adafruit_DHT.read_retry(self._sensor_type, self._pin)

        t = self._calibrated_t.value(temperature)
        h = self._calibrated_t.value(humidity)
        return t, h

    def _poll_device(self):
        """APolling._poll_device"""
        t, h = self._get_values()

        if self._validate_t.valuerange(t):
            self._publish_value(self._topics_pub["temperature"], t)
        else:
            self._logger.warning("temperature out of valid range {}".format(self._validate_t.valuerangeMessage(t)))

        if self._validate_h.valuerange(h):
            self._publish_value(self._topics_pub["humidity"], h)
        else:
            self._logger.warning("humidity out of valid range {}".format(self._validate_h.valuerangeMessage(h)))

    def _driver_start(self):
        """ADriver._driver_start"""
        self._start_polling()
        if self._event_pin:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._event_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self._register_events()

    def _driver_stop(self):
        """ADriver._driver_stop"""
        self._stop_polling()
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
    """Calls the static method DHT.standalone()."""
    DHT.standalone()


if __name__ == "__main__":
    DHT.standalone()
