import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pelops.mymqttclient import MyMQTTClient
from pelops.logging.mylogger import create_logger

from yaml import load

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
import os


def _on_message(msg):
    print("test - received message: '{}'".format(msg))


def get_logger(filename):
    config = load(open(filename, 'r'), Loader=Loader)
    logger = create_logger(config["logger"], __name__)
    return logger


def resister_to_pubs(filename, pos=None, on_message=None):
    mqtt = MyMQTTClient(get_mqtt_config(filename), get_logger(filename))
    if on_message is None:
        on_message = _on_message
    mqtt.connect()
    subs = get_topics_pub(filename, pos)
    for k,s in subs.items():
        print("registering topic '{}'.".format(s))
        mqtt.subscribe(s, on_message)


def send_to_topic(filename, topic, msg):
    print("sending to topic '{}' the value '{}'".format(topic, msg))
    mqtt = MyMQTTClient(get_mqtt_config(filename), get_logger(filename))
    mqtt.on_message = _on_message
    mqtt.connect()
    mqtt.publish(topic, msg)
    mqtt.disconnect()


def get_mqtt_config(filename):
    config = load(open(filename, 'r'), Loader=Loader)
    credentials = load(open(os.path.expanduser(config["mqtt"]["credentials-file"]), 'r'), Loader=Loader)
    config["mqtt"].update(credentials["mqtt"])
    return config["mqtt"]


def get_mqtt(filename):
    mqtt = MyMQTTClient(get_mqtt_config(filename), get_logger(filename))
    return mqtt


def get_topics_pub(filename, pos=None):
    c = get_driver_config(filename, pos)
    pubs = c["topics-pub"]
    result = {}
    for k,v in pubs.items():
        result[k] = v
    return result


def get_resolution(filename, pos=None):
    c = get_driver_config(filename, pos)
    return 2**c["bit"]


def get_maxvalue(filename, pos=None):
    c = get_driver_config(filename, pos)
    return c["maxvalue"]


def get_driver_config(filename, pos=None):
    config = load(open(filename, 'r'), Loader=Loader)
    if pos is None:
        c = config["driver"]
    else:
        c = config["drivers"][pos]
    return c


def get_topics_sub(filename, pos=None):
    c = get_driver_config(filename, pos)
    subs = c["topics-sub"]
    result = {}
    for k,v in subs.items():
        result[k] = v
    return result


def get_mqtt_translations(filename, pos=None):
    c = get_driver_config(filename, pos)
    subs = c["mqtt-translations"]
    return subs


def get_model(filename, pos=None):
    c = get_driver_config(filename, pos)
    return str(c["model"])
