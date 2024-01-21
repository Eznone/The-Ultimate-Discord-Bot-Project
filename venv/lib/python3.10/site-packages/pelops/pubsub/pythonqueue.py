from pelops.pubsub.apubsub import APubSub
import queue
from pelops.mythreading import LoggerThread


class PythonQueue(APubSub):
    _message_queue = None
    _message_worker = None

    def __init__(self, config, logger, quiet=False):
        APubSub.__init__(self, config, logger, __name__, quiet)
        self._message_queue = queue.Queue()
        self._message_worker = LoggerThread(target=self._worker, logger=self._logger)

    def _worker(self):
        while True:
            item = self._message_queue.get()
            if item is None:
                break
            if self.is_connected.isSet():
                topic, message = item
                self._on_message(topic, message)
            self._message_queue.task_done()

    def _on_message(self, topic, message):
        if topic in self._topic_handler:
            self._stats.recv(topic)
            for handler in self._topic_handler[topic]:
                handler(message)

    def connect(self):
        self._message_worker.start()
        self.is_connected.set()
        self.is_disconnected.clear()

    def disconnect(self):
        self.is_connected.clear()
        self._message_queue.put(None)
        self._message_worker.join()
        self.is_disconnected.set()

    def publish(self, topic, msg):
        self._logger.info("publish - publishing to topic '{}' the message '{}'.".format(topic, msg))
        if self.is_connected.isSet():
            self._stats.sent(topic)
            self._message_queue.put((topic, str(msg).encode("UTF-8")))
        else:
            self._logger.warning("publish - trying to publish while not being connected to mqtt broker.")
            raise RuntimeWarning("publish - trying to publish while not being connected to mqtt broker.")

    def _subscribe_postprocessor(self, topic, handler, ignore_duplicate=False):
        pass

    def _unsubscribe_postprocessor(self, topic):
        pass
