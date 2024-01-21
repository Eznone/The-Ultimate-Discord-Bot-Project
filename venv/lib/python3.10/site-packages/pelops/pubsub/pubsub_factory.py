from pelops.pubsub.mymqttclient import MyMQTTClient
from pelops.pubsub.pythonqueue import PythonQueue


class PubSub_Factory:
    @staticmethod
    def create_pubsub_client(config, logger):
        if config["type"].lower() == "mqtt":
            return MyMQTTClient(config, logger)
        elif config["type"].lower() == "queue":
            return PythonQueue(config, logger)
        else:
            err = "unknown pubsub type '{}'. expectecd [MQTT, QUEUE]".format(config["type"])
            logger.error(err)
            raise RuntimeError(err)
