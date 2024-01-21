import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTT_ERR_SUCCESS, MQTT_ERR_NO_CONN
from paho.mqtt.client import LOGGING_LEVEL
import time
from pelops.logging import mylogger
from pelops.pubsub.apubsub import APubSub
from threading import Condition


class MyMQTTClient(APubSub):
    """Wrapper for the paho.mqtt.client. Provides a topic to method mapping, thus enabling that one instance of
    paho.mqtt.client can be used with different incoming message handler. Further, it separates the time of
    registering a subscription from the status of the connection. Subscribed topic/handler pairs are automatically
    registered / unregistered upon connection/disconnection.

    In the configuration file you can choose to either provide an credentials file ("credentials-file") or to add
    the credentials directly ("mqtt-user", "mqtt-password").

    Topics must be provided without any wildcards.

    mqtt-client yaml configuration:
    mqtt:
        mqtt-address: localhost
        mqtt-port: 1883
        credentials-file: ~/credentials.yaml
        retain-messages: True  # optional - default FALSE
        qos: 0  # optional - default 0
        log-level: INFO  # log level for the logger

    credentials-file file:
    mqtt:
        mqtt-password: secret
        mqtt-username: user
    """

    _client = None  # holds an instance of paho.mqtt.client.Client
    _paho_logger = None  # child instance of _logger - for paho.client internal errors

    _retained_messages = None  # if set to true, message broker will be signaled to retain the published messages
    _qos = None  # quality of service values for publish, subscribe, and last will
    _will_topic = None  # topic the last will should be sent ot
    _will_message = None  # message that will be used as last will

    _mid_results = None
    _new_results_available = None

    def __init__(self, config, logger, quiet=False):
        """
        Constructor

        :param config: config yaml structure
        :param logger: instance of logger - a child with name __name__ will be spawned
        :param quiet: boolean - if True, the runtime shell outputs like "Connecting" will be surpressed
        """

        APubSub.__init__(self, config, logger, "MQTT", quiet)

        self._paho_logger = mylogger.get_child(self._logger, "paho")
        self._client = mqtt.Client()
        self._client.enable_logger(self._logger)
        self._mid_results = []
        self._new_results_available = Condition()

        try:
            self._retained_messages = self._config["retain-messages"]
        except KeyError:
            self._retained_messages = False

        try:
            self._qos = self._config["qos"]
        except KeyError:
            self._qos = 0

        try:
            self._connection_timeout = self._config["connection-timeout"]
        except KeyError:
            self._connection_timeout = 30

        try:
            self._ack_timeout = self._config["ack-timeout"]
        except KeyError:
            self._ack_timeout = 5

    def _connect_client(self):
        """Connect to mqtt broker."""
        if self.is_connected.is_set():
            self._logger.warning("_connect_client - is_connect is already set. trying to connect anyway.")
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_unsubscribe = self._on_unsubscribe
        self._client.on_subscribe = self._on_subscribe
        self._client.on_publish = self._on_publish
        self._client.on_message = self._on_message
        self._client.on_log = self._on_log
        self._client.username_pw_set(self._config["mqtt-user"], password=self._config["mqtt-password"])
        self._client.connect(self._config["mqtt-address"], self._config["mqtt-port"], 60)
        self._client.loop_start()
        if not self.is_connected.wait(self._connection_timeout):
            self._logger.warning("_connect_client - connection to broker could not be established.")
            raise RuntimeWarning("_connect_client - connection to broker could not be established.")

    def _add_mid_result(self, mid):
        self._new_results_available.acquire()
        self._mid_results.append(mid)
        self._new_results_available.notify_all()
        self._new_results_available.release()

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        self._logger.debug("_on_subscribe - client {}, userdata {}, mid {}, granted_qos {}"
                           .format(client, userdata, mid, granted_qos))
        if granted_qos[0] != self._qos:
            self._logger.warning("_on_subscribe - requested qos {}, got qos {}".format(self._qos, granted_qos))
        self._add_mid_result(mid)

    def _on_publish(self, client, userdata, mid):
        self._logger.debug("_on_publish - client {}, userdata {}, mid {}"
                           .format(client, userdata, mid))
        self._add_mid_result(mid)

    def _on_unsubscribe(self, client, userdata, mid):
        self._logger.debug("_on_unsubscribe - client {}, userdata {}, mid {}"
                           .format(client, userdata, mid))
        self._add_mid_result(mid)

    def _on_log(self, client, userdata, level, buf):
        self._paho_logger.log(LOGGING_LEVEL[level], buf)

    def clear_retained_messages(self):
        """
        Signal message broker that retained messages should be cleared for all provided topics. Useful for testing.
        Connects and disconnects from broker immediately.
        """
        self._logger.info("clear_retained_messages - start")
        with self._lock_client:
            self._connect_client()
            for topic in self._topic_handler.keys():
                self._logger.info("clear_retained_messages() - clearing topic '{}'.".format(topic))
                self.publish(topic, None)  # publishing a message with zero bytes clears retained value
        self.disconnect()
        self._logger.info("clear_retained_messages - done")

    def connect(self):
        """Connect to the mqtt broker using the provided configuration and registering of all provided message
        handler."""

        self._logger.warning("MyMQTTClient.connect() - Connecting to mqtt.")
        self._logger.info("connect() - Connecting to mqtt.")
        with self._lock_client:
            self._connect_client()
            self._publish_will()
            self._logger.info("connect() - subscribe to topics '{}'.".format(self._topic_handler.keys()))
            self._execute_subscribe(self._topic_handler.keys())

        self._logger.info("connect() - connected.")

    def disconnect(self):
        """Disconnect from mqtt broker and set is_connected to False."""
        self._logger.warning("MyMQTTClient.disconnect() - disconnecting from mqtt")
        self._logger.info("disconnect() - disconnecting from mqtt")
        with self._lock_client:
            self._client.disconnect()
            if not self.is_disconnected.wait(self._connection_timeout):
                self._logger.error("disconnect - connection to broker could not be closed.")
                raise RuntimeError("disconnect - connection to broker could not be closed.")
        self._logger.info("disconnect() - disconnected.")

    def _on_disconnect(self, client, userdata, rc):
        """
        Return code after trying to connect to mqtt broker. If successfully connect, is_disconnected is True.
        Params as defined by paho.mqtt.client. Sets is_disconnected and claers is_disconnected events.

        # The rc parameter indicates the disconnection state. If MQTT_ERR_SUCCESS (0), the callback was called in
        # response to a disconnect() call. If any other value the disconnection was unexpected, such as might be
        # caused by a network error.
        """
        self.is_connected.clear()
        self.is_disconnected.set()

        if rc == 0:
            self._logger.warning("MyMQTTClient - disconnected.")
        else:
            self._logger.error("MyMQTTClient - unexpected disconnection.")

    def _on_connect(self, client, userdata, flags, rc):
        """
        Return code after trying to connect to mqtt broker. If successfully connected, is_connected is True. Params as
        defined by paho.mqtt.client. Sets is_connected and clears is_disconnected events. Raises runtime error if
        result code is != 0.

        # 0: Connection successful
        # 1: Connection refused - incorrect protocol version
        # 2: Connection refused - invalid client identifier
        # 3: Connection refused - server unavailable
        # 4: Connection refused - bad username or password
        # 5: Connection refused - not authorised
        # 6-255: Currently unused.
        """
        if rc == 0:
            self.is_connected.set()
            self.is_disconnected.clear()
            self._logger.warning("MyMQTTClient._on_connect - Connected with result code " + str(rc))
        else:
            if rc == 1:
                msg = "result code 1: Connection refused - incorrect protocol version"
            elif rc == 2:
                msg = "result code 2: Connection refused - invalid client identifier"
            elif rc == 3:
                msg = "result code 3: Connection refused - server unavailable"
            elif rc == 4:
                msg = "result code 4: Connection refused - bad username or password"
            elif rc == 5:
                msg = "result code 5: Connection refused - not authorised"
            else:
                msg = "result code {}: Currently unused.".format(rc)
            self._logger.error("_on_connect - Failed! " + msg)
            raise RuntimeError("_on_connect - Failed! " + msg)

    def _on_message(self, client, userdata, msg):
        """on message handler as defined by paho.mqtt.client. calls every for this topic registered handler with
        the message payload."""
        t = time.time()

        self._logger.info("_on_message - received message '{}' on topic '{}' @{}s. {}".
                  format(msg.payload, msg.topic, t, msg))
        self._stats.recv(msg.topic)

        for handler in self._topic_handler[msg.topic]:
            self._logger.info("_on_message - calling handler '{}' ({}).".format(handler, t))
            try:
                handler(msg.payload)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as err:
                self._logger.exception("{}\n{}".format(err, err.__traceback__))
                raise err

    def publish(self, topic, msg):
        """
        simple wrapper for paho.mqtt.client publish. publishes message if connected; raises RuntimeWarning
        otherwise.

        :param topic: string - mqtt topic
        :param msg: payload
        """
        self._logger.info("publish - publishing to topic '{}' the message '{}'.".format(topic, msg))
        if self.is_connected.is_set():
            self._execute("_execute_publish", self._client.publish, topic, payload=msg,
                          qos=self._qos, retain=self._retained_messages)
            self._stats.sent(topic)
        else:
            self._logger.warning("publish - trying to publish while not being connected to mqtt broker.")
            raise RuntimeWarning("publish - trying to publish while not being connected to mqtt broker.")

    def _publish_will(self):
        """simple wrapper for paho.mqtt.client set_will. publishes will if connected; raises RuntimeWarning
        otherwise."""
        if self._will_message is None or self._will_topic is None:
            self._logger.info("_publish_will - no will provided")
        else:
            self._logger.info("_publish_will - publishing last will")
            if self.is_connected.is_set():
                self._client.will_set(self._will_topic, self._will_message, qos=self._qos, retain=self._retained_messages)
            else:
                self._logger.warning("_publish_will - trying to publish while not being connected to mqtt broker.")
                raise RuntimeWarning("_publish_will - trying to publish while not being connected to mqtt broker.")

    def set_will(self, topic, will):
        """
        Set will parameters. If already connected, it will be published immediately or stored to be published upon
        connection.

        :param topic: string - mqtt topic
        :param will: payload
        """
        self._logger.info("set_will - setting last will to topic '{}' and message '{}'."
                          .format(topic, will))

        if topic is None:
            self._logger.error("set_will - topic ({}) must be not None.".format(topic))
            raise ValueError("set_will - topic ({}) must be not None.".format(topic))

        self._will_topic = topic
        self._will_message = will
        if self.is_connected.is_set():
            self._publish_will()

    def _unsubscribe_postprocessor(self, topics):
        if topics:
            self._execute("_execute_unsubscribe", self._client.unsubscribe, topics)

    def _subscribe_postprocessor(self, topic, handler, ignore_duplicate=False):
        if self.is_connected.is_set():
            self._logger.info("subscribe - activating topic subscription.")
            self._execute_subscribe([topic])

    def _execute_subscribe(self, topics):
        self._logger.debug("_execute_subscribe - start {}".format(topics))
        if not topics:
            self._paho_logger.info("_execute_subscribe - empty topics list. skipping.")
        else:
            argument = []
            for topic in topics:
                arg = (topic, self._qos)
                argument.append(arg)
            self._execute("_execute_subscribe", self._client.subscribe, argument)
        self._logger.debug("_execute_subscribe - end {}".format(topics))

    def _execute(self, caller_name, method, *args, **kwargs):
        self._logger.info("{} - executing".format(caller_name))
        self._logger.debug("__execute: caller_name {}, method {}, args {}, kwargs {}"
                           .format(caller_name, method, args, kwargs))
        try:
            result, mid = method(*args, **kwargs)
        except:
            err = "{} - unknown error".format(caller_name)
            self._logger.error(err)
            raise err

        if result != MQTT_ERR_SUCCESS:
            if result == MQTT_ERR_NO_CONN:
                warning = "{} - MQTT_ERR_NO_CONN".format(caller_name)
                self._logger.warning(warning)
                raise RuntimeWarning(warning)
            else:
                err = "{} - unknown error {}".format(caller_name, result)
                raise RuntimeError(err)

        self._logger.info("{} - waiting for ACK".format(caller_name))
        if not self._wait_for_ack(mid):
            err = "{} - waiting for mid={} ACK timeout. failed to execute command '{}' with args {}, kwargs {}".\
                format(caller_name, mid, method.__name__, args, kwargs)
            self._logger.error(err)
            raise RuntimeError(err)

        self._logger.info("{} - success".format(caller_name))

    def _wait_for_ack(self, mid):
        def _check_queue():
            if mid in self._mid_results:
                self._mid_results.remove(mid)
                return True
            return False

        result = False
        max_time = time.time() + self._ack_timeout
        self._new_results_available.acquire()
        while True:
            max_wait = max_time - time.time()
            if _check_queue():
                result = True
                break
            if self._new_results_available.wait(max_wait):
                if _check_queue():
                    result = True
                    break
            else:
                break
        self._new_results_available.release()
        return result

