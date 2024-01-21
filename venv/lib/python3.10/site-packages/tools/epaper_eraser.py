import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from time import sleep
import _thread

from PIL import Image
from PIL import ImageDraw

from copreus.baseclasses.aepaper import AEPaper, EPaperConstants, EPaperMQTTMessageConverter
from tests_manual.tools import get_mqtt, get_model

print("send a lot of white images to the epaper - hopefully removing all 'ghosts'.")

filename = 'config_epaperdirect.yaml'
number_of_loops = 4
model = get_model(filename)

_ep_thread = _thread.start_new_thread(AEPaper.standalone, (['-c', filename],))

mqtt = get_mqtt(filename)
mqtt.connect()

white_image = Image.new('1', (EPaperConstants.model[model]["height"], EPaperConstants.model[model]["width"]), 255)  # 255: clear the frame
black_image = Image.new('1', (EPaperConstants.model[model]["height"], EPaperConstants.model[model]["width"]), 0)  # 0: clear the frame
white_draw = ImageDraw.Draw(white_image)
black_draw = ImageDraw.Draw(black_image)
msg_white = EPaperMQTTMessageConverter.to_full_image(white_image)
msg_black = EPaperMQTTMessageConverter.to_full_image(black_image)

print("sending {}x a white-black full image combinations to the epaper.".format(number_of_loops))
for i in range(0,number_of_loops):
    print("send black image")
    mqtt.client.publish("/w/thermostat/display/full_image_twice", msg_black)
    sleep(5)
    print("send white image")
    mqtt.client.publish("/w/thermostat/display/full_image_twice", msg_white)
    sleep(5)

mqtt.disconnect()
print("done")
