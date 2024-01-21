from threading import Event
from copreus import version
from pelops.abstractmicroservice import AbstractMicroservice


class ADriver(AbstractMicroservice):
    """Base class that all drivers must implement.

     * Provides MQtt-related functionality like subcribe to topics, publish to topics, start/stop mqtt client.
     * start/stop the service.
     * apply basic configuration from json object
     * standalone enabling methods - each driver can be used on its own from the command line.

    A yaml file must contain two root blocks:
     * mqtt - mqtt-address, mqtt-port, and path to credentials file credentials-file (a file consisting of two entries:
     mqtt-user, mqtt-password)
     * driver or drivers. drivers is a list of driver entries with two additional parameters per driver: active and
     name. a driver entry contains at least (driver implementation might add additional ones): type, name, topic-pub
     (list of key/value pairs), topic-sub (list of key/value pairs), and mqtt-translations (what are the
     commands/states-values that are transmitted via mqtt. only where necessary).
    """

    _version = version

    _topics_pub = None  # list of topics this driver publishes to
    _topics_sub = None  # list of topics this driver listens to
    _type = None  # unique identifier of driver class. usually the class name.
    _name = None  # name of driver instance. should be unique in combination with _type.
    is_stopped = None  # threading.Event that is true if the driver is not running. False between start() and stop().
    _mqtt_translations = None  # contains all mqtt commands/states and their mqtt.payload representations.
    _ui_commands = None

    def __init__(self, config, mqtt_client=None, logger=None, logger_name=None, stdout_log_level=None, no_gui=None,
                 manage_monitoring_agent=True):
        AbstractMicroservice.__init__(self, config, "driver", mqtt_client, logger, logger_name,
                                      stdout_log_level=stdout_log_level, no_gui=no_gui,
                                      manage_monitoring_agent=manage_monitoring_agent)

        self._type = self.__class__.__name__
        if self._type.upper() != self._config["type"].upper():
            self._logger.error("ADriver.__init__ - Type of class ({}) is different than type of config ({}).".format(self._type.upper(), self._config["type"].upper()))
            raise TypeError("Type of class ({}) is different than type of config ({}).".format(self._type.upper(), self._config["type"].upper()))

        try:
            self._name = self._config["name"]
        except KeyError:
            self._name = self._type

        if self._logger is not None:
            self._logger = self._logger.getChild(self._name)

        self._topics_pub = {}
        try:
            self._add_topics_pub(self._config["topics-pub"])
        except KeyError:
            pass

        self._topics_sub = {}
        try:
            self._add_topics_sub(self._config["topics-sub"])
        except KeyError:
            pass

        self._mqtt_translations = {}
        try:
            self._add_mqtt_translations(self._config["mqtt-translations"])
        except KeyError:
            pass

        self.is_stopped = Event()
        self.is_stopped.set()

        self._ui_commands = {}

    def load_ui_commands(self, prefix=""):
        for key, value in self._ui_commands.items():
            self._add_ui_command(prefix+key, value)

    def get_name(self):
        return self._name

    def get_config(self):
        return self._config

    def get_short_info(self):
        return "[{}] type:{} is_stopped:{}".format(self._name, self._type, self.is_stopped.is_set())

    def _add_topics_pub(self, topics_pub):
        for k,v in topics_pub.items():
            self._topics_pub[k] = v

    def _add_topics_sub(self, topics_sub):
        for k,v in topics_sub.items():
            self._topics_sub[k] = v

    def _add_mqtt_translations(self, mqtt_translations):
        for k, v in mqtt_translations.items():
            self._mqtt_translations[k] = str(v).encode('UTF-8')

    def _publish_value(self, topic, value):
        """Wrapper method to publish a value to the given topic."""
        self._mqtt_client.publish(topic, value)
        self._logger.info("ADriver._publish_value - {}: {}".format(topic, str(value)))

    @classmethod
    def _get_description(cls):
        return "Device driver for '{}'\n" \
               "In Greek mythology, Copreus (Κοπρεύς) was King Eurystheus' herald. He announced Heracles' Twelve " \
               "Labors. This script starts a driver driver on a raspberry pi and connects the device to MQTT. " \
               "Thus, copreus takes commands from the king (MQTT) and tells the hero (Device) what its labors " \
               "are. Further, copreus reports to the king whatever the hero has to tell him.".format(cls.__name__)

    def _start(self):
        """AbstractMicroservice._start"""
        self.is_stopped.clear()
        if self._manage_ui:
            self._logger.info("loading ui commands")
            self.load_ui_commands()
        else:
            self._logger.info("skipping loading ui commands")
        self._driver_start()
        self._logger.warning("Driver '{}.{}' started".format(self._type, self._name))

    def _stop(self):
        """AbstractMicroservice._stop"""
        self._driver_stop()
        self.is_stopped.set()
        self._logger.warning("Driver '{}.{}' stopped".format(self._type, self._name))

    def _driver_start(self):
        raise NotImplementedError

    def _driver_stop(self):
        raise NotImplementedError

    def runtime_information(self):
        info = {
            "name": self._name,
            "type": self._type
        }
        info.update(self._runtime_information())
        return info

    def _runtime_information(self):
        raise NotImplementedError

    def config_information(self):
        info = {
            "name": self._name,
            "type": self._type
        }
        info.update(self._config_information())
        return info

    def _config_information(self):
        raise NotImplementedError
