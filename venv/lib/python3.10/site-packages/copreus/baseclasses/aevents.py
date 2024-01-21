import RPi.GPIO as GPIO


class AEvents(object):
    """Additional base class for driver that must react to changing pin states.

    Events are registered for BOTH (raising and falling edge). If necessary, the handler function must differentiate
    between raising and falling edge. Usually done by reading the current state of the pin.

    GPIO.setmode(GPIO.BCM)"""

    _events = None  # dict containing the pin-method parings.
    _logger_aevents = None  # print debugging information if set to yes.

    def __init__(self, config, logger):
        self._events = {}
        self._logger_aevents = logger
        GPIO.setmode(GPIO.BCM)

    def _add_event(self, pin, func, bounce_time=50):
        """Add an event handler """
        self._logger_aevents.info("AEvents._add_event - pin:{}, func:{}, bounce:{}.".format(pin, func, bounce_time))
        self._events[int(pin)] = {"f": func, "b": bounce_time}

    def _register_events(self):
        """Register all events that are stored in the dict _events. Usually called in the _start_sequence method of the
        silbling."""
        self._logger_aevents.info("AEvents._register_events - register events")
        for pin,event in self._events.items():
            self._logger_aevents.debug("AEvents._register_events - register event pin:{}, callback:'{}', "
                                      "bounce_time:'{}'".
                                      format(str(pin), str(event["f"]), str(event["b"])))
            GPIO.setmode(GPIO.BCM)                                      
            GPIO.add_event_detect(pin, GPIO.BOTH, callback=event["f"], bouncetime=event["b"])

    def _unregister_events(self):
        """Unregister from all events that are stored in the dict _events. Usually called in the
         _stop_sequence method of the silbling."""
        self._logger_aevents.info("AEvents._unregister_events - unregister events")
        for pin,event in self._events.items():
            self._logger_aevents.debug("AEvents._unregister_events - remove event for pin {}.".format(pin))
            GPIO.setmode(GPIO.BCM)
            GPIO.remove_event_detect(pin)
