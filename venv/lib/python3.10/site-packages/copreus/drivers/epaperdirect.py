from copreus.baseclasses.aepaper import AEPaper
from copreus.baseclasses.aepaper import EPaperMQTTMessageConverter
from time import sleep
import queue
from pelops.mythreading import LoggerThread
import threading
from enum import Enum
from copreus.schema.epaperdirect import get_schema


class TaskType(Enum):
    """Task type for entries in the message queue."""
    DISPLAY = 0
    SWITCH = 1


class EPaperDirect(AEPaper):
    """
    This driver basically updates either the whole display (full_image) or selected parts (partial_image). The latter
    one results in faster update times. Internally, the epaper has two buffers. Via a command message the buffers are
    flipped. After flipping, one buffer is used to update the display while the other buffer is ready to receive new
    data via spi.

    When using partial image updates please take the two buffers under consideration. If two different areas are
    updated alternatively, it will result in a "blinking" behavior. The most common case - one static background
    image - and constantly update of the same area can be realised by first sending the full_image_twice and then
    the partial_image messages.

    Partial images must have a width and an x-position value that are multiples of eight. Any other value will result
    in a ValueError. Some displays have a width that is not compliant to this rule. In this case the display will have
    a logic width (e.g. 2.13 inch display has a width of 122 and a logic width of 128).

    The driver entry in the yaml file consists of:
      * ADriver entries
        * topics_sub:
            * full_image - a single image covering the whole display to be placed in the current buffer.
            * partial_image - list of image covering only parts of the display plus their position to be placed into
            the current buffer.
            * switch_frame - switch between the two frame buffers
        * mqtt-translations:
            * switch_frame - the command expected for switch_frame action
        * topics_pub:
            * message_queue_size - publishes the number of messages that wait to be processes.

    Example:
        driver:
            type: epaperdirect
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
                full_image: /test/display/full_image
                partial_image: /test/display/partial_image
                switch_frame: /test/display/switch_frame
            mqtt-translations:
                switch_frame: SWITCH
            topics-pub:
                message_queue_size: /test/display/message_queue_size

    """
    _msg_queue_size = 0  # number of mqtt messages that wait to be processed
    _msg_queue = None  # queue with tasks to be executed that are received via mqtt
    _msg_queue_worker_thread = None  # thread that processes all entries that are put to _msg_queue

    _topic_pub_msg_queue_size = None  # topic the current message queue size will be published to
    _switch_command = None  # expected command that initiates a frame buffer switch

    _display_frame_lock = None   # locked during image update (processing time + update_time)

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
        self._display_frame_lock = threading.Lock()

        self._msg_queue = queue.Queue()
        self._msg_queue_size = 0
        self._msg_queue_worker_thread = LoggerThread(target=self._msg_queue_worker, logger=self._logger,
                                                     name="epaperdirect.{}".format(self.get_name()))

        self._switch_command = self._mqtt_translations["switch_frame"]
        self._topic_pub_msg_queue_size = self._topics_pub["message_queue_size"]

    def _handler_switch_frame(self, msg):
        """on_message handler for topic sub 'switch_frame'"""
        if msg == self._switch_command:
            self._logger.info("EPaperDirect._handler_switch_frame - received switch frame command via topic {}.".format(self._topics_sub["switch_frame"]))
            self._put_to_msg_queue(TaskType.SWITCH)
        else:
            self._logger.info("EPaperDirect._handler_switch_frame - received unknown command '{}' via topic {}. expected command {}."
                              .format(msg, self._topics_sub["switch_frame"], self._switch_command))

    def _handler_display_full_image(self, msg):
        """on_message handler for topic sub 'full_image'"""
        self._logger.info("EPaperDirect._handler_display_full_image - received full_image in topic {}.".format(self._topics_sub["full_image"]))
        image_entry = EPaperMQTTMessageConverter.from_full_image(msg, self._transpose,
                                                                 self._width, self._height)
        self._put_to_msg_queue(TaskType.DISPLAY, image_entry)

    def _handler_display_partial_image(self, msg):
        """on_message handler for topic sub 'partial_image'"""
        self._logger.info("EPaperDirect._handler_display_partial_image - received partial_image in topic {}.".format(self._topics_sub["partial_image"]))
        image_entries = EPaperMQTTMessageConverter.from_partial_images(msg, self._transpose,
                                                                       self._width, self._height)
        self._put_to_msg_queue(TaskType.DISPLAY, image_entries)

    def _msg_queue_worker(self):
        """
        process each item in queue and decrease _queue_size (new value is published). two different types of tasks
        can be processed:
          * DISPLAY - take the provided value and call _display_image
          * SWITCH - call _switch_frame
        this approach ensures that an incoming switch statement is processed if and only if all previously received
        images (full or partial) have been processed.
        """
        while True:
            task = self._msg_queue.get()
            if task is None:
                break

            tasktype, value = task

            if tasktype == TaskType.DISPLAY:
                self._display_image(value)
            elif tasktype == TaskType.SWITCH:
                self._switch_frame()
            else:
                self._logger.error("EPaperDirect._msg_queue_worker - unknown task type '{}'".format(tasktype))
                raise ValueError("EPaperDirect._msg_queue_worker - unknown task type '{}'".format(tasktype))

            self._msg_queue.task_done()
            self._msg_queue_size = self._msg_queue_size - 1

            self._logger.info("EPaperDirect._msg_queue_worker - mqtt message queue size decreased to: {}.".format(self._msg_queue_size))
            self._publish_value(self._topic_pub_msg_queue_size, self._msg_queue_size)

    def _put_to_msg_queue(self, tasktype, value=None):
        """
        increase queue size, publish new value and put task togehter with task type to _msg_queue

        :param tasktype: TaskType enum value
        :param value: payload for task (optional)
        :return:
        """
        self._msg_queue.put([tasktype, value])
        self._msg_queue_size = self._msg_queue_size + 1
        self._logger.info("EPaperDirect._put_to_msg_queue - mqtt message queue size increased to: {}.".format(self._msg_queue_size))
        self._publish_value(self._topic_pub_msg_queue_size, self._msg_queue_size)

    def _empty_msg_queue(self):
        """remove all tasks from _msg_queue"""
        while not self._msg_queue.empty():
            try:
                temp = self._msg_queue.get_nowait()
                self._msg_queue.task_done()
            except queue.Empty:
                pass
        self._msg_queue_size = 0
        self._logger.info("EPaperDirect._empty_msg_queue - mqtt message queue cleared")
        self._publish_value(self._topic_pub_msg_queue_size, self._msg_queue_size)

    def _switch_frame(self):
        """
        switch between the two frames. the active frame will be displayed.
        """
        self._logger.info("EPaperDirect._switch_frame - switch to other frame (_display_frame_lock)")
        with self._display_frame_lock:
            self._logger.info("EPaperDirect._switch_frame - _display_frame_lock acquired")
            self._display_frame()
            self._logger.info("EPaperDirect._switch_frame - _display_frame_lock released.")

    def _display_image(self, images):
        """send received image(s) to the epaper.

        acquire the lock (_display_frame_lock), wake up from deep sleep (optional), put all (partial) images into the current frame buffer,
        display frame, send back to deep sleep (optional), wait the _update_time and then release the lock."""
        self._logger.info("EPaperDirect._display_image - display image")
        with self._display_frame_lock:
            self._logger.info("EPaperDirect._display_image - lock _display_frame_lock acquired")
            if self._auto_deep_sleep:
                self._reset()

            for map in images:
                x = map["x"]
                y = map["y"]
                image = map["image"]
                self._logger.info("EPaperDirect._display_image - ... added image at {}/{}.".format(x, y))
                self._set_frame_memory(image, x, y)

            self._display_frame()
            if self._auto_deep_sleep:
                self._deep_sleep()
            sleep(self._update_time)
            self._logger.info("EPaperDirect._display_image - ... image displayed. lock _display_frame_lock released.")

    def _epaper_start(self):
        """start the message queue workers and subscribe to the incoming topics."""
        self._msg_queue_worker_thread.start()
        self._mqtt_client.subscribe(self._topics_sub["full_image"], self._handler_display_full_image)
        self._mqtt_client.subscribe(self._topics_sub["partial_image"], self._handler_display_partial_image)
        self._mqtt_client.subscribe(self._topics_sub["switch_frame"], self._handler_switch_frame)
        self._publish_value(self._topic_pub_msg_queue_size, self._msg_queue_size)

    def _epaper_stop(self):
        """unsubscribe from all topics and empty message queue"""
        with self._display_frame_lock:
            self._mqtt_client.unsubscribe(self._topics_sub["full_image"], self._handler_display_full_image)
            self._mqtt_client.unsubscribe(self._topics_sub["partial_image"], self._handler_display_partial_image)
            self._mqtt_client.unsubscribe(self._topics_sub["switch_frame"], self._handler_switch_frame)
            self._empty_msg_queue()
            self._msg_queue.join()

    @classmethod
    def _get_schema(cls):
        return get_schema()

    def _runtime_information(self):
        return {}

    def _config_information(self):
        return {}


def standalone():
    """Calls the static method EPaperDirect.standalone()."""
    EPaperDirect.standalone()


if __name__ == "__main__":
    EPaperDirect.standalone()
