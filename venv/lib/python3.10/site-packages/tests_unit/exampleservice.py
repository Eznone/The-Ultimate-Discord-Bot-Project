from pelops.abstractmicroservice import AbstractMicroservice


class ExampleService(AbstractMicroservice):
    _version = 2
    start_topic = None
    stop_topic = None
    stop_me_topic = None

    def __init__(self, config, pubsub_client=None, logger=None, stdout_log_level=None, no_gui=None):
        AbstractMicroservice.__init__(self, config, "test", pubsub_client, logger, logger_name="service",
                                      manage_monitoring_agent=False, no_gui=True)
        self.start_topic = self._config["start"]
        self.stop_topic = self._config["stop"]
        self.stop_me_topic = self._config["stop-me"]

    def _stop_me_handler(self, message):
        self._logger.info("received stop-me signal on topic '{}'".format(self.stop_me_topic))
        self.asyncstop()

    def _start(self):
        self._logger.info("sending 'start' to topic '{}'".format(self.start_topic))
        self._logger.info("start - subscribing")
        self._pubsub_client.subscribe(self.stop_me_topic, self._stop_me_handler)
        self._logger.info("start - publishing")
        self._pubsub_client.publish(self.start_topic, "start")

    def _stop(self):
        self._logger.info("sending 'stop' to topic '{}'".format(self.stop_topic))
        self._logger.debug("_stop - 1")
        self._pubsub_client.unsubscribe(self.stop_me_topic, self._stop_me_handler)
        self._logger.debug("_stop - 2")
        self._pubsub_client.publish(self.stop_topic, "stop")
        self._logger.debug("_stop - 3")

    def runtime_information(self):
        return {}

    def config_information(self):
        return {}

    @classmethod
    def _get_description(cls):
        return "TestService"

    @classmethod
    def _get_schema(cls):
        schema = {
            "test": {
                "description": "test configuration",
                "type": "object",
                "properties": {
                    "start": {
                        "description": "start",
                        "type": "string",
                    },
                    "stop": {
                        "description": "stop",
                        "type": "string",
                    },
                    "stop-me": {
                        "description": "stop-me",
                        "type": "string"
                    }
                },
                "required": ["start", "stop", "stop-me"]
            }
        }
        return schema

