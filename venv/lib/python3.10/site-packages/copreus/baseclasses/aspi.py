from threading import Lock
import RPi.GPIO as GPIO
import spidev


class ASPI:
    """Additional base class for drivers that want to use the SPI interface.

    Expects a sub-segment called 'spi' in the driver yaml. The entries in this sub-segment are:
      * pin_cs - cable select gpio pin (if -1 or not present the spi-driver internal cs will be used. e.g.
      SPI_CE0_N/GPIO08 for device 0.)
      * bus - spi bus
      * device - spi device
      * maxspeed - maximum connection speed in Hz

    For the case that different devices are connected to the same bus/device but different cs-pins, this class uses a
    Lock mechanism to avoid concurrent resource usage. If none is provided to the constructor, each driver instance
    is acting independently.

    GPIO.setmode(GPIO.BCM)"""

    _cs = -1  # cable select gpio pin id
    _use_spi_internal_cs = False
    _bus = -1  # spi bus
    _device = -1  # spi device
    _max_speed = -1  # maximum connection speed in Hz
    _spi = None  # instance of spidev
    _spi_lock = None  # threading.Lock
    _logger_aspi = False  # print debugging information if set to yes.
    _silence_logger = False  # if set to True, logging for this class will be turned off

    def __init__(self, config, logger, spi_lock = None, silence_logger=False):
        self._logger_aspi = logger
        self._silence_logger = silence_logger

        if spi_lock is None:
            self._spi_lock = Lock()
        else:
            self._spi_lock = spi_lock

        try:
            self._use_spi_internal_cs = False
            self._cs = config["spi"]["pin_cs"]
            if self._cs == -1:
                self._use_spi_internal_cs = True
        except KeyError:
            self._use_spi_internal_cs = True

        self._bus = config["spi"]["bus"]
        self._device = config["spi"]["device"]
        self._max_speed = config["spi"]["maxspeed"]

        GPIO.setmode(GPIO.BCM)
        if not self._use_spi_internal_cs:
            GPIO.setup(self._cs, GPIO.OUT)

    def _connect_spi(self):
        """Initializes and opens spi interface."""
        self._logger_aspi.info("connect to spi")
        self._spi = spidev.SpiDev()
        self._spi.open(self._bus, self._device)
        self._spi.max_speed_hz = self._max_speed
        self._spi.mode = 0b00
        # self._spi.no_cs = True  # TODO - https://gitlab.com/tgd1975/copreus/issues/1

    def _disconnect_spi(self):
        """Closes spi interface."""
        self._logger_aspi.info("ASPI._disconnect_spi - disconnect from spi")
        self._spi.close()

    def _transfer(self, msg):
        """Start transfer if and only if the lock was aqcuired successfully. CS pin is lowered and raised before and
        after the transfer."""
        if not self._silence_logger:
            self._logger_aspi.debug("ASPI._transfer - acquire _spi_lock")
        with self._spi_lock:
            if not self._silence_logger:
                self._logger_aspi.debug("ASPI._transfer - ... acquire _spi_lock success")
            if not self._use_spi_internal_cs:
                GPIO.output(self._cs, 0)
            result = self._spi.xfer2(msg)
            if not self._use_spi_internal_cs:
                GPIO.output(self._cs, 1)
        if not self._silence_logger:
            self._logger_aspi.debug("ASPI._transfer - released lock _spi_lock")
        return result

    def _start_spi(self):
        """Initialize CS-pin and connect to spi interface. Usually called in the _start_sequence method of the
                silbling."""
        if not self._use_spi_internal_cs:
            GPIO.output(self._cs, 1)
        self._connect_spi()

    def _stop_spi(self):
        """Relase CS-pin and disconnect to spi interface. Usually called in the _stop_sequence method of the
                silbling."""
        self._disconnect_spi()
        if not self._use_spi_internal_cs:
            GPIO.cleanup(self._cs)
