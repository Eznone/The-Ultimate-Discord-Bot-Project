import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from copreus.drivers.input import Input

from pelops.myconfigtools import read_config
from pelops.mymqttclient import MyMQTTClient
from pelops.logging.mylogger import create_logger


def input_handler_hold(message):
    print("button_hold: {}".format(message))


def input_handler_pressed(message):
    print("button_pressed: {}".format(message))


def input_handler_released(message):
    print("button_released: {}".format(message))


def input_handler_state(message):
    print("button_state: {}".format(message))


filename = '../tests_unit/config_input.yaml'
config = read_config(filename)
logger = create_logger(config["logger"], __name__)
mqttclient = MyMQTTClient(config["mqtt"], logger, True)
mqttclient.connect()
mqttclient.subscribe(config["driver"]["topics-pub"]["button_pressed"], input_handler_pressed)
mqttclient.subscribe(config["driver"]["topics-pub"]["button_released"], input_handler_released)
mqttclient.subscribe(config["driver"]["topics-pub"]["button_state"], input_handler_state)
mqttclient.subscribe(config["driver"]["topics-pub"]["button_hold"], input_handler_hold)

Input.standalone(('-c', filename))

