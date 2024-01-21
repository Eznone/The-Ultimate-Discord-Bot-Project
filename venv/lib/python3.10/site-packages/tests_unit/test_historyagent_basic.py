import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pelops.pubsub.mymqttclient import MyMQTTClient
from pelops.logging.mylogger import create_logger
from pelops.myconfigtools import read_config
from pelops.historyagent import HistoryAgent
import time
import threading


# https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', msg=None):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    if msg is None:
        print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    else:
        print('\r%s |%s| %s%% %s %s' % (prefix, bar, percent, suffix, msg), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


class TestHistoryServiceBasic(unittest.TestCase):
    def time_diff_almost_equal(self, history, group_by, places=7):
        if len(history) == 0:
            return

        list = []
        for entry in history:
            list.append(entry["time"])
        list.sort()
        prev = list.pop(0)
        for akt in list:
            self.assertAlmostEqual(prev + group_by, akt, places, "time diff check '(prev + group_by) == akt' failed: ({} + {}) != {}".format(prev, group_by, akt))
            prev = akt

    @classmethod
    def setUpClass(cls):
        cls.main_config = read_config(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) +
                                 "/tests_unit/config_historyagent.yaml")
        cls.logger = create_logger(cls.main_config["logger"], "TestHistoryServiceBasic")
        cls.logger.info("start")
        cls.mqtt_client = MyMQTTClient(cls.main_config["pubsub"], cls.logger)
        cls.mqtt_client.connect()

    def setUp(self):
        self.config = {
            "group-by": 10,
            "aggregator": "avg",
            "use-dataservice": False,
            "dataservice-request-topic-prefix": "/request",
            "dataservice-response-topic-prefix": "/response"
        }
        self.update_available = threading.Event()

    @classmethod
    def tearDownClass(cls):
        cls.mqtt_client.disconnect()
        cls.logger.info("end")

    def test_00create(self):
        hs = HistoryAgent(self.config, 100, "/topic/test", False, self.update_available, self.mqtt_client,
                          self.logger)
        self.assertIsNotNone(hs)
        self.time_diff_almost_equal(hs.history, hs._group_by)

    def test_01start_stop(self):
        hs = HistoryAgent(self.config, 100, "/topic/test", False, self.update_available, self.mqtt_client,
                          self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        self.time_diff_almost_equal(hs.history, hs._group_by)
        hs.stop()

    def test_02direct_avg(self):
        self.config["aggregator"] = "avg"
        hs = HistoryAgent(self.config, 100, "/topic/test", False, self.update_available, self.mqtt_client,
                          self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        hs._aggregation_timestamp = 0
        for i in range(1101):
            hs.add_value(i, i)
        self.assertEqual(hs.history[0]["value"], 104.5)
        self.assertEqual(hs.history[0]["time"], 110)
        self.assertEqual(len(hs.history), 100)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 1100)
        self.time_diff_almost_equal(hs.history, hs._group_by)
        hs.stop()

    def test_03direct_min(self):
        self.config["aggregator"] = "min"
        hs = HistoryAgent(self.config, 100, "/topic/test", False, self.update_available, self.mqtt_client,
                          self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        hs._aggregation_timestamp = 0
        for i in range(1101):
            hs.add_value(i, i)
        self.assertEqual(hs.history[0]["value"], 100)
        self.assertEqual(hs.history[0]["time"], 110)
        self.assertEqual(len(hs.history), 100)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 1100)
        self.time_diff_almost_equal(hs.history, hs._group_by)
        hs.stop()

    def test_04direct_max(self):
        self.config["aggregator"] = "max"
        hs = HistoryAgent(self.config, 100, "/topic/test", False, self.update_available, self.mqtt_client,
                          self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        hs._aggregation_timestamp = 0
        for i in range(1101):
            hs.add_value(i, i)
        self.assertEqual(hs.history[0]["value"], 109)
        self.assertEqual(hs.history[0]["time"], 110)
        self.assertEqual(len(hs.history), 100)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 1100)
        self.time_diff_almost_equal(hs.history, hs._group_by)
        hs.stop()

    def test_05direct_median(self):
        self.config["aggregator"] = "median"
        hs = HistoryAgent(self.config, 100, "/topic/test", False, self.update_available, self.mqtt_client,
                          self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        hs._aggregation_timestamp = 0
        for i in range(1101):
            hs.add_value(i, i)
        self.assertEqual(hs.history[0]["value"], 105)
        self.assertEqual(hs.history[0]["time"], 110)
        self.assertEqual(len(hs.history), 100)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 1100)
        self.time_diff_almost_equal(hs.history, hs._group_by)
        hs.stop()

    def test_06direct_avg_gaps(self):
        self.config["aggregator"] = "avg"
        hs = HistoryAgent(self.config, 10, "/topic/test", False, self.update_available, self.mqtt_client,
                          self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        hs._aggregation_timestamp = 0
        for i in range(15):
            hs.add_value(i, i*20)
        self.assertEqual(hs.history[0]["time"], 190)
        self.assertEqual(hs.history[0]["value"], 9)
        self.assertEqual(hs.history[1]["value"], None)
        self.assertEqual(hs.history[2]["value"], 10)
        self.assertEqual(hs.history[3]["value"], None)
        self.assertEqual(hs.history[4]["value"], 11)
        self.assertEqual(hs.history[5]["value"], None)
        self.assertEqual(hs.history[6]["value"], 12)
        self.assertEqual(hs.history[7]["value"], None)
        self.assertEqual(hs.history[8]["value"], 13)
        self.assertEqual(hs.history[9]["value"], None)
        self.assertEqual(len(hs.history), 10)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 14)
        self.time_diff_almost_equal(hs.history, hs._group_by)
        hs.stop()

    def test_07mqtt_avg(self):
        prog_bar_max = 21
        prog_bar_length = prog_bar_max * 2
        print("takes apprx. 10s ...")
        printProgressBar(0, prog_bar_max, prefix='Progress:', suffix='Complete', length=prog_bar_length)

        self.config["group-by"] = 2
        hs = HistoryAgent(self.config, 10, "/topic/test", True, self.update_available, self.mqtt_client, self.logger)
        self.assertIsNotNone(hs)
        hs.start()

        time.sleep(0.5)
        printProgressBar(1, prog_bar_max, prefix='Progress:', suffix='Complete', length=prog_bar_length)
        for i in range(5*4):
            self.mqtt_client.publish("/topic/test", i)
            time.sleep(0.5)
            printProgressBar(i+1, prog_bar_max, prefix='Progress:', suffix='Complete', length=prog_bar_length)
        time.sleep(0.5)
        printProgressBar(i+2, prog_bar_max, prefix='Progress:', suffix='Complete', length=prog_bar_length)

        self.assertEqual(hs.history[0]["value"], 1)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 19)
        self.time_diff_almost_equal(hs.history, hs._group_by)
        hs.stop()

    def test_08change_length(self):
        hs = HistoryAgent(self.config, 10, "/topic/test", False, self.update_available, self.mqtt_client,
                          self.logger)
        self.assertIsNotNone(hs)
        self.time_diff_almost_equal(hs.history, hs._group_by)
        hs._aggregation_timestamp = 0
        for i in range(101):
            hs.add_value(i, i)
        self.assertEqual(hs.history[0]["value"], 4.5)
        self.assertEqual(hs.history[9]["value"], 94.5)
        self.assertEqual(len(hs.history), 10)
        self.time_diff_almost_equal(hs.history, 10)
        hs.set_max_length(5)
        self.assertEqual(len(hs.history), 5)
        self.assertEqual(hs.history[0]["value"], 54.5)
        self.assertEqual(hs.history[4]["value"], 94.5)
        self.time_diff_almost_equal(hs.history, 10)
        hs.set_max_length(10)
        for j in range(i, i+51):
            hs.add_value(j, j)
        self.assertEqual(len(hs.history), 10)
        self.assertEqual(hs.history[0]["value"], 54.5)
        self.assertEqual(hs.history[9]["value"], 144.5)
        self.time_diff_almost_equal(hs.history, 10)


if __name__ == '__main__':
    unittest.main()
