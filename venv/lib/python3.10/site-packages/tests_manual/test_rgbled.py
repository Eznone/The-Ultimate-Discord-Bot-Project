import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import _thread
from time import sleep
import json
from copreus.drivers.rgbled import RGBLed, message_schema
from pelops.myconfigtools import read_config
from pelops.mymqttclient import MyMQTTClient
from pelops.logging.mylogger import create_logger

filename = '../tests_unit/config_rgbled.yaml'
config = read_config(filename)
logger = create_logger(config["logger"], __name__)
mqttclient = MyMQTTClient(config["mqtt"], logger, True)
mqttclient.connect()


colors = ["BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "AQUA", "MAGENTA"]


def show_colors(topic):
    print("show_colors")
    for color in colors:
        struct = {
            "color": color
        }
        print(" - {}".format(struct))
        mqttclient.publish(topic, json.dumps(struct))
        sleep(0.2)


def show_rgb(topic):
    print("show_rgb")
    for r in range(2):
        for g in range(2):
            for b in range(2):
                struct = {
                    "r": r == 1,
                    "g": g == 1,
                    "b": b == 1
                }
                print(" - {}".format(struct))
                mqttclient.publish(topic, json.dumps(struct))
                sleep(0.2)


def show_blink_symmetric(topic):
    print("show_blink_symmetric")
    struct = {
        "color_a": "BLUE",
        "color_b": "GREEN",
        "delay": 0.2
    }
    print(" - {}".format(struct))
    mqttclient.publish(topic, json.dumps(struct))
    sleep(2)


def show_blink_asymmetric(topic):
    print("show_blink_asymmetric")
    struct = {
        "color_a": "RED",
        "color_b": "YELLOW",
        "delay_a": 0.1,
        "delay_b": 0.4
    }
    print(" - {}".format(struct))
    mqttclient.publish(topic, json.dumps(struct))
    sleep(2)


def loop(topics, ):
    sleep(2)
    topic = topics["command"]
    while 1:
        show_colors(topic)
        sleep(0.5)
        show_rgb(topic)
        sleep(0.5)
        show_blink_symmetric(topic)
        show_blink_asymmetric(topic)


_loop_thread = _thread.start_new_thread(loop, (config["driver"]["topics-sub"], ))
RGBLed.standalone(('-c', filename))

