from copreus.baseclasses.aepaper import EPaperMQTTMessageConverter
from copreus.baseclasses.aepaper import AEPaper
from PIL import Image
from io import BytesIO
from pelops.mythreading import LoggerThread
import threading
import datetime
import queue
from copreus.schema.epapersimple import get_schema
import pelops.ui.tools


class EPaperSimple(AEPaper):
    """
    A simplified interface for the epaper. It accepts full images only and displays the last recevied message. If
    during an update several other images are received all but the last one are dropped. Additionally, the display
    can be wiped regularly to ensure that no fragments/ghosts are shown.

    The driver entry in the yaml file consists of:
      * ADriver entries
        * topics_sub:
            * image - a single image covering the whole display to be placed in the current buffer.
        * topics_pub:
            * message_queue_size - publishes the number of messages that wait to be processes.
      * EPaperSimple entries
        * wipe-screen:
            * every-nth-day - how often should the timer be called
            * time - time during a day when the wipe screen action should take place. best use a time when no one will
            look on the screen like early in the morning
            * at-start-up - wipe the screen immedietly after start of the driver

    Example:
        driver:
            type: epapersimple
            model: 2.9
            spi:
                pin_cs: -1 # use spi cs mechanism. GPIO08/SPI_CE0_N
                bus: 0
                device: 0
                maxspeed: 2000000
            transpose: 270
            pin_rst:  13
            pin_dc:   19
            pin_busy: 6
            VCOM: -3.2
            autodeepsleep: True
            topics-sub:
                image: /test/display/full_image
            topics-pub:
                message_queue_size: /test/display/message_queue_size
            wipe-screen:
                every-nth-day: 1  # 0 for never
                time: 03:15 # wipe-screen will be called at the first update after this time. ignored if every-nth-day==0
                at-start-up: True

    """
    _topic_pub_msg_queue_size = None  # number of images in queue - possible values are 0 or 1
    _akt_image_entry = None  # last displayed image

    _update_available = None  # event - triggers if a new image is available -> display image is called by worker
    _image_queue = None

    _display_lock = None  # lock to restrict access to the display - used by wipe-screen and display image
    _stop_threads = None  # threading.Event to signal the poll loop to stop immediately.
    _display_update_thread = None  # thread in which the poll loop is executed.
    _wipe_screen_on_start = None  # wipe screen immediately
    _wipe_screen_thread = None  # thread for timed wipe-screen
    _wipe_screen_time = None  # time HH:MM at which the screen should be wiped
    _wipe_img_black = None  # black image for wiping
    _wipe_img_white = None  # white image for wiping

    def __init__(self, config, mqtt_client=None, logger=None, spi_lock=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        """
        Constructor

        :param config: yaml config structure
        :param mqtt_client: mymqttclient instance (optional)
        :param logger: logger instance (optional)
        :param spi_lock: spi lock instance (optional)
        """

        AEPaper.__init__(self, config, mqtt_client, logger, spi_lock=spi_lock, logger_name=self.__class__.__name__,
                         stdout_log_level=stdout_log_level, no_gui=no_gui,
                         manage_monitoring_agent=manage_monitoring_agent)

        self._update_available = threading.Event()
        self._update_available.clear()
        self._display_lock = threading.Lock()
        self._stop_threads = threading.Event()
        self._display_update_thread = LoggerThread(target=self._display_akt_image, logger=self._logger,
                                                   name="epapersimple.update.{}".format(self.get_name()))
        self._image_queue = queue.Queue()

        self._wipe_screen_on_start = bool(self._config["wipe-screen"]["at-start-up"])
        self._every_nth_day = self._config["wipe-screen"]["every-nth-day"]
        temp = self._config["wipe-screen"]["time"].split(":")
        self._wipe_screen_time = datetime.time(hour=int(temp[0]), minute=int(temp[1]))
        self._wipe_screen_thread = LoggerThread(target=self._wipe_screen_timer, logger=self._logger,
                                                name="epapersimple.wipe.{}".format(self.get_name()))

        self._wipe_img_black = Image.new('L', (self._width, self._height), 0)
        self._wipe_img_white = Image.new('L', (self._width, self._height), 255)

        self._topic_pub_msg_queue_size = self._topics_pub["message_queue_size"]

        self._ui_commands["wipe_screen"] = self._cmd_wipe_screen
        self._ui_commands["load_file"] = self._cmd_load_file
        self._ui_commands["save_file"] = self._cmd_save_file

    def _cmd_load_file(self, args):
        """load_file filename - load an image file and display the content"""
        if len(args) == 0:
            print("expected one argument. 'load_file filename'")
        else:
            filename = args
            try:
                self._load_image(filename)
                text = "loaded image from '{}'".format(filename)
            except IOError as e:
                text = "cannot load image from '{}'\n{}".format(filename, e)
            pelops.ui.tools.more(text)

    def _cmd_save_file(self, args):
        """save_file filename - save the last image to the provided file name as a PNG image"""
        if len(args) == 0:
            print("expected one argument: 'load_file filename'")
        else:
            filename = args
            try:
                image, _, _ = self._akt_image_entry
                text = "saved last image to '{}'".format(filename)
            except IOError as e:
                text = "cannot save image to '{}'\n{}".format(filename,e)
            pelops.ui.tools.more(text)

    def _cmd_wipe_screen(self, args):
        """wipe_screen - wipe the epaper with a series of black/white images and restore the last displayed image"""
        pelops.ui.tools.more("wipping screen ...")
        self._wipe_screen()
        pelops.ui.tools.more("... done")

    def _set_update_available(self):
        """sets state to none emtpy queue (sets _update_available event and publishes message queue size 1."""
        self._logger.info("EPaperSimple._set_update_available")
        self._update_available.set()
        self._mqtt_client.publish(self._topic_pub_msg_queue_size, 1)

    def _clear_update_available(self):
        """sets state to empty queue (clears _update_available event and publishes message queue size 0."""
        self._logger.info("EPaperSimple._clear_update_available")
        if self._image_queue.empty():
            self._update_available.clear()
            self._mqtt_client.publish(self._topic_pub_msg_queue_size, 0)
        else:
            self._logger.info("EPaperSimple._clear_update_available - skipped. image queue not empty: {}"
                               .format(self._image_queue.qsize()))

    def _handler_display_image(self, msg):
        """on_message handler for topic sub 'full_image'"""
        self._logger.info("EPaperSimple._handler_display_image - received full_image in topic {}."
                          .format(self._topics_sub["image"]))
        if self._update_available.is_set():
            self._logger.info("EPaperSimple._handler_display_image - replacing image that waits for being displayed.")
        image = Image.open(BytesIO(msg))
        self._queue_image(image)

    def _load_image(self, path):
        """reads an image for the provided system path"""
        self._logger.info("EPaperSimple._load_image - loading image from file {}.".format(path))
        image = Image.open(path)
        self._queue_image(image)

    def _queue_image(self, image):
        """takes an image instance, transposes it and puts intor the image queue for further processing"""
        self._logger.info("EPaperSimple._queue_image - adding image to the queue")
        image, x, y = EPaperMQTTMessageConverter.transpose_image(self._transpose, image, self._width, self._height)
        self._image_queue.put([image, x, y])
        self._set_update_available()

    def _display_akt_image(self):
        """
        send received image to the epaper. uses the image that has been assigned to _akt_image. skips update if the
        value is None. loop stops if _Stop_threads is set.

        acquire the lock (_display_frame_lock), wake up from deep sleep (optional), put the image into the
        current frame buffer, display frame, send back to deep sleep (optional), wait the _update_time and then
        release the lock."""

        self._logger.info("EPaperSimple._display_akt_image - thread started")

        while not self._stop_threads.is_set():
            self._update_available.wait(timeout=0.25)  # busy waiting ... currently no elegant way to wait for two events ...
            if not self._update_available.is_set():
                continue  # timeout reached

            while not self._image_queue.empty():
                self._logger.info("... fetching entry from image queue.")
                self._akt_image_entry = self._image_queue.get()

            if self._akt_image_entry is None:
                self._logger.info("... no image received until now - nothing to be displayed ...")
                self._clear_update_available()
                continue

            image, x, y = self._akt_image_entry

            self._logger.info("display image. acquiring lock ...")
            with self._display_lock:
                self._logger.info("... lock acquired")
                if self._auto_deep_sleep:
                    self._reset()
                self._set_frame_memory(image, x, y)
                self._display_frame()
                if self._auto_deep_sleep:
                    self._deep_sleep()
                self._stop_threads.wait(timeout=self._update_time)  # wait for image to be processed or for stop_loop event
                self._logger.info("... image displayed. lock released.")

            self._clear_update_available()

        self._logger.info("EPaperSimple._display_akt_image - thread stopped")

    def _seconds_to_next_timer_event(self):
        """
        Calculates how many seconds are from now to next "HH:MM" time.

        :return: float / seconds
        """
        now = datetime.datetime.now()
        time = now.time()
        day = now.date()
        self._logger.info("EPaperSimple._seconds_to_next_timer_event - now: {}, day: {}, time: {}"
                           .format(now, day, time))
        self._logger.info("EPaperSimple._seconds_to_next_timer_event - target_time: {}, n-th day: {}"
                           .format(self._wipe_screen_time, self._every_nth_day))

        if time > self._wipe_screen_time:
            # wait until next day (or nth day) for wipe_screen_time to occur
            self._logger.info("EPaperSimple._seconds_to_next_timer_event - time > wipe_screen_time")
            target = datetime.datetime.combine(day, self._wipe_screen_time)
            target = target + datetime.timedelta(days=self._every_nth_day)
        elif time < self._wipe_screen_time:
            # wait until wipe_screen_time today
            self._logger.info("EPaperSimple._seconds_to_next_timer_event - time < wipe_screen_time")
            target = datetime.datetime.combine(day, self._wipe_screen_time)
        else:
            # its now!
            self._logger.info("EPaperSimple._seconds_to_next_timer_event - time == wipe_screen_time")
            target = now

        wait_time = target - now
        self._logger.info("EPaperSimple._seconds_to_next_timer_event - wait_time: {}.".format(wait_time))
        return wait_time.total_seconds()

    def _wipe_screen_timer(self):
        """endless loop that waits until next wipe screen time and initialize wipe screen and restarts wait.
        stops if _stop_threads is set."""
        self._logger.info("EPaperSimple._wipe_screen_timer - thread started")
        while not self._stop_threads.is_set():
            wait_time = self._seconds_to_next_timer_event()
            self._logger.info("EPaperSimple._wipe_screen_timer - waiting {} seconds (time: {}, nth-day: {})"
                                 .format(wait_time, self._wipe_screen_time, self._every_nth_day))
            self._stop_threads.wait(timeout=wait_time)
            if not self._stop_threads.is_set():
                self._wipe_screen()
        self._logger.info("EPaperSimple._wipe_screen_timer - thread stopped")

    def _wipe_screen(self):
        """wipes the screen by displaying alternating black and white images. restores to last displayed image
        at the end by setting _update_available timer."""
        self._logger.info("EPaperSimple._wipe_screen - started")
        wait_time = self._update_time + 0.5

        self._logger.info("EPaperSimple._wipe_screen - acquiring lock ...")
        with self._display_lock:
            self._logger.info("EPaperSimple._wipe_screen - ... lock acquired")
            if self._auto_deep_sleep:
                self._reset()

            # set white
            self._logger.info("EPaperSimple._wipe_screen - display white")
            self._set_frame_memory(self._wipe_img_white, 0, 0)
            self._display_frame()
            self._stop_threads.wait(timeout=wait_time)  # wait for image to be processed or for stop_loop event

            # set black
            self._logger.info("EPaperSimple._wipe_screen - display black")
            self._set_frame_memory(self._wipe_img_black, 0, 0)
            self._display_frame()
            self._stop_threads.wait(timeout=wait_time)  # wait for image to be processed or for stop_loop event

            for i in range(4):
                # set white
                self._logger.info("EPaperSimple._wipe_screen - display white")
                self._display_frame()
                self._stop_threads.wait(timeout=wait_time*2)  # wait for image to be processed or for stop_loop event
                # set black
                self._logger.info("EPaperSimple._wipe_screen - display black")
                self._display_frame()
                self._stop_threads.wait(timeout=wait_time*2)  # wait for image to be processed or for stop_loop event

            if self._auto_deep_sleep:
                self._deep_sleep()

            self._logger.info("EPaperSimple._wipe_screen - ... lock released")

        # initiate display of akt image
        self._logger.info("EPaperSimple._wipe_screen - initiate update display")
        self._set_update_available()
        self._logger.info("EPaperSimple._wipe_screen - finished")

    def _epaper_start(self):
        """starts by subscribing to image topic, optionally wipeing screen and setting timer to next wipe time."""
        self._mqtt_client.subscribe(self._topics_sub["image"], self._handler_display_image)
        self._stop_threads.clear()
        if self._wipe_screen_on_start:
            self._wipe_screen()
        if self._every_nth_day > 0:
            self._wipe_screen_thread.start()
        self._display_update_thread.start()

    def _epaper_stop(self):
        """stops by unsubscribing, and stopping threads."""
        self._mqtt_client.unsubscribe(self._topics_sub["image"], self._handler_display_image)
        self._stop_threads.set()
        self._display_update_thread.join()
        if self._every_nth_day > 0:
            self._wipe_screen_thread.join()

    @classmethod
    def _get_schema(cls):
        return get_schema()

    def _runtime_information(self):
        return {}

    def _config_information(self):
        return {}


def standalone():
    """Calls the static method EPaperSimple.standalone()."""
    EPaperSimple.standalone()


if __name__ == "__main__":
    EPaperSimple.standalone()
