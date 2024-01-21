import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import _thread
from threading import Event
from time import sleep, strftime
from copreus.drivers.adc import ADC
from tests_manual.tools import resister_to_pubs, send_to_topic, get_topics_sub, get_driver_config, get_topics_pub

filename = 'config_adc.yaml'

send_to_topic(filename, "/test/closed", 1)

# check if use-calibration is set to 'false' ----------
c = get_driver_config(filename)
if c["use-calibration"]:
    raise ValueError("for calibration parameter 'use-calibration' must be set to false "
                     "(currently: {}).".format(c["use-calibration"]))
# -----------------------------------------------------


# on_message ------------------------------------------
volt_in = -1.0
received = Event()
received.clear()
topic_volt = get_topics_pub(filename)["volt"]

def volt_in_received(client, userdata, msg):
    if msg.topic == topic_volt:
        global volt_in
        volt_in = float(msg.payload)
        received.set()


resister_to_pubs(filename,on_message=volt_in_received)
# -----------------------------------------------------


# create csv file -------------------------------------
data_adc = open("calibration_adc_"+strftime("%Y%m%d-%H%M%S")+".csv", "w")
# -----------------------------------------------------


# start ADC driver ------------------------------------
_adc_thread = _thread.start_new_thread(ADC.standalone, (['-c', filename],))
topic_readnow = get_topics_sub(filename)["readnow"]
# -----------------------------------------------------

# get number of steps as user input -------------------
sleep(1)  # wait a little bit - previous tasks should be finished before continuing
steps = -1
try:
    while steps <= 0:
        newstep = input("Number of steps (0<x<=64): ")
        if int(newstep) > 0 and int(newstep) <= 64:
            steps = int(newstep)
            print("new value for step: {}.".format(steps))
except ValueError:
    pass
# -----------------------------------------------------

print("start calibration -------------------------------")
print("volt_out;volt_in;multimeter")
print("# - [ref_value, raw_value]", file=data_adc)

for step in range(1, steps+1):
    input("to start next iteration ({}/{}) press enter.".format(step, steps))

    # read value from adc ---------------------------------
    received.clear()
    send_to_topic(filename, topic_readnow, 1)
    received.wait()
    # -----------------------------------------------------

    # get reference value from user -----------------------
    multimeter = -1
    while multimeter < 0:
        mm = input("multimeter value for adc value {} V: ".format(volt_in))
        try:
            mm = float(mm)
            accept_value = input("accept entered value {} V (y/N)? ".format(mm))
            if accept_value == "y" or accept_value == "Y":
                multimeter = mm
        except ValueError:
            pass
    # -----------------------------------------------------

    # write to file/stdout --------------------------------
    print("{};{};{}".format(step, volt_in, multimeter))
    # - [ref_value, raw_value]
    print(" - [{}, {}]".format(multimeter, volt_in), file=data_adc)
    # -----------------------------------------------------

data_adc.close()
print("done. -------------------------------------------")
print("cleaning up.")
try:
    _thread.interrupt_main()
except KeyboardInterrupt:
    pass
sleep(1)
print("finished.")






