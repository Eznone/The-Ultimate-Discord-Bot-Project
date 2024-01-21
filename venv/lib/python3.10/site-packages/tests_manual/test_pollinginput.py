import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from copreus.drivers.pollinginput import PollingInput

from pelops.myconfigtools import read_config
from pelops.mymqttclient import MyMQTTClient
from pelops.logging.mylogger import create_logger


def input_handler_pressed(message):
    print("button_pressed: {}".format(message))


def input_handler_state(message):
    print("button_state: {}".format(message))


filename = '../tests_unit/config_pollinginput.yaml'
config = read_config(filename)
logger = create_logger(config["logger"], __name__)
mqttclient = MyMQTTClient(config["mqtt"], logger, True)
mqttclient.connect()
mqttclient.subscribe(config["driver"]["topics-pub"]["button_pressed"], input_handler_pressed)
mqttclient.subscribe(config["driver"]["topics-pub"]["button_state"], input_handler_state)

PollingInput.standalone(('-c', filename))

