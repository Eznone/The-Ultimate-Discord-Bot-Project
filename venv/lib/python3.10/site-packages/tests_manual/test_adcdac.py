import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import _thread
from time import sleep

from copreus.drivermanager.drivermanager import DriverManager
from tests_manual.tools import send_to_topic, get_topics_sub, get_resolution, get_maxvalue, resister_to_pubs, \
    get_mqtt_translations


filename = '../tests_unit/config_adcdac.yaml'
dac_pos = 1
adc_pos = 0


def loop(topics):
    adc_topic = get_topics_sub(filename, adc_pos)["readnow"]
    adc_command = get_mqtt_translations(filename, adc_pos)["readnow"]
    while 1:
        topic = topics["raw"]
        span = get_resolution(filename, dac_pos)
        steps = 10
        step_size = float(span) / float(steps)
        for i in range(0, steps+1):
            value = int(step_size * i)
            send_to_topic(filename, topic, value)
            sleep(1)
            send_to_topic(filename, adc_topic, adc_command)
            sleep(1)

        topic = topics["volt"]
        span = get_maxvalue(filename, dac_pos)
        steps = 10
        step_size = float(span) / float(steps)
        for i in range(0, steps+1):
            value = (step_size * i)
            send_to_topic(filename, topic, value)
            sleep(1)
            send_to_topic(filename, adc_topic, adc_command)
            sleep(1)


subs = get_topics_sub(filename, dac_pos)
resister_to_pubs(filename, adc_pos)
_loop_thread = _thread.start_new_thread(loop, (subs,))

# -------------- above are preparations - below is starting of the driver manager

DriverManager.standalone(('-c', filename))

#_config, _verbose = DriverManager._args_to_config(('-c', filename))
#dm = DriverManager(_config, _verbose)
#dm._start()
#try:
#    while not dm._is_stopped.wait(0.1):  # timeout is necessary for CTRL+C
#        pass
#except KeyboardInterrupt:
#    pass
#dm._stop()