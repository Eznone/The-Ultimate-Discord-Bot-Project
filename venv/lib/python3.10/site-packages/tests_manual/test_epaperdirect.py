import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from time import sleep, time, strftime
import _thread
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageOps
from copreus.baseclasses.aepaper import EPaperConstants
from copreus.drivers.epaperdirect import EPaperDirect, EPaperMQTTMessageConverter
from pelops.myconfigtools import read_config
from pelops.logging.mylogger import create_logger
from pelops.mymqttclient import MyMQTTClient
import threading
import RPi.GPIO as GPIO


class MessageQueueStats:
    max_count = None
    min_count = None
    akt_count = None
    count_list = None
    message_counter = 0
    _event = None
    TIMEOUT = 5
    RAISE_EXCEPTIONS = False

    def __init__(self, mqtt_client, topic, event):
        self.count_list = []
        mqtt_client.subscribe(topic, self._message_queue_size_handler)
        self._event = event

    def _message_queue_size_handler(self, value):
        value = int(value)
        self.message_counter += 1
        self.akt_count = value
        if self.max_count is None:
            self.min_count = value
            self.max_count = value
        self.min_count = min(value, self.min_count)
        self.max_count = max(value, self.max_count)
        self.count_list.append(value)
        self._event.set()

    def wait_for_message(self, expected_value):
        self._event.wait(timeout=self.TIMEOUT)
        if not self._event.is_set():
            print("RuntimeError - wait_for_message({}) timeout occurred.".format(expected_value))
            if self.RAISE_EXCEPTIONS:
                raise RuntimeError("wait_for_message({}) timeout occurred.".format(expected_value))
        if self.akt_count != expected_value:
            print("ValueError - expected: {} != received: {}".format(expected_value, self.akt_count))
            if self.RAISE_EXCEPTIONS:
                raise ValueError("expected: {} != received: {}".format(expected_value, self.akt_count))
        self._event.clear()

    def wait_for_value(self, expected_value, max_counter=10):
        self._event.wait(timeout=self.TIMEOUT)
        if not self._event.is_set():
            print("RuntimeError - wait_for_value({}) timeout occurred.".format(expected_value))
            if self.RAISE_EXCEPTIONS:
                raise RuntimeError("wait_for_value({}) timeout occurred.".format(expected_value))
        counter = 0
        while self.akt_count != expected_value:
            counter += 1
            self._event.clear()
            self._event.wait(timeout=self.TIMEOUT)
            if not self._event.is_set():
                print("current count list: {}".format(self.count_list))
                print("RuntimeError - wait_for_value({}) timeout occurred.".format(expected_value))
                if self.RAISE_EXCEPTIONS:
                    raise RuntimeError("wait_for_value({}) timeout occurred.".format(expected_value))
            if counter > max_counter:
                print("current count list: {}".format(self.count_list))
                print("RuntimeError - wait_for_value({}) max counter violation occurred ({}>{})."
                      .format(expected_value, counter, max_counter))
                if self.RAISE_EXCEPTIONS:
                    raise RuntimeError("wait_for_value({}) max counter violation occurred ({}>{})."
                                       .format(expected_value, counter, max_counter))
        self._event.clear()


filename = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/tests_unit/config_epaperdirect.yaml"
config = read_config(filename)
logger = create_logger(config["logger"], "TestEPaperDirect")
logger.info("start")
mqtt_client = MyMQTTClient(config["mqtt"], logger)
mqtt_client.connect()

# sudo apt install fonts-freefont-ttf
font_file = "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf"

model = str(config["driver"]["model"])
display_width = EPaperConstants.model[model]["height"]
display_height = EPaperConstants.model[model]["width"]
topic_sub_full_image = config["driver"]["topics-sub"]["full_image"]
topic_sub_partial_image = config["driver"]["topics-sub"]["partial_image"]
topic_sub_switch_frame = config["driver"]["topics-sub"]["switch_frame"]
command_switch_frame = config["driver"]["mqtt-translations"]["switch_frame"]

stats_event = threading.Event()
stats_event.clear()
stats = MessageQueueStats(mqtt_client, config["driver"]["topics-pub"]["message_queue_size"], stats_event)

_ep_thread = _thread.start_new_thread(EPaperDirect.standalone, (('-c', filename),))

try:
    font_small = ImageFont.truetype(font_file, 12)
    font_large = ImageFont.truetype(font_file, 64)
except OSError:
    print("OS Error - can't open font file '{}'.".format(font_file))
    raise

sleep(1)
stats.wait_for_message(0)

base_image = Image.new('L', (display_width, display_height), 255)  # 255: clear the frame
draw = ImageDraw.Draw(base_image)
draw.rectangle((0, 10, display_width, 32), fill=0)
draw.text((30, 16), 'e-Paper Demo', font=font_small, fill=255)
inverted_image = ImageOps.invert(base_image)

print("--- sending full image once ---")
msg = EPaperMQTTMessageConverter.to_full_image(base_image)
mqtt_client.publish(topic_sub_full_image, msg)
stats.wait_for_message(1)
sleep(5)
stats.wait_for_message(0)

print("--- sending inverted full image once ---")
msg = EPaperMQTTMessageConverter.to_full_image(inverted_image)
mqtt_client.publish(topic_sub_full_image, msg)
stats.wait_for_message(1)
sleep(5)
stats.wait_for_message(0)

print("--- switching display frames 4 times ---")
for i in range(4):
    print(i, "SWITCH")
    mqtt_client.publish(topic_sub_switch_frame, "SWITCH")
    stats.wait_for_message(1)
    sleep(5)
    stats.wait_for_message(0)

print("--- test message queue ---")
print("... sending 4 images")
msg = EPaperMQTTMessageConverter.to_full_image(base_image)
mqtt_client.publish(topic_sub_full_image, msg)
mqtt_client.publish(topic_sub_full_image, msg)
mqtt_client.publish(topic_sub_full_image, msg)
mqtt_client.publish(topic_sub_full_image, msg)
print("expecting queues size 4")
stats.wait_for_value(4, 5)
if stats.max_count != 4:
    raise ValueError("stats max_counter {} not as expected {}.".format(stats.max_count, 4))
print("expecting queues size 3")
stats.wait_for_message(3)
print("expecting queues size 2")
stats.wait_for_message(2)
print("expecting queues size 1")
stats.wait_for_message(1)
print("expecting queues size 0")
stats.wait_for_message(0)
print("final stats: {}".format(stats.count_list))
sleep(5)

print("--- sending full image twice ---")
print("... 1")
msg = EPaperMQTTMessageConverter.to_full_image(base_image)
mqtt_client.publish(topic_sub_full_image, msg)
stats.wait_for_message(1)
stats.wait_for_message(0)
print("... 2")
msg = EPaperMQTTMessageConverter.to_full_image(base_image)
mqtt_client.publish(topic_sub_full_image, msg)
stats.wait_for_message(1)
stats.wait_for_message(0)

sleep(5)

print("--- testing partial image ---")
time_large = Image.new('1', (205, 80), 255)  # 255: clear the frame
draw_large = ImageDraw.Draw(time_large)
time_small = Image.new('1', (56, 16), 0)
draw_small = ImageDraw.Draw(time_small)

large_width, large_height = time_large.size
small_width, small_height = time_small.size

minutes = 3
print("... displaying time for the next {} minutes".format(minutes))
for i in range(minutes):
    t = strftime('%H:%M')

    draw_large.rectangle((0, 0, large_width, large_height), fill=255)
    draw_large.text((0, 0), t, font=font_large, fill=0)

    draw_small.rectangle((0, 0, small_width, small_height), fill=0)
    draw_small.text((0,0), t, font=font_small, fill=255)

    list = [
        {
            "x": int((display_width-large_width)/2),
            "y": 40,
            "image": time_large
        },
        {
            "x": display_width-small_width-16,
            "y": 16,
            "image": time_small
        }
    ]
    msg = EPaperMQTTMessageConverter.to_partial_images(list)
    print("updating time to '{}'".format(t))
    mqtt_client.publish(topic_sub_partial_image, msg)
    stats.wait_for_message(1)

    ct = time()
    current_second = int(ct) * 1000
    current_ms = int(ct * 1000.0)

    step_target = 60
    step = (step_target - ct % step_target)
    step_safety = 1

    diff = step + ((current_ms - current_second) / 1000.0) # wait this for the next ms ...

    print("sleeping for {} seconds.".format(diff+step_safety))
    sleep(diff + step_safety)
    stats.wait_for_message(0)

print("--- stopped testing partial image ---")

print("--- erase ---")
print("... sending black and white images. takes approx. 52 seconds.")

white_image = Image.new('1', (EPaperConstants.model[model]["height"], EPaperConstants.model[model]["width"]), 255)  # 255: clear the frame
black_image = Image.new('1', (EPaperConstants.model[model]["height"], EPaperConstants.model[model]["width"]), 0)  # 0: clear the frame
white_draw = ImageDraw.Draw(white_image)
black_draw = ImageDraw.Draw(black_image)
msg_white = EPaperMQTTMessageConverter.to_full_image(white_image)
msg_black = EPaperMQTTMessageConverter.to_full_image(black_image)

for i in range(4):
    print("erase loop {}.".format(i))
    print("sending black image a")
    mqtt_client.publish(topic_sub_full_image, msg_black)
    sleep(1)
    print("sending black image b")
    mqtt_client.publish(topic_sub_full_image, msg_black)
    sleep(5)
    print("sending white image a")
    mqtt_client.publish(topic_sub_full_image, msg_white)
    sleep(1)
    print("sending white image b")
    mqtt_client.publish(topic_sub_full_image, msg_white)
    sleep(5)

stats.wait_for_value(0)
print("final stats: ".format(stats.count_list))
print("--- finished testing ---")

print("cleanup")
sleep(0.5)
mqtt_client.disconnect()
GPIO.cleanup()
sleep(0.5)
print("done")
