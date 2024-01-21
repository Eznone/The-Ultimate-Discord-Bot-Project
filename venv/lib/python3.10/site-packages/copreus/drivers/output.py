import RPi.GPIO as GPIO
from copreus.baseclasses.adriver import ADriver
from copreus.schema.output import get_schema


class Output(ADriver):
    """Generic driver that sets the given output pin.

    The driver entry in the yaml file consists of:
      * ADriver entries
        * topics_sub: closed - mqtt-translations.closed-true and mqtt-translations.closed-false
      * Output entries
        * pin: gpio pin
        * physical-closed: high/low - mapping between logcial states (closed/open) and physical output
        parameters (low/high)
        * initially-closed: True/False - defines if the output is opened or closed after start of driver

    Example:
    driver:
        type: output
        pin: 21
        initially-closed: True
        physical-closed: high
        topics-sub:
            closed: /test/closed
        mqtt-translations:
            closed-true: ON
            closed-false: OFF
    """

    _pin = -1  # gpio pin id
    _gpio_closed = -1  # value to write to gpio pin for closing output (0/1)
    _gpio_opened = -1  # value to write to gpio pin for opening output (0/1)
    _initially_closed = False  # should the output be opened or closed after start

    def __init__(self, config, mqtt_client=None, logger=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        ADriver.__init__(self, config, mqtt_client, logger, logger_name=self.__class__.__name__,
                         stdout_log_level=stdout_log_level, no_gui=no_gui,
                         manage_monitoring_agent=manage_monitoring_agent)

        self._pin = int(self._config["pin"])
        self._initially_closed = bool(self._config["initially-closed"])
        if str(self._config["physical-closed"].lower()) == "low":
            self._gpio_closed = 0
        elif str(self._config["physical-closed"].lower()) == "high":
            self._gpio_closed = 1
        else:
            self._logger.error("'physical-closed' - expected 'low'/'high' but received '{}'.".
                               format(self._config["physical-closed"].lower()))
            raise ValueError("'physical-closed' - expected 'low'/'high' but received '{}'.".
                             format(self._config["physical-closed"].lower()))
        self._gpio_opened = (self._gpio_closed + 1) % 2

        self._ui_commands["gpio_open"] = self._cmd_gpio_open
        self._ui_commands["gpio_close"] = self._cmd_gpio_close
        self._ui_commands["gpio_toggle"] = self._cmd_gpio_toggle
        self._ui_commands["gpio_state"] = self._cmd_gpio_state

    def _cmd_gpio_open(self, args):
        """gpio_open - opens the gpio: GPIO_OPEN"""
        GPIO.output(self._pin, self._gpio_opened)
        print("[{}] opened gpio {}.".format(self._name, self._pin))

    def _cmd_gpio_close(self, args):
        """gpio_close - closes the gpio: GPIO_CLOSE"""
        GPIO.output(self._pin, self._gpio_closed)
        print("[{}] closed gpio {}.".format(self._name, self._pin))

    def _cmd_gpio_toggle(self, args):
        """gpio_toggle - toggles the state of the gpio: GPIO_TOGGLE"""
        GPIO.output(self._pin, not GPIO.input(self._pin))
        if GPIO.input(self._pin) == self._gpio_closed:
            state = "closed"
        else:
            state = "open"
        print("[{}] toggled state of gpio {} - new state: {}".format(self._name, self._pin, state))

    def _cmd_gpio_state(self, args):
        """gpio_state - reads the state of the gpio: GPIO_STATE"""
        if GPIO.input(self._pin) == self._gpio_closed:
            state = "closed"
        else:
            state = "open"
        print("[{}] gpio {} is {}".format(self._name, self._pin, state))

    def _message_closed(self, msg):
        """on_message handler for topic sub 'closed'."""
        self._logger.info("received message '{}' on topic '{}'.".format(msg, self._topics_sub["closed"]))
        if str(msg) == str(self._mqtt_translations["closed-true"]):
            self._logger.info("writing '{}' to pin '{}'.".format(self._gpio_closed, self._pin))
            GPIO.output(self._pin, self._gpio_closed)
        elif str(msg) == str(self._mqtt_translations["closed-false"]):
            self._logger.info("writing '{}' to pin '{}'.".format(self._gpio_opened, self._pin))
            GPIO.output(self._pin, self._gpio_opened)
        else:
            raise ValueError("Output.'{}'.payload expects {} or {}. received '{}' instead.".format(
                msg.topic, self._mqtt_translations["closed-true"], self._mqtt_translations["closed-false"],
                msg))

    def _driver_start(self):
        """ADriver._driver_start"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.OUT)
        if self._initially_closed:
            GPIO.output(self._pin, self._gpio_closed)
        else:
            GPIO.output(self._pin, self._gpio_opened)
        self._mqtt_client.subscribe(self._topics_sub["closed"], self._message_closed)

    def _driver_stop(self):
        """ADriver._driver_stop"""
        self._mqtt_client.unsubscribe(self._topics_sub["closed"], self._message_closed)
        GPIO.cleanup(self._pin)

    @classmethod
    def _get_schema(cls):
        return get_schema()

    def _runtime_information(self):
        return {}

    def _config_information(self):
        return {}


def standalone():
    """Calls the static method Output.standalone()."""
    Output.standalone()


if __name__ == "__main__":
    Output.standalone()
