import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import _thread
from time import sleep

from copreus.drivermanager.drivermanager import DriverManager
from pelops.myconfigtools import read_config
from pelops.mymqttclient import MyMQTTClient
from pelops.logging.mylogger import create_logger


def output_loop(topics, cmds):
    sleep(5)
    topic = topics["closed"]
    cmd_true = cmds["closed-true"]
    cmd_false = cmds["closed-false"]
    state = 0
    while 1:
        state = (state + 1) % 2
        if state:
            cmd = cmd_false
        else:
            cmd = cmd_true
        print(cmd)
        mqttclient.publish(topic, cmd)
        sleep(3)


def input_handler_pressed(message):
    print("button_pressed: {}".format(message))


def input_handler_state(message):
    print("button_state: {}".format(message))


def bme280_handler_temperature(message):
    print("bme280-temperature: {}".format(message))


def bme280_handler_humidity(message):
    print("bme280-humidity: {}".format(message))


def bme280_handler_pressure(message):
    print("bme280-pressure: {}".format(message))


def dht_handler_temperature(message):
    print("dht-temperature: {}".format(message))


def dht_handler_humidity(message):
    print("dht-humidity: {}".format(message))


filename = '../tests_unit/config_drivermanager.yaml'
config = read_config(filename)

name_to_listpos = {}
for pos in range(len(config["drivers"])):
    name_to_listpos[config["drivers"][pos]["name"]] = pos

logger = create_logger(config["logger"], __name__)
mqttclient = MyMQTTClient(config["mqtt"], logger, True)
mqttclient.connect()
mqttclient.subscribe(config["drivers"][name_to_listpos["input"]]["topics-pub"]["button_pressed"],
                     input_handler_pressed)
mqttclient.subscribe(config["drivers"][name_to_listpos["input"]]["topics-pub"]["button_state"],
                     input_handler_state)

mqttclient.subscribe(config["drivers"][name_to_listpos["bme280"]]["topics-pub"]["temperature"],
                     bme280_handler_temperature)
mqttclient.subscribe(config["drivers"][name_to_listpos["bme280"]]["topics-pub"]["humidity"],
                     bme280_handler_humidity)
mqttclient.subscribe(config["drivers"][name_to_listpos["bme280"]]["topics-pub"]["pressure"],
                     bme280_handler_pressure)

mqttclient.subscribe(config["drivers"][name_to_listpos["dht"]]["topics-pub"]["temperature"],
                     dht_handler_temperature)
mqttclient.subscribe(config["drivers"][name_to_listpos["dht"]]["topics-pub"]["humidity"],
                     dht_handler_humidity)

_output_loop_thread = _thread.start_new_thread(output_loop,
                                               (config["drivers"][name_to_listpos["output"]]["topics-sub"],
                                                config["drivers"][name_to_listpos["output"]]["mqtt-translations"],))

# -------------- above are preparations - below is starting of the driver manager

DriverManager.standalone(('-c', filename))

