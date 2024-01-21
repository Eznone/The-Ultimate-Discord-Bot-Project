import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import _thread
from time import sleep

from copreus.drivers.output import Output
from pelops.myconfigtools import read_config
from pelops.mymqttclient import MyMQTTClient
from pelops.logging.mylogger import create_logger

filename = '../tests_unit/config_output.yaml'
config = read_config(filename)
logger = create_logger(config["logger"], __name__)
mqttclient = MyMQTTClient(config["mqtt"], logger, True)
mqttclient.connect()

def loop(topics, cmds):
    sleep(2)
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


_loop_thread = _thread.start_new_thread(loop, (config["driver"]["topics-sub"], config["driver"]["mqtt-translations"],))
Output.standalone(('-c', filename))

