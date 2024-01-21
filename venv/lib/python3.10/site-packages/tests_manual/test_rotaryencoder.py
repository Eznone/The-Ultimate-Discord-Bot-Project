import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from copreus.drivers.rotaryencoder import RotaryEncoder
from tests_manual.tools import resister_to_pubs

filename = '../tests_unit/config_rotaryencoder.yaml'
resister_to_pubs(filename)
RotaryEncoder.standalone(('-c', filename))

