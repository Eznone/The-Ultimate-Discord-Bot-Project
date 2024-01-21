import RPi.GPIO as GPIO
from copreus.baseclasses.arotaryencoder import ARotaryEncoder


class RotaryEncoder2(ARotaryEncoder):
    """Driver for rotary encoder like the KY-040 together with schmitttriggers for debouncing and a flipflop for
    direction detection in hardware. (e.g. http://www.bristolwatch.com/ele2/rotary.htm)

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
        type: rotaryencoder2
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

    def __init__(self, config, mqtt_client=None, logger=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        ARotaryEncoder.__init__(self, config, mqtt_client, logger, logger_name=self.__class__.__name__,
                                stdout_log_level=stdout_log_level, no_gui=no_gui,
                                manage_monitoring_agent=manage_monitoring_agent)

    def _detect_rotation_direction(self):
        """Event handler for gpio pin 'clk'. Reads the direction from 'dt'."""
        akt_clk = GPIO.input(self._clk)
        self._logger.info("Rotary-event detected.")

        if GPIO.input(self._dt):
            rotate = self._RIGHT
        else:
            rotate = self._LEFT

        return rotate


def standalone():
    """Calls the static method RotaryEncoder.standalone()."""
    RotaryEncoder2.standalone()


if __name__ == "__main__":
    RotaryEncoder2.standalone()
