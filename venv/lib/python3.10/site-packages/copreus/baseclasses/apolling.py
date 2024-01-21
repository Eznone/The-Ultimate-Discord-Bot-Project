from time import time
import threading
from pelops.mythreading import LoggerThread


class APolling(object):
    """Additional base class for driver that need to poll in regular intervals.

    Expects 'poll-interval' in the driver yaml configuration - device is polled every n seconds. Further,
    for spontaneus polling, apolling subscribes to poll-now and upon receiving of the predefined command in
    mqtt-translations, polling is started. if 'poll-interval' is set to '0' the driver reacts only to poll_now mqtt
    commands.
    """

    _poll_interval = -1  # poll time in seconds
    _stop_loop = None  # threading.Event to signal the poll loop to stop immediately.
    _loop_thread = None  # thread in which the poll loop is executed.
    _logger_apolling = False  # print debugging information if set to yes.
    _mqtt_client_apolling = False  # mqtt client instance
    _poll_lock = None  # lock polling
    _poll_now_topic = None  # listen to this topic for poll now commands
    _poll_now_command = None  # if this command is received, start polling immediately

    def __init__(self, config, mqtt_client, logger):
        self._logger_apolling = logger
        self._mqtt_client_apolling = mqtt_client
        self._poll_interval = config["poll-interval"]
        self._poll_now_command = config["mqtt-translations"]["poll-now"]
        self._poll_now_topic = config["topics-sub"]["poll-now"]
        self._stop_loop = threading.Event()
        self._poll_lock = threading.Lock()

    def poll_now(self):
        with self._poll_lock:
            self._poll_device()

    def _poll_now(self, msg):
        """on_message handler for topic sub 'readnow'."""
        msg = msg.decode("utf-8")
        self._logger_apolling.info("received message '{}' on topic '{}'.".format(msg, self._poll_now_topic))
        if str(msg) == str(self._poll_now_command):
            self.poll_now()
        else:
            self._logger_apolling.error("msg expects {}. received '{}' instead.".
                               format(self._poll_now_command, msg))
            raise ValueError("msg expects {}. received '{}' instead.".
                             format(self._poll_now_command, msg))

    def _poll_loop(self):
        """Executes _poll_device and then waits (_POLL_INTERVAL - execution time of _poll_device). This guarantees that
        e.g. the state of a pin is checked exactly each 30 seconds."""
        self._logger_apolling.info("APolling._poll_loop - entered poll_loop method.")

        while not self._stop_loop.isSet():
            start = time()
            with self._poll_lock:
                self._poll_device()
            sleep_for = max(0, self._poll_interval - (time() - start))

            self._logger_apolling.info("APolling._poll_loop - sleep for " + str(sleep_for) + " seconds.")
            self._stop_loop.wait(sleep_for)

        self._logger_apolling.info("APolling._poll_loop - exiting poll_loop method.")

    # @abstract
    def _poll_device(self):
        """This method must be implemented by the silbing class. Whatever should must be done to poll the driver should
        be placed here."""
        self._logger_apolling.error("APolling._poll_device - Please implement this method")
        raise NotImplementedError("Please implement this method!")

    def _start_polling(self):
        """Start a new thread with _pool_loop. Usually called in the _start_sequence method of the silbling."""
        if self._poll_interval == 0:
            self._logger_apolling.info("APolling._start_polling - poll interval is set to '0' -> poll loop is disabled.")
        else:
            self._logger_apolling.info("APolling._start_polling - start loop thread.")
            self._stop_loop.clear()
            self._loop_thread = LoggerThread(target=self._poll_loop, name="copreus.polling",
                                             logger=self._logger_apolling)
            self._loop_thread.start()
        self._logger_apolling.info("APolling._start_polling - registering poll_now topic handler.")
        self._mqtt_client_apolling.subscribe(self._poll_now_topic, self._poll_now)
        self._logger_apolling.info("APolling._start_polling - started.")

    def _stop_polling(self):
        """Stop _pool_loop with Event _stop_loop. Usually called in the _stop_sequence method of the silbling."""
        self._logger_apolling.info("APolling._stop_polling - unregistering poll_now topic handler.")
        self._mqtt_client_apolling.unsubscribe(self._poll_now_topic, self._poll_now)
        if self._poll_interval > 0:
            self._logger_apolling.info("APolling._start_polling - stopping loop thread.")
            self._stop_loop.set()
            self._loop_thread.join()
        self._logger_apolling.info("APolling._stop_polling - stopped.")

