import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from copreus.drivers.dht import DHT
from pelops.myconfigtools import read_config
from pelops.mymqttclient import MyMQTTClient
from pelops.logging.mylogger import create_logger
import threading
import random
import time


def input_handler_temperature(message):
    print("--- temperature: {}".format(message))


def input_handler_humidity(message):
    print("--- humidity: {}".format(message))


filename = '../tests_unit/config_dht.yaml'
config = read_config(filename)
config["driver"]["poll-interval"] = 9999
logger = create_logger(config["logger"], __name__)
mqttclient = MyMQTTClient(config["mqtt"], logger, True)
mqttclient.connect()
mqttclient.subscribe(config["driver"]["topics-pub"]["temperature"], input_handler_temperature)
mqttclient.subscribe(config["driver"]["topics-pub"]["humidity"], input_handler_humidity)

dht = DHT(config)
dht_thread = threading.Thread(target=dht.run)
dht_thread.start()
dht._is_started.wait()

print("started")
while dht._is_started:
    t = 5 + random.random() * 5
    print("waiting for {} second.".format(t))
    time.sleep(t)
    print("... sending poll-now request")
    mqttclient.publish(config["driver"]["topics-sub"]["poll-now"], config["driver"]["mqtt-translations"]["poll-now"])

print("finished")