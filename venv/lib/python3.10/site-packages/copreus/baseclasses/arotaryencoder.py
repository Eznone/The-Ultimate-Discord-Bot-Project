from time import time
import RPi.GPIO as GPIO
from copreus.baseclasses.adriver import ADriver
from copreus.baseclasses.aevents import AEvents
from copreus.schema.rotaryencoder import get_schema
import enum
import collections
import pelops.ui.tools


class Direction(enum.Enum):
    NONE = 0
    LEFT = -1
    RIGHT = 1


EntryType = collections.namedtuple('EntryType', ['time', 'direction'])


class ARotaryEncoder(ADriver, AEvents):
    """Driver for rotary encoder like the KY-040 with software solutions for debouncing and direction detection.

    The driver entry in the yaml file consists of:
      * ADriver entries
        * topics_pub:
          * rotate - mqtt-translations.rotate-left and mqtt-translations.rotate-right
          * button_pressed - mqtt-translations.button_pressed
          * button_state - mqtt-translations.button_state-open and mqtt-translations.button_state-closed
      * RotaryEncoder entries
        * sw: gpio pin for pressing the rotary encoder
        * dt: dt gpio pin
        * clk: clk gpio pin

    Example:
    driver:
        type: rotaryencoder
        pin_sw:  12
        pin_dt:  16
        pin_clk: 20
        topics-pub:
            rotate: /input1/rotate
            button_pressed: /input1/button/pressed
            button_state:   /input1/button/state
        mqtt-translations:
            rotate-left: LEFT
            rotate-right: RIGHT
            button_pressed: PRESSED
            button_state-open: OPEN
            button_state-closed: CLOSED
    """

    _clk = -1  # clk gpio pin id
    _dt = -1  # dt gpio pin id
    _sw = -1  # sw gpio pin id

    _rotation_history = None  # stores the last n detected rotations

    def __init__(self, config, mqtt_client=None, logger=None, logger_name=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        ADriver.__init__(self, config, mqtt_client, logger,
                         stdout_log_level=stdout_log_level, no_gui=no_gui,
                         manage_monitoring_agent=manage_monitoring_agent)
        AEvents.__init__(self, self._config, self._logger)

        self._clk = self._config["pin_clk"]
        self._dt = self._config["pin_dt"]
        self._sw = self._config["pin_sw"]

        self._add_event(self._clk, self._callback_rotary, 1)
        self._add_event(self._sw, self._callback_sw)

        self._rotation_history = collections.deque(maxlen=25)

        self._ui_commands["button_state"] = self._cmd_button_state

    def _cmd_rotation_history(self, args):
        """rotation_history - displays the last rotation events (time + direction): ROTATION_HISTORY"""
        text = "[{}] rotation history\n".format(self._name)
        now = time()
        for entry in self._rotation_history:
            t = now - entry.time
            d = entry.direction
            text += " - {} s; {}".format(t, d.name)
        pelops.ui.tools.more(text)

    def _cmd_button_state(self, args):
        """button_state - displays if the button is closed or open: BUTTON_STATE"""
        state = GPIO.input(self._sw)
        if not state:
            print("[{}] button (gpio: {}) is closed".format(self._name, self._sw))
        else:
            print("[{}] button (gpio: {}) is open".format(self._name, self._sw))

    def _callback_sw(self, channel):
        """Event handler for gpio pin 'sw'. Publishes to the topics 'button_state' and 'button_pressed'."""
        self._logger.info("SW-event detected.")
        state = GPIO.input(self._sw)
        if not state:
            self._publish_value(self._topics_pub["button_pressed"], self._mqtt_translations["button_pressed"])
            self._publish_value(self._topics_pub["button_state"], self._mqtt_translations["button_state-closed"])
        else:
            self._publish_value(self._topics_pub["button_state"], self._mqtt_translations["button_state-open"])

    def _callback_rotary(self, channel):
        """rotation detection and publishing"""
        rotate = self._detect_rotation_direction()
        if rotate == Direction.RIGHT:
            self._publish_value(self._topics_pub["rotate"], self._mqtt_translations["rotate-right"])
            self._rotation_history.append(EntryType(time=time(), direction=rotate))
        elif rotate == Direction.LEFT:
            self._publish_value(self._topics_pub["rotate"], self._mqtt_translations["rotate-left"])
            self._rotation_history.append(EntryType(time=time(), direction=rotate))
        else:
            pass

    def _detect_rotation_direction(self):
        raise NotImplementedError

    def _driver_start(self):
        """ADriver._driver_start"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._dt, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self._sw, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self._clk, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._last_clk = GPIO.input(self._clk)
        self._register_events()

    def _driver_stop(self):
        """ADriver._driver_stop"""
        self._unregister_events()
        GPIO.cleanup(self._dt)
        GPIO.cleanup(self._sw)
        GPIO.cleanup(self._clk)

    @classmethod
    def _get_schema(cls):
        return get_schema()

    def _runtime_information(self):
        return {}

    def _config_information(self):
        return {}

