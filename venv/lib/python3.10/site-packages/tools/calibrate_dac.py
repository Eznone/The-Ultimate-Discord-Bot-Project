import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import _thread
from time import sleep, strftime
from copreus.drivers.dac import DAC
from tests_manual.tools import get_driver_config, get_topics_sub, send_to_topic

filename = 'config_dac.yaml'

#send_to_topic(filename, "/test/closed", 0)

# check if use-calibration is set to 'false' ----------
c = get_driver_config(filename)
if c["use-calibration"]:
    raise ValueError("for calibration parameter 'use-calibration' must be set to false "
                     "(currently: {}).".format(c["use-calibration"]))
# -----------------------------------------------------

# create csv file -------------------------------------
data_dac = open("calibration_dac_"+strftime("%Y%m%d-%H%M%S")+".csv", "w")
# -----------------------------------------------------


# start ADC driver ------------------------------------
_adc_thread = _thread.start_new_thread(DAC.standalone, (['-c', filename],))
topic_volt = get_topics_sub(filename)["volt"]
# -----------------------------------------------------


value = -1.0
counter = 0
max = c["maxvalue"]
min = 0
step = 0.5

# get user input for parameters ---------------------
sleep(1)  # wait a little bit - previous tasks should be finished before continuing
print("Default calibration steps: {} V to {} V with step width {} V.".format(min, max, step))
newmin = input("Min value ({} V): ".format(min))
try:
    if float(newmin) > min and float(newmin) < max:
        min = float(newmin)
        print("new value for min: {} V.".format(str(min)))
except ValueError:
    pass
try:
    newmax = input("Max value ({} V): ".format(max))
    if float(newmax) > min and float(newmax) <= max:
        max = float(newmax)
        print("new value for max: {} V.".format(max))
except ValueError:
    pass
try:
    newstep = input("Step value ({} V): ".format(step))
    if float(newstep) >= 0 and float(newstep) <= (max-min):
        step = float(newstep)
        print("new value for step: {} V.".format(step))
except ValueError:
    pass
# -----------------------------------------------------

print("Values used for calibration steps: {} V to {} V with step width {} V.".format(min, max, step))

print("start calibration -------------------------------")
print("volt_out;volt_in;multimeter")
print("# - [ref_value, raw_value]", file=data_dac)

for value in range(int(min*100), int(max*100)+1, int(step*100)):
    if value > int(max*100):
        break
    volt_out = value / 100.0
    print(" ... sending value twice to dac.")
    send_to_topic(filename, topic_volt, volt_out)
    sleep(1)
    send_to_topic(filename, topic_volt, volt_out)
    sleep(2)
    multimeter = -1
    while multimeter < 0:
        mm = input("multimeter value for out value {} V: ".format(volt_out))
        try:
            mm = float(mm)
            accept_value = input("accept entered value {} V (y/N)? ".format(mm))
            if accept_value == "y" or accept_value == "Y":
                multimeter = mm
        except ValueError:
            pass
    print("{};{}".format(volt_out, multimeter))
    # - [ref_value, raw_value]
    print(" - [{}, {}]".format(multimeter, volt_out), file=data_dac)

data_dac.close()
print("done. -------------------------------------------")
print("cleaning up.")
try:
    _thread.interrupt_main()
except KeyboardInterrupt:
    pass
sleep(1)
print("finished.")
