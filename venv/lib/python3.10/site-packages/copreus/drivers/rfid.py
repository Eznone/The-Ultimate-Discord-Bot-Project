import RPi.GPIO as GPIO
import datetime
import json
from pirc522 import RFID as PIRC522
from pelops.mythreading import LoggerThread
from copreus.baseclasses.adriver import ADriver
from copreus.baseclasses.apolling import APolling
from copreus.schema.rfid import get_schema
from threading import Lock


class RFID(ADriver, APolling):
    """Driver for the RFID_RC522 sensor with spi connectivity. /rfid/state is a json structure e.g.
    {"uid": "116:4:126:1", "present": "TRUE", "timestamp": "2009-11-10T23:00:00.0Z"}

    The driver entry in the yaml file consists of:
      * ADriver entries
      * APolling entries

    Example:
    driver:
        type: rfid
        pins:
            pin_rst: 25
            pin_irq: 13
            pin_cs: 17  # optional - only necessary if spi-bus 1 or 2
        spi:
            bus: 0
            device: 1
            maxspeed: 1000000
        topics-pub:
            uid: /rfid/uid
            present: /rfid/preset
            state: /rfid/state
        topics-sub:
            poll-now: /rfid/pollnow
            poll-forced: /rfid/pollforced
        mqtt-translations:
            present-true: TRUE
            present-false: FALSE
            poll-now: True
        poll-interval: 5
        pub-pattern: ONREAD  # ONREAD (everytime the sensor has been read), ONCHANGE (only if a new value for any field has been detected)
    """

    _rfid = None

    _pin_rst = None
    _pin_irq = None
    _pin_cs = None
    _spi_bus = None
    _spi_device = None
    _spi_speed = None

    _pub_on_change = None

    _last_state = None

    _repeat_polling = 2

    _lock_poll_method = None

    def __init__(self, config, mqtt_client=None, logger=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        ADriver.__init__(self, config, mqtt_client, logger, logger_name=self.__class__.__name__,
                         stdout_log_level=stdout_log_level, no_gui=no_gui,
                         manage_monitoring_agent=manage_monitoring_agent)
        APolling.__init__(self, self._config, self._mqtt_client, self._logger)

        self._pin_rst = self._config["pins"]["pin_rst"]
        self._pin_irq = self._config["pins"]["pin_irq"]
        try:
            self._pin_cs = self._config["pins"]["pin_cs"]
        except KeyError:
            self._pin_cs = 0

        self._spi_bus = self._config["spi"]["bus"]
        self._spi_device = self._config["spi"]["device"]
        self._spi_speed = self._config["spi"]["maxspeed"]

        self._pub_on_change = False
        if self._config["pub-pattern"] == "ONCHANGE":
            self._pub_on_change = True

        GPIO.setmode(GPIO.BCM)
        self._rfid = PIRC522(bus=self._spi_bus, device=self._spi_device, speed=self._spi_speed, pin_rst=self._pin_rst,
                             pin_ce=self._pin_cs, pin_irq=self._pin_irq, pin_mode=GPIO.BCM)

        self._last_state = self._get_state_template()
        self._last_state["uid"] = "-1"

        self._lock_poll_method = Lock()

    def _get_state_template(self):
        return {
            "uid": "",
            "present": self._mqtt_translations["present-false"].decode('UTF-8'),
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "error": None,
        }

    def _read_rfid(self):
        self._logger.info("RFID._read_rfid - start")

        result = self._get_state_template()
        (error, data) = self._rfid.request()  # Returns (False, None) if no tag is present, otherwise returns (True, tag type)

        if not error:
            if data is not None:
                self._logger.debug("RFID._read_rfid.request success. data: {}".format(data))
                (error, uid) = self._rfid.anticoll()

                if not error:
                    if uid is not None:
                        self._logger.debug("RFID._read_rfid.anticoll success.uid: {}".format(uid))
                        result["present"] = self._mqtt_translations["present-true"].decode('UTF-8')
                        result["uid"] = "{}:{}:{}:{}".format(uid[0],uid[1],uid[2],uid[3])
                        self._rfid.request() # necessary for request to work properly the next time
                    else:
                        result["error"] = "anticoll_2: {}/{}".format(error, uid)
                else:
                    result["error"] = "anticoll_1: {}/{}".format(error, uid)
            else:
                pass # no card present - expected behavior
        else:
            result["error"] = "request: {}/{}".format(error, data)

        if result["error"] is not None:
            self._logger.debug("RFID._read_rfid - result error: {}".format(result))
        else:
            self._logger.debug("RFID._read_rfid - result: {}.".format(result))
        self._logger.info("RFID._read_rfid - finished")

        return result["error"], result

    def _is_publish_candidate(self, state):
        if not self._pub_on_change:
            return True
        if state["uid"] == self._last_state["uid"] and state["present"] == self._last_state["present"]:
            self._logger.debug("RFID._publish_now - skip pub. no change detected.")
            return False
        return True

    def _publish(self, state):
        self._logger.info("RFID._publish state:{}".format(state))
        self._publish_value(self._topics_pub["state"], json.dumps(state))
        self._publish_value(self._topics_pub["uid"], state["uid"])
        self._publish_value(self._topics_pub["present"], state["present"])
        self._last_state = state

    def _poll_device(self, override_onread=False):
        """APolling._poll_device"""
        self._logger.info("RFID._poll_device - enter")

        with self._lock_poll_method:
            self._logger.info("RFID._poll_device - lock acquired")
            errors = []
            for i in range(self._repeat_polling):
                error, result = self._read_rfid()
                errors.append(error)
                if error is None:
                    break

            if error is not None:
                #  self._logger.error("RFID._poll_device - rfid sensor produced repeated errors: {}".format(errors))
                pass  # since request produce junk if no card is present ... 

            if self._is_publish_candidate(result) or override_onread:
                self._publish(result)

        self._logger.info("RFID._poll_device - finished")

    def _pollforced_handler(self, message):
        message =  message.decode("UTF-8")
        self._logger.info("RFID._pollforced received: {}".format(message))
        if message == self._mqtt_translations["poll-now"].decode("UTF-8"):
            self._poll_device(override_onread=True)
        else:
            self._logger.warning("RFID._pollforced unknown message command '{}'. excpected: '{}'".format(message, self._mqtt_translations["poll-now"].decode("UTF-8")))

    def _driver_start(self):
        """ADriver._driver_start"""
        self._start_polling()
        self._logger.info("RDIF._driver_start - subscribing to topic {}.".format(self._topics_sub["poll-forced"]))
        self._mqtt_client.subscribe(self._topics_sub["poll-forced"], self._pollforced_handler)

    def _driver_stop(self):
        """ADriver._driver_stop"""
        self._stop_polling()
        self._logger.info("RDIF._driver_start - unsubscribing from topic {}.".format(self._topics_sub["poll-forced"]))
        self._mqtt_client.unsubscribe(self._topics_sub["poll-forced"], self._pollforced_handler)
        # self._rfid.cleanup() - this method calls GPIO.cleanup() -> would make troubles for all other drivers!

    @classmethod
    def _get_schema(cls):
        return get_schema()

    def _runtime_information(self):
        return {}

    def _config_information(self):
        return {}
