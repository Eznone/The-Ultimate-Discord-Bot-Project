import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from copreus.drivers.bme_280 import BME_280
from pelops.myconfigtools import read_config
from pelops.mymqttclient import MyMQTTClient
from pelops.logging.mylogger import create_logger


def input_handler_temperature(message):
    print("temperature: {}".format(message))


def input_handler_humidity(message):
    print("humidity: {}".format(message))


def input_handler_pressure(message):
    print("pressure: {}".format(message))



filename = '../tests_unit/config_bme_280.yaml'
config = read_config(filename)
logger = create_logger(config["logger"], __name__)
mqttclient = MyMQTTClient(config["mqtt"], logger, True)
mqttclient.connect()
mqttclient.subscribe(config["driver"]["topics-pub"]["temperature"], input_handler_temperature)
mqttclient.subscribe(config["driver"]["topics-pub"]["humidity"], input_handler_humidity)
mqttclient.subscribe(config["driver"]["topics-pub"]["pressure"], input_handler_pressure)

BME_280.standalone(('-c', filename))

