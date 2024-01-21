import RPi.GPIO as GPIO
from copreus.baseclasses.adriver import ADriver
from copreus.baseclasses.apolling import APolling
from copreus.schema.pollinginput import get_schema
from enum import Enum
import collections
import math


class PollingInput(ADriver, APolling):
    """Generic driver that polls the value of a pin and publishes a state change as soon as a new value has been
    observed long enough.

    The driver entry in the yaml file consists of:
      * ADriver entries
        * topics_pub:
          * button_pressed - mqtt-translations.button_pressed
          * button_state - mqtt-translations.button_state-open and mqtt-translations.button_state-closed
          * state_undefined - if set, a list containting the last n (defined by stability-timespan) measured values
          is published
      * APolling entries
        * topics_sub:
          * poll-now
        * poll-interval
      * PollingInput entries
        * pin: gpio pin
        * stability-timespan

    Example:
    driver:
        type: input
        pin:  21
        poll-interval: 1
        stability-timespan: 5 # for how many seconds must a new value be measured at the pin to trigger a state change
        topics-sub:
            poll-now: /test/button/pollnow
        topics-pub:
            button_pressed: /test/button/pressed
            button_state:   /test/button/state
            state_undefined: /test/button/state_undefined
        mqtt-translations:
            poll-now: True
            button_pressed: PRESSED
            button_state-open: OPEN
            button_state-closed: CLOSED

    """

    class _StateRepresentation(Enum):
        HIGH = 1
        LOW = 0
        UNDEFINED = -1

    _pin = -1  # gpio pin id
    _state = None  # virtual gpio pin value
    _history = None  # history of past measured gpio pin values
    _stability_timespan = None  # for how many seconds must a new value be measured at the pin to trigger a state change

    def __init__(self, config, mqtt_client=None, logger=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        ADriver.__init__(self, config, mqtt_client, logger, logger_name=self.__class__.__name__,
                         stdout_log_level=stdout_log_level, no_gui=no_gui,
                         manage_monitoring_agent=manage_monitoring_agent)
        APolling.__init__(self, self._config, self._mqtt_client, self._logger)

        self._pin = self._config["pin"]
        self._stability_timespan = max(self._poll_interval, self._config["stability-timespan"])

        collection_length = math.ceil(self._stability_timespan / self._poll_interval)
        self._history = collections.deque(maxlen=collection_length)

        self._ui_commands["gpio_state"] = self._cmd_gpio_state

    def _cmd_gpio_state(self, args):
        """gpio_state - displays if the gpio is closed or open: GPIO_STATE"""
        state_representation = self._get_new_state_representation()
        if state_representation == self._StateRepresentation.UNDEFINED:
            stable = False
        else:
            stable = True
        if self._state == self._StateRepresentation.LOW:
            print("[{}] gpio {} is closed (stable value: {})".format(self._name, self._pin, stable))
        else:
            print("[{}] gpio {} is open (stable value: {})".format(self._name, self._pin, stable))

    def _get_new_state_representation(self):
        if len(self._history) < self._history.maxlen:
            state_representation = self._StateRepresentation.UNDEFINED
        elif sum(self._history) == 0:
            state_representation = self._StateRepresentation.LOW
        elif sum(self._history) == self._history.maxlen:
            state_representation = self._StateRepresentation.HIGH
        else:
            state_representation = self._StateRepresentation.UNDEFINED
        return state_representation

    def _poll_device(self):
        """APolling._poll_device"""
        measured_state = int(GPIO.input(self._pin))
        self._history.append(measured_state)
        state_representation = self._get_new_state_representation()

        self._logger.debug("PollingInput._poll_device - measured state: {}, state representation: {}."
                           .format(measured_state, state_representation))

        if state_representation == self._StateRepresentation.UNDEFINED:
            # we have to wait until enough data is available
            if len(self._topics_pub["state_undefined"]) > 0:
                message = "{}".format(self._history)
                self._publish_value(self._topics_pub["state_undefined"], message)
        elif state_representation == self._state:
            # no change in state - default state
            pass
        else:
            self._state = state_representation
            self._logger.info("PollingInput._poll_device - detected state change. new state: {}.".format(self._state))
            if self._state == self._StateRepresentation.LOW:
                self._publish_value(self._topics_pub["button_pressed"], self._mqtt_translations["button_pressed"])
                self._publish_value(self._topics_pub["button_state"], self._mqtt_translations["button_state-closed"])
            else:
                self._publish_value(self._topics_pub["button_state"], self._mqtt_translations["button_state-open"])

    def _driver_start(self):
        """ADriver._driver_start"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._start_polling()

    def _driver_stop(self):
        """ADriver._driver_stop"""
        self._stop_polling()
        GPIO.cleanup(self._pin)

    @classmethod
    def _get_schema(cls):
        return get_schema()

    def _runtime_information(self):
        return {}

    def _config_information(self):
        return {}


def standalone():
    """Calls the static method Input.standalone()."""
    PollingInput.standalone()


if __name__ == "__main__":
    PollingInput.standalone()
