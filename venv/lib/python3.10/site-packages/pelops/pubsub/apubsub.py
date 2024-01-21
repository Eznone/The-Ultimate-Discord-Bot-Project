from threading import Event, Lock
from pelops.logging import mylogger
from pelops.pubsub.statistics import Statistics


class APubSub(object):
    _client = None  # holds an instance of paho.mqtt.client.Client
    _config = None  # yaml configuration
    _logger = None  # logger instance
    _quiet = None  # surpress printing high-level runtime information if set to yes.
    _lock_client = None  # locks processing of all relevant methods (connect, disconnect, subscribe, unsubscribe, unsubscribe all)
    is_connected = None  # threading.Event - True if connection to mqtt broker has been successfully established.
    is_disconnected = None # threading.Event - True if no connection to the mqtt broker exists
    _stats = None  # keeps statics on sent and received messages
    _topic_handler = None  # dict{string:list} - for each registered topic exists an entry with a list of all message handlers for this topic

    def __init__(self, config, logger, loggername, quiet=False):
        """
        Constructor

        :param config: config yaml structure
        :param logger: instance of logger - a child with name __name__ will be spawned
        :param quiet: boolean - if True, the runtime shell outputs like "Connecting" will be surpressed
        """
        self._config = config
        self._logger = mylogger.get_child(logger, loggername, config)
        self._quiet = quiet
        self._logger.info("__init__ - initalizing")
        self._logger.debug("__init__ - config: {}.".format(self._config))
        self.is_connected = Event()
        self.is_connected.clear()
        self.is_disconnected = Event()
        self.is_disconnected.set()
        self._lock_client = Lock()
        self._topic_handler = {}
        self._stats = Statistics()

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def publish(self, topic, msg):
        raise NotImplementedError

    def subscribe(self, topic, handler, ignore_duplicate=False):
        """
        Registeres the provided handler to the provided topic. The handler is expected to accept the message payload
        as only parameter (e.g. "def myhandler(message)", "mymqttclient.subscribe('/topic', myhandler)"). For each topic
        several handler can be registered. If a topic/handler pair is suscribed more than once a ValueError will be
        raised.

        :param topic: string - mqtt topic
        :param handler: method
        :param ignore_duplicate: no error will be produce in case of topic/handler pair has already been added
        """
        self._logger.info("subscribe - subscribing topic '{}' with handler '{}'.".format(topic, handler))
        with self._lock_client:
            try:
                h = self._topic_handler[topic]
                if h.count(handler) > 0 and not ignore_duplicate:
                    raise ValueError("subscribe - topic/handler pair already added. ({}/{})"
                                     .format(topic, handler))
                h.append(handler)
            except KeyError:
                self._topic_handler[topic] = [handler,]
            self._subscribe_postprocessor(topic, handler, ignore_duplicate)

    def _subscribe_postprocessor(self, topic, handler, ignore_duplicate=False):
        raise NotImplementedError

    def unsubscribe(self, topic, handler, ignore_not_found=False):
        """
        Unsubscribe topic/handler pair (reverse of subscribe). As several handler might be registered for the same topic
        and the same client might be used in different microservices, removing all handler for a given topic might
        result in unwanted side effects.

        :param topic: string - mqtt topic
        :param handler: method
        :param ignore_not_found: no error will be produce in case of topic/handler pair does not exist
        """

        self._logger.info("unsubscribe - unsubscribing topic '{}' with handler '{}'.".
                          format(topic, handler))
        with self._lock_client:
            try:
                if len(self._topic_handler[topic]) > 1:
                    self._logger.debug("unsubscribe - more than one handler registered for topic.")
                    if handler not in self._topic_handler[topic]:
                        if not ignore_not_found:
                            raise ValueError("unsubscribe - unknown handler '{}' for topic '{}'"
                                             .format(handler, topic))

                    self._topic_handler[topic].remove(handler)
                else:
                    self._logger.debug("unsubscribe - clear topic handler entry from dict and unsubscribe from "
                                       "topic.")
                    if handler not in self._topic_handler[topic]:
                        if not ignore_not_found:
                            self._logger.error("unsubscribe - unknown handler '{}' for topic '{}'"
                                                 .format(handler, topic))
                            raise ValueError("unsubscribe - unknown handler '{}' for topic '{}'"
                                             .format(handler, topic))

                    del(self._topic_handler[topic])
                    self._unsubscribe_postprocessor([topic])

            except KeyError:
                if not ignore_not_found:
                    self._logger.error("unsubscribe - unknown topic '{}'".format(topic))
                    raise

    def _unsubscribe_postprocessor(self, topics):
        raise NotImplementedError

    def get_stats(self):
        st = {}
        for k, v in self.subscribed_topics().items():
            st[k] = v

        stats = {
            "connected": self.is_connected.is_set(),
            "mqtt_stats": self._stats.get_stats(),
            "subscribed_topics": st
        }
        return stats

    def subscribed_topics(self):
        result = {}
        for k, v in self._topic_handler.items():
            result[k] = []
            for x in v:
                result[k].append(x.__qualname__)
        return result

    def unsubscribe_all(self):
        """
        Reset all subscriptions. Mainly used for testing purposes.
        """
        self._logger.info("unsubscribe_all")
        with self._lock_client:
            self._logger.info("unsubscribe_all - topics '{}'".format(self._topic_handler.keys()))
            self._unsubscribe_postprocessor(list(self._topic_handler.keys()))
            self._topic_handler.clear()
