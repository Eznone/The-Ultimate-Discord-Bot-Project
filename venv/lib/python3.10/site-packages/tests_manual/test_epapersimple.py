import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from time import sleep
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageOps
from copreus.baseclasses.aepaper import EPaperConstants
from copreus.drivers.epapersimple import EPaperSimple, EPaperMQTTMessageConverter
from pelops.myconfigtools import read_config
from pelops.logging.mylogger import create_logger
from pelops.mymqttclient import MyMQTTClient
import threading
import time
import datetime


class MessageQueueStats:
    max_count = None
    min_count = None
    akt_count = None
    count_list = None
    message_counter = 0
    _event = None
    TIMEOUT = 10
    RAISE_EXCEPTIONS = False

    def __init__(self, mqtt_client, topic, event):
        self.count_list = []
        mqtt_client.subscribe(topic, self._message_queue_size_handler)
        self._event = event

    def to_string(self):
        str = "count: {}; min: {}, max: {}, akt: {}, list: {}."\
            .format(self.message_counter, self.max_count, self.min_count, self.akt_count, self.count_list)
        return str

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
        print("wait_for_message. '{}'".format(expected_value))
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
        print("wait_for_value. '{}'".format(expected_value))
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


filename = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/tests_unit/config_epapersimple.yaml"
config = read_config(filename)
logger = create_logger(config["logger"], "TestEPaperSimple")
logger.info("start =====================================================================================")
mqtt_client = MyMQTTClient(config["mqtt"], logger)
mqtt_client.connect()


# sudo apt install fonts-freefont-ttf
font_file = "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf"

model = str(config["driver"]["model"])
display_width = EPaperConstants.model[model]["height"]
display_height = EPaperConstants.model[model]["width"]
topic_sub_image = config["driver"]["topics-sub"]["image"]

stats_event = threading.Event()
stats_event.clear()
stats = MessageQueueStats(mqtt_client, config["driver"]["topics-pub"]["message_queue_size"], stats_event)

logger.info("--- wiping screen at start-up -------------------------------------------------------")
print("--- wiping screen at start-up ---")
config["driver"]["wipe-screen"]["every-nth-day"] = 0
config["driver"]["wipe-screen"]["time"] = "00:00"
config["driver"]["wipe-screen"]["at-start-up"] = True
eps = EPaperSimple(config)
eps_thread = threading.Thread(target=eps.run)
start = time.time()
eps_thread.start()
eps._is_started.wait()
stats.wait_for_message(1)
stats.wait_for_message(0)
eps.stop()
eps.is_stopped.wait()
eps_thread.join()
stop = time.time()
akt_diff = stop-start
expected_min_diff = eps._update_time * 6  # six color changes
print("... possibly a success: {}. measured {} seconds. expected minimum {} seconds."
      .format((expected_min_diff<=akt_diff), akt_diff, expected_min_diff))
time.sleep(1)

logger.info("--- sending two images -------------------------------------------------------")
print("--- sending two images ---")
config["driver"]["wipe-screen"]["every-nth-day"] = 0
config["driver"]["wipe-screen"]["time"] = "00:00"
config["driver"]["wipe-screen"]["at-start-up"] = False
eps = EPaperSimple(config)
eps_thread = threading.Thread(target=eps.run)
eps_thread.start()
eps._is_started.wait()

try:
    font_small = ImageFont.truetype(font_file, 12)
    font_large = ImageFont.truetype(font_file, 64)
except OSError:
    print("OS Error - can't open font file '{}'.".format(font_file))
    raise

regular_image = Image.new('L', (display_width, display_height), 255)  # 255: clear the frame
draw = ImageDraw.Draw(regular_image)
draw.rectangle((0, 10, display_width, 32), fill=0)
draw.text((30, 16), 'e-Paper Demo', font=font_small, fill=255)

print("... sending regular image")
msg = EPaperMQTTMessageConverter.to_full_image(regular_image)
mqtt_client.publish(topic_sub_image, msg)
stats.wait_for_message(1)
stats.wait_for_message(0)

sleep(1)

print("... sending inverted image")
inverted_image = ImageOps.invert(regular_image)
msg = EPaperMQTTMessageConverter.to_full_image(inverted_image)
mqtt_client.publish(topic_sub_image, msg)
stats.wait_for_message(1)
stats.wait_for_message(0)

eps.stop()
eps.is_stopped.wait()
eps_thread.join()

logger.info("--- test message-queue -------------------------------------------------------")
print("--- test message-queue (sending 4 regular and 1 inverted image - 3 regular images should be discarded) ---")
config["driver"]["wipe-screen"]["every-nth-day"] = 0
config["driver"]["wipe-screen"]["time"] = "00:00"
config["driver"]["wipe-screen"]["at-start-up"] = False

msg_regular = EPaperMQTTMessageConverter.to_full_image(regular_image)
msg_inverted = EPaperMQTTMessageConverter.to_full_image(inverted_image)

eps = EPaperSimple(config)
eps_thread = threading.Thread(target=eps.run)
eps_thread.start()
eps._is_started.wait()
start = time.time()

mqtt_client.publish(topic_sub_image, msg_regular)
mqtt_client.publish(topic_sub_image, msg_regular)
mqtt_client.publish(topic_sub_image, msg_regular)
mqtt_client.publish(topic_sub_image, msg_regular)
mqtt_client.publish(topic_sub_image, msg_regular)
mqtt_client.publish(topic_sub_image, msg_regular)
mqtt_client.publish(topic_sub_image, msg_regular)
mqtt_client.publish(topic_sub_image, msg_regular)
mqtt_client.publish(topic_sub_image, msg_inverted)

stats.wait_for_value(0)
diff = time.time() - start
print("sended 9 images and displayed 2 in {} seconds. current stats: {}".format(diff, stats.to_string()))
if stats.count_list != [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0]:
    raise RuntimeError("Not expected sequence of message queue sizes. received {}; "
                       "expected [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0].".format(stats.count_list))

eps.stop()
eps.is_stopped.wait()
eps_thread.join()


logger.info("--- wipe screen timer -------------------------------------------------------")
print("--- wipe screen timer (restores to regular image) ---")
# set time for wipe screen to next full minute that is at least 10 seconds away (but not longer than 60 seconds)
now = time.time()
next_full_minute = 60 - (now % 60)
if next_full_minute < 20:
    next_full_minute += 60
now = datetime.datetime.now()
target = now + datetime.timedelta(seconds=next_full_minute)
target_time = "{:02d}:{:02d}".format(target.hour, target.minute)
print("... wipe screen scheduled to: {} / in {} seconds.".format(target_time, next_full_minute))
config["driver"]["wipe-screen"]["every-nth-day"] = 1
config["driver"]["wipe-screen"]["time"] = target_time
config["driver"]["wipe-screen"]["at-start-up"] = False

eps = EPaperSimple(config)
eps_thread = threading.Thread(target=eps.run)
eps_thread.start()
eps._is_started.wait()
mqtt_client.publish(topic_sub_image, msg_regular)

print("... waiting for approximately {:0.2f} seconds.".format(next_full_minute))

temp = stats.TIMEOUT
stats.TIMEOUT=next_full_minute+30
stats.wait_for_message(1)
stats.TIMEOUT = temp
stats.wait_for_value(0)

eps.stop()
eps.is_stopped.wait()
eps_thread.join()

print("... finished wipe screen timer")

print("final stats: ".format(stats.count_list))
if stats.max_count != 1 and stats.min_count != 0:
    raise RuntimeError("states are not as expected: max {} vs. max target 1 and min {} vs. min target 0."
                       .format(stats.max_count, stats.min_count))


logger.info("--- finished testing -------------------------------------------------------")
print("--- finished testing ---")

print("cleanup")
sleep(0.5)
mqtt_client.disconnect()
sleep(0.5)
print("done")
logger.info("stop ======================================================================================")