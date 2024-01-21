from time import time
import RPi.GPIO as GPIO
from copreus.baseclasses.arotaryencoder import ARotaryEncoder, Direction


class RotaryEncoder(ARotaryEncoder):
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

    _last_clk = -1  # last clk value - used for rotation direction detection
    _last_time = -1 # time stamp of the last rotation step
    _last_direction = 0  # rotation direction of the last rotation step
    _min_time_gap = 0.100  # minimum time gap between direction changes

    def __init__(self, config, mqtt_client=None, logger=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        ARotaryEncoder.__init__(self, config, mqtt_client, logger, logger_name=self.__class__.__name__,
                                stdout_log_level=stdout_log_level, no_gui=no_gui,
                                manage_monitoring_agent=manage_monitoring_agent)
        self._last_time = time()

    def _detect_rotation_direction(self):
        """Event handler for gpio pin 'clk'. Detects the rotation direction and filters out 'rotation bounces' -
        rotation direction changes that happen to fast und are thus considered to originiate in bounces. Publishes
        to the topic 'rotate'."""
        akt_clk = GPIO.input(self._clk)
        akt_time = time()
        self._logger.info("Rotary-event detected.")

        rotate = Direction.NONE

        if akt_clk != self._last_clk:
            rotate = Direction.LEFT
            if GPIO.input(self._dt) != akt_clk:
                rotate = Direction.RIGHT

            #filter
            if akt_time - self._last_time < self._min_time_gap and rotate != self._last_direction:
                self._logger.info("Time between direction change to small - skipping this event.")
                rotate = Direction.NONE
            else:
                self._last_direction = rotate
                self._last_time = akt_time

        self._last_clk = akt_clk
        return rotate


def standalone():
    """Calls the static method RotaryEncoder.standalone()."""
    RotaryEncoder.standalone()


if __name__ == "__main__":
    RotaryEncoder.standalone()
