import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import _thread
from time import sleep

from copreus.drivers.dac import DAC
from tests_manual.tools import send_to_topic, get_topics_sub, get_resolution, get_maxvalue


filename = '../tests_unit/config_dac.yaml'


def loop(topics):
    while 1:
        topic = topics["raw"]
        span = get_resolution(filename)
        steps = 10
        stepsize = float(span) / float(steps)
        for i in range(0, steps+1):
            value = int(stepsize * i)
            send_to_topic(filename, topic, value)
            sleep(1)

        topic = topics["volt"]
        span = get_maxvalue(filename)
        steps = 10
        stepsize = float(span) / float(steps)
        for i in range(0, steps+1):
            value = (stepsize * i)
            send_to_topic(filename, topic, value)
            sleep(1)


subs = get_topics_sub(filename)
_loop_thread = _thread.start_new_thread(loop, (subs,))
DAC.standalone(('-c', filename))

