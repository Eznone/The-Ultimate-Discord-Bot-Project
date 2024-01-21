import RPi.GPIO as GPIO
from copreus.baseclasses.adriver import ADriver
from copreus.schema.rgbled import get_schema
import json
import jsonschema
from enum import Enum
from asyncscheduler import AsyncScheduler
from pelops.ui.tools import parse

message_rgb_schema = {
    "type": "object",
    "description": "rgb boolean",
    "properties": {
        "r": {
            "description": "red",
            "type": "boolean"
        },
        "g": {
            "description": "green",
            "type": "boolean"
        },
        "b": {
            "description": "blue",
            "type": "boolean"
        }
    },
    "required": ["r", "g", "b"],
    "additionalItems": False
}


message_color_schema = {
    "type": "object",
    "description": "rgb color name",
    "properties": {
        "color": {
            "description": "color",
            "type": "string",
            "enum": ["BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "AQUA", "MAGENTA"]
        }
    },
    "required": ["color"],
    "additionalItems": False
}


message_blink_symmetric_schema = {
    "type": "object",
    "description": "alternate between two color names with equal delays",
    "properties": {
        "color_a": {
            "description": "color a",
            "type": "string",
            "enum": ["BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "AQUA", "MAGENTA"]
        },
        "color_b": {
            "description": "color b",
            "type": "string",
            "enum": ["BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "AQUA", "MAGENTA"]
        },
        "delay": {
            "description": "delay after activating each color in seconds",
            "type": "number"
        }
    },
    "required": ["color_a", "color_b", "delay"],
    "additionalItems": False
}


message_blink_asymmetric_schema = {
    "type": "object",
    "description": "alternate between two color names with two different delays",
    "properties": {
        "color_a": {
            "description": "color a",
            "type": "string",
            "enum": ["BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "AQUA", "MAGENTA"]
        },
        "color_b": {
            "description": "color b",
            "type": "string",
            "enum": ["BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "AQUA", "MAGENTA"]
        },
        "delay_a": {
            "description": "delay after activating color a in seconds",
            "type": "number"
        },
        "delay_b": {
            "description": "delay after activating color b in seconds",
            "type": "number"
        }
    },
    "required": ["color_a", "color_b", "delay_a", "delay_b"],
    "additionalItems": False
}


message_schema = {
    "definitions": {},
    "$schema": "http://json-schema.org/draft-06/schema#",
    "oneOf": [
            message_rgb_schema,
            message_color_schema,
            message_blink_symmetric_schema,
            message_blink_asymmetric_schema
    ],
    "additionalItems": False
}


class Color(Enum):
    BLACK = {"r": False, "g": False, "b": False}
    WHITE = {"r": True, "g": True, "b": True}
    RED = {"r": True, "g": False, "b": False}
    GREEN = {"r": False, "g": True, "b": False}
    BLUE = {"r": False, "g": False, "b": True}
    YELLOW = {"r": True, "g": True, "b": False}
    AQUA = {"r": False, "g": True, "b": True}
    MAGENTA = {"r": True, "g": False, "b": True}


class ALEDDriver:
    _logger = None
    _set_pins = None
    _scheduler = None

    def __init__(self, set_pins, logger, scheduler, struct):
        self._logger = logger
        self._scheduler = scheduler
        self._set_pins = set_pins
        self._process_struct(struct)

    def _process_struct(self, struct):
        raise NotImplementedError()

    def display(self):
        self._scheduler.clear_scheduler()
        try:
            self._scheduler.stop()
        except AttributeError:
            # expected exception - AsyncScheduler expects to be running when stop is being called.
            # TODO - update AsyncScheduler implementation 
            pass
        self._display()

    def _display(self):
        raise NotImplementedError()


class StaticColor(ALEDDriver):
    _color = None

    def _process_struct(self, struct):
        self._color = Color[struct["color"]]

    def _display(self):
        self._logger.info("StaticColor.setting color '{}'".format(self._color))
        self._set_pins(self._color.value["r"], self._color.value["g"], self._color.value["b"])


class StaticRGB(ALEDDriver):
    _rgb = None

    def _process_struct(self, struct):
        self._rgb = struct

    def _display(self):
        self._logger.info("StaticRGB.setting rgb '{}'".format(self._rgb))
        self._set_pins(self._rgb["r"], self._rgb["g"], self._rgb["b"])


class BlinkColorsAsymmetric(ALEDDriver):
    _color_a = None
    _color_b = None
    _delay_a = None
    _delay_b = None

    def _process_struct(self, data):
        self._color_a = Color[data["color_a"]]
        self._color_b = Color[data["color_b"]]
        self._delay_a = data["delay_a"]
        self._delay_b = data["delay_b"]

    def _display_color(self, color):
        self._logger.info("BlinkColors._display_color color '{}'".format(color))
        self._set_pins(color.value["r"], color.value["g"], color.value["b"])

    def _add_repeat_color(self, delay, color):
        self._logger.info("BlinkColors._add_repeat_color - add repeat {} for color {} to scheduler.".format(delay, color))
        self._scheduler.repeat(delay, 1, self._display_color, (color,))

    def _display(self):
        delay = self._delay_a + self._delay_b
        self._scheduler.enter(0, 1, self._add_repeat_color, (delay, self._color_a))
        self._scheduler.enter(self._delay_a, 1, self._add_repeat_color, (delay, self._color_b))
        self._display_color(self._color_b)
        self._scheduler.start()


class BlinkColorsSymmetric(BlinkColorsAsymmetric):
    def _process_struct(self, data):
        self._color_a = Color[data["color_a"]]
        self._color_b = Color[data["color_b"]]
        self._delay_a = data["delay"]
        self._delay_b = data["delay"]


class LEDDriverFactory:
    @staticmethod
    def create(set_pins, logger, scheduler, struct):
        if "delay" in struct:
            driver = BlinkColorsSymmetric(set_pins, logger, scheduler, struct)
        elif "delay_a" in struct:
            driver = BlinkColorsAsymmetric(set_pins, logger, scheduler, struct)
        elif "color" in struct:
            driver = StaticColor(set_pins, logger, scheduler, struct)
        elif "r" in struct:
            driver = StaticRGB(set_pins, logger, scheduler, struct)
        else:
            raise ValueError("LEDDriverFactory.create - dont know how to handle struct '{}'".format(struct))
        return driver


class RGBLed(ADriver):
    """Generic driver that sets the given output pin.

    The driver entry in the yaml file consists of:
      * ADriver entries
        * topics_sub: closed - mqtt-translations.closed-true and mqtt-translations.closed-false
      * Output entries
        * pin-red/pin-green/pin-blue: gpio pin
        * physical-closed: high/low - mapping between logcial states (closed/open) and physical output
        parameters (low/high)
        * initial-color: ["BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "AQUA", "MAGENTA"]

    The accepted message schemata are:
      * rgb: {"r": True, "b": False, "g": True}
      * color: {"color": "MAGENTA"}
      * blink_symmetric: {"color_a": "MAGENTA", "color_b": "AQUA", "delay": 1}
      * blink_asymmetric: {"color_a": "MAGENTA", "color_b": "AQUA", "delay_a": 1, "delay_b": 2}

    Example:
    driver:
        type: rgbled
        pin-red: 21
        pin-green: 22
        pin-blue: 23
        initial-color: GREEN  # ["BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "AQUA", "MAGENTA"]
        physical-closed: high
        topics-sub:
            command: /test/rgbled  # four different message types are accepted: rgb, color, blink_symmetric, blink_asymmetric
    """

    _pin_red = -1  # gpio pin id
    _pin_green = -1  # gpio pin id
    _pin_blue = -1  # gpio pin id
    _gpio_closed_red = -1  # value to write to gpio pin for closing output (0/1)
    _gpio_opened_red = -1  # value to write to gpio pin for opening output (0/1)
    _gpio_closed_green = -1  # value to write to gpio pin for closing output (0/1)
    _gpio_opened_green = -1  # value to write to gpio pin for opening output (0/1)
    _gpio_closed_blue = -1  # value to write to gpio pin for closing output (0/1)
    _gpio_opened_blue = -1  # value to write to gpio pin for opening output (0/1)
    _initial_color = None  # should the output be opened or closed after start
    _scheduler = None
    _active_driver = None

    def __init__(self, config, mqtt_client=None, logger=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        ADriver.__init__(self, config, mqtt_client, logger, logger_name=self.__class__.__name__,
                         stdout_log_level=stdout_log_level, no_gui=no_gui,
                         manage_monitoring_agent=manage_monitoring_agent)

        self._pin_red = int(self._config["pin-red"])
        self._pin_green = int(self._config["pin-green"])
        self._pin_blue = int(self._config["pin-blue"])
        
        self._initial_color = Color[self._config["initial-color"]]

        self._gpio_closed_red = self._read_physical_closed("physical-closed-red")
        self._gpio_opened_red = (self._gpio_closed_red + 1) % 2
        self._gpio_closed_green = self._read_physical_closed("physical-closed-green")
        self._gpio_opened_green = (self._gpio_closed_green + 1) % 2
        self._gpio_closed_blue = self._read_physical_closed("physical-closed-blue")
        self._gpio_opened_blue = (self._gpio_closed_blue + 1) % 2

        self._scheduler = AsyncScheduler()

        self._ui_commands["gpio_color"] = self._cmd_gpio_color
        self._ui_commands["gpio_rgb"] = self._cmd_gpio_rgb
        self._ui_commands["gpio_blink"] = self._cmd_gpio_blink
        self._ui_commands["gpio_state"] = self._cmd_gpio_state

    def _read_physical_closed(self, config_entry_name):
        if str(self._config[config_entry_name].lower()) == "low":
            gpio_closed = 0
        elif str(self._config[config_entry_name].lower()) == "high":
            gpio_closed = 1
        else:
            self._logger.error("'{}' - expected 'low'/'high' but received '{}'.".
                               format(config_entry_name, self._config[config_entry_name].lower()))
            raise ValueError("'{}' - expected 'low'/'high' but received '{}'.".
                             format(config_entry_name, self._config[config_entry_name].lower()))
        return gpio_closed

    def _cmd_gpio_color(self, args):
        """gpio_color - sets the rgb-led to the named color: GPIO_COLOR [BLACK|WHITE|RED|GREEN|BLUE|YELLOW|AQUA|MAGENTA]"""
        args = parse(args)
        print("{} {} '{}'\n".format(args, len(args), args[0].upper()))
        if len(args) != 1:
            print("Wrong arguments: {}. expected 'GPIO_COLOR [BLACK|WHITE|RED|GREEN|BLUE|YELLOW|AQUA|MAGENTA]'.\n".format(args))
        elif args[0].upper() not in Color.__members__:
            print("Wrong color: {}. expected 'GPIO_COLOR [BLACK|WHITE|RED|GREEN|BLUE|YELLOW|AQUA|MAGENTA]'.\n".format(args[0].upper()))
        else:
            color = args[0].upper()
            print("Setting color to: {}.".format(color))
            self._active_driver = StaticColor(self._set_pins, self._logger, self._scheduler, {"color": color})
            self._active_driver.display()

    def _cmd_gpio_rgb(self, args):
        """gpio_rgb - sets the rgb-led to the boolean values: GPIO_RGB Red Green Blue"""
        def _check_is_bool(s):
            s = s.lower()
            return s in ["true", "false"]

        args = parse(args)

        if len(args) != 3:
            print("Wrong arguments: {}. expected 'GPIO_RGB Red Green Blue'.\n".format(args))
        elif not (_check_is_bool(args[0]) and _check_is_bool(args[1]) and _check_is_bool(args[2])):
            print("All three parameters must be either 'True' of 'False. got: '{}'.\n".format(args))
        else:
            struct = {
                "r": args[0].lower() == "true", 
                "g": args[1].lower() == "true", 
                "b": args[2].lower() == "true"
                }
            print("Setting rgb to: {}.".format(struct))
            self._active_driver = StaticRGB(self._set_pins, self._logger, self._scheduler, struct)
            self._active_driver.display()

    def _cmd_gpio_blink(self, args):
        """gpio_blink - sets two colors and the delays for alternating between them: GPIO_BLINK [BLACK|WHITE|RED|GREEN|BLUE|YELLOW|AQUA|MAGENTA] [BLACK|WHITE|RED|GREEN|BLUE|YELLOW|AQUA|MAGENTA] delay (delay)"""
        expected = "GPIO_BLINK [BLACK|WHITE|RED|GREEN|BLUE|YELLOW|AQUA|MAGENTA] [BLACK|WHITE|RED|GREEN|BLUE|YELLOW|AQUA|MAGENTA] delay (delay)"

        args = parse(args)

        if len(args) < 3 or len(args) > 4:
            print("Wrong arguments: {}. expected '{}'.\n".format(args, expected))
        elif args[0].upper() not in Color.__members__:
            print("Wrong color A: {}. expected '{}'.\n".format(args[0].upper(), expected))
        elif args[1].upper() not in Color.__members__:
            print("Wrong color B: {}. expected '{}'.\n".format(args[1].upper(), expected))
        elif len(args) == 3:
            try:
                delay = float(args[2])
            except ValueError:
                print("Wrong delay value: {}. expected a float value.\n".format(args[2]))
                return
            struct = {
                "delay": delay,
                "color_a": args[0].upper(),
                "color_b": args[1].upper()
            }
            print("Setting symmetric blink to {}".format(struct))
            self._active_driver = BlinkColorsSymmetric(self._set_pins, self._logger, self._scheduler, struct)
            self._active_driver.display()
        else:
            try:
                delay_a = float(args[2])
            except ValueError:
                print("Wrong delay value: {}. expected a float value.\n".format(args[2]))
                return            
            try:
                delay_b = float(args[3])
            except ValueError:
                print("Wrong delay value: {}. expected a float value.\n".format(args[3]))
                return     
            struct = {
                "delay_a": delay_a,
                "delay_b": delay_b,
                "color_a": args[0].upper(),
                "color_b": args[1].upper()
            }
            print("Setting asymmetric blink to {}".format(struct))
            self._active_driver = BlinkColorsAsymmetric(self._set_pins, self._logger, self._scheduler, struct)
            self._active_driver.display()                

    def _cmd_gpio_state(self, args):
        """gpio_state - reads the state of the gpio: GPIO_STATE"""
        if GPIO.input(self._pin_red) == self._gpio_closed_red:
            state_red = "closed"
        else:
            state_red = "open"

        if GPIO.input(self._pin_green) == self._gpio_closed_green:
            state_green = "closed"
        else:
            state_green = "open"

        if GPIO.input(self._pin_blue) == self._gpio_closed_blue:
            state_blue = "closed"
        else:
            state_blue = "open"
            
        print("[{}] gpios: red {} is {}, green {} is {}, blue {} is {}.".format(self._name, self._pin_red, state_red, self._pin_green, state_green, self._pin_blue, state_blue))

    def _message_handler(self, msg):
        """on_message handler for topic sub 'command'."""
        self._logger.info("received message '{}' on topic '{}'.".format(msg, self._topics_sub["command"]))
        
        temp = msg.decode("UTF-8")
        struct = json.loads(temp)
        try:
            jsonschema.validate(struct, message_schema)
        except jsonschema.exceptions.ValidationError:
            raise ValueError("RGBLed.'{}'.payload received unexpected message format: '{}'.".format(msg.topic, temp))
        except jsonschema.exceptions.SchemaError:
            raise RuntimeError("RGBLed._message_handler - schema error!")

        self._active_driver = LEDDriverFactory.create(self._set_pins, self._logger, self._scheduler, struct)
        self._active_driver.display()

    def _set_pins(self, red, green, blue):
        def _output(pin, closed, open, value):
            if value:
                GPIO.output(pin, closed)
            else:
                GPIO.output(pin, open)

        _output(self._pin_red, self._gpio_closed_red, self._gpio_opened_red, red)
        _output(self._pin_green, self._gpio_closed_green, self._gpio_opened_green, green)
        _output(self._pin_blue, self._gpio_closed_blue, self._gpio_opened_blue, blue)

    def _driver_start(self):
        """ADriver._driver_start"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin_red, GPIO.OUT)
        GPIO.setup(self._pin_blue, GPIO.OUT)
        GPIO.setup(self._pin_green, GPIO.OUT)

        self._active_driver = StaticColor(self._set_pins, self._logger, self._scheduler, {"color": self._initial_color.name})
        self._active_driver.display()

        self._mqtt_client.subscribe(self._topics_sub["command"], self._message_handler)

    def _driver_stop(self):
        """ADriver._driver_stop"""
        self._mqtt_client.unsubscribe(self._topics_sub["command"], self._message_handler)
        GPIO.cleanup(self._pin_red)
        GPIO.cleanup(self._pin_blue)
        GPIO.cleanup(self._pin_green)

    @classmethod
    def _get_schema(cls):
        return get_schema()

    def _runtime_information(self):
        return {}

    def _config_information(self):
        return {}


def standalone():
    """Calls the static method Output.standalone()."""
    RGBLed.standalone()


if __name__ == "__main__":
    RGBLed.standalone()


