import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pelops.pubsub.mymqttclient import MyMQTTClient
from pelops.logging.mylogger import create_logger
from pelops.myconfigtools import read_config
from pelops.historyagent import HistoryAgent
from datetime import datetime, timedelta
import time
import threading
import json


class TestHistoryServiceAggregatedImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._TEST_00 = True
        cls._TEST_01 = True
        cls._TEST_02 = True
        cls._TEST_03 = True
        cls._TEST_04 = True
        cls._TEST_05 = True

        cls.main_config = read_config(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) +
                                 "/tests_unit/config_historyagent.yaml")
        cls.logger = create_logger(cls.main_config["logger"], "TestHistoryServiceAggregatedImport")
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

    def tearDown(self):
        self.mqtt_client.unsubscribe_all()

    def _time_diff_almost_equal(self, history, group_by, places=7):
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

    def _no_none_values(self, history, pos_from=0, pos_to=None):
        if pos_to is None:
            pos_to = len(history) - 1
        for i in range(pos_from, pos_to+1):
            entry = history[i]
            self.assertIsNotNone(entry["value"])

    def test_00aggregated_import_all(self):
        if self._TEST_00 == False:
            return None

        event = threading.Event()
        event.clear()

        def mqtt_request_handler(message):
            request = json.loads(message.decode("utf-8"))
            first = datetime.strptime(request["from"], HistoryAgent._TIME_FORMAT)
            last = datetime.strptime(request["to"], HistoryAgent._TIME_FORMAT)
            group_by = float(request["group-by"]) / 3
            next = first
            response = {"data": []}
            value = 0
            while next < last:
                response["data"].append({"time": next.strftime(HistoryAgent._TIME_FORMAT), "value": value})
                next = next + timedelta(seconds=group_by)
                value += 1

            response["len"] = value
            response["first"] = first.strftime(HistoryAgent._TIME_FORMAT)
            response["last"] = last.strftime(HistoryAgent._TIME_FORMAT)
            response["topic"] = "/topic/test"
            response["version"] = 2
            response["group-by"] = group_by

            self.mqtt_client.publish("/response/topic/test", json.dumps(response))
            event.set()

        self.mqtt_client.subscribe("/request/topic/test", mqtt_request_handler)
        self.config["use-dataservice"] = True
        hs = HistoryAgent(self.config, 10, "/topic/test", False, self.update_available, self.mqtt_client, self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        event.wait(5)
        time.sleep(1)
        self.assertEqual(len(hs.history), 10)
        self.assertEqual(hs.history[9]["value"], 35)
        self.assertEqual(len(hs._aggregation), 0)
        self._time_diff_almost_equal(hs.history, hs._group_by)
        self._no_none_values(hs.history)
        self.mqtt_client.unsubscribe("/request/topic/test", mqtt_request_handler)
        hs.stop()

    def test_01aggregated_import_all_shift(self):
        if self._TEST_01 == False:
            return None

        event = threading.Event()
        def mqtt_request_handler(message):
            request = json.loads(message.decode("utf-8"))
            first = datetime.strptime(request["from"], HistoryAgent._TIME_FORMAT)
            last = datetime.strptime(request["to"], HistoryAgent._TIME_FORMAT)
            group_by = float(request["group-by"]) / 3
            first -= timedelta(seconds=2 * float(request["group-by"]) / 3)
            last += timedelta(seconds=float(request["group-by"]) / 3)
            next = first
            response = {"data": []}
            value = 0
            while next < last:
                response["data"].append({"time": next.strftime(HistoryAgent._TIME_FORMAT), "value": value})
                next = next + timedelta(seconds=group_by)
                value += 1
            response["len"] = value
            response["first"] = first.strftime(HistoryAgent._TIME_FORMAT)
            response["last"] = last.strftime(HistoryAgent._TIME_FORMAT)
            response["topic"] = "/topic/test"
            response["version"] = 2
            response["group-by"] = group_by

            self.mqtt_client.publish("/response/topic/test", json.dumps(response))
            event.set()

        self.mqtt_client.subscribe("/request/topic/test", mqtt_request_handler)
        self.config["use-dataservice"] = True
        hs = HistoryAgent(self.config, 10, "/topic/test", False, self.update_available, self.mqtt_client, self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        event.wait(5)
        time.sleep(1)
        self.assertEqual(len(hs.history), 10)
        self.assertEqual(hs.history[9]["value"], 39)
        self.assertEqual(len(hs._aggregation), 0)
        self._time_diff_almost_equal(hs.history, hs._group_by)
        self._no_none_values(hs.history)
        self.mqtt_client.unsubscribe("/request/topic/test", mqtt_request_handler)
        hs.stop()

    def test_02aggregated_import_all_shift_gap(self):

        if self._TEST_02 == False:
            return None

        event = threading.Event()

        def mqtt_request_handler(message):
            request = json.loads(message.decode("utf-8"))
            first = datetime.strptime(request["from"], HistoryAgent._TIME_FORMAT)
            last = datetime.strptime(request["to"], HistoryAgent._TIME_FORMAT)
            group_by = float(request["group-by"]) / 3
            first -= timedelta(seconds=2 * float(request["group-by"]) / 3)
            last += timedelta(seconds=float(request["group-by"]) / 3) - timedelta(seconds=group_by*9)
            next = first
            response = {"data": []}
            value = 0
            while next < last:
                response["data"].append({"time": next.strftime(HistoryAgent._TIME_FORMAT), "value": value})
                next = next + timedelta(seconds=group_by)
                value += 1
            response["len"] = value
            response["first"] = first.strftime(HistoryAgent._TIME_FORMAT)
            response["last"] = last.strftime(HistoryAgent._TIME_FORMAT)
            response["topic"] = "/topic/test"
            response["version"] = 2
            response["group-by"] = group_by
            self.mqtt_client.publish("/response/topic/test", json.dumps(response))
            event.set()

        self.mqtt_client.subscribe("/request/topic/test", mqtt_request_handler)
        self.config["use-dataservice"] = True
        hs = HistoryAgent(self.config, 10, "/topic/test", False, self.update_available, self.mqtt_client, self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        event.wait(5)
        time.sleep(1)
        self.assertEqual(len(hs.history), 10)
        self.assertEqual(hs.history[8]["value"], 30)
        self._no_none_values(hs.history, pos_from=0, pos_to=8)
        self.assertIsNone(hs.history[9]["value"])
        self._no_none_values(hs.history, pos_from=10)
        self.assertEqual(len(hs._aggregation), 0)
        self._time_diff_almost_equal(hs.history, hs._group_by)
        self.mqtt_client.unsubscribe("/request/topic/test", mqtt_request_handler)
        hs.stop()

    def test_03aggregated_import_partial(self):

        if self._TEST_03 == False:
            return None

        event = threading.Event()

        def mqtt_request_handler(message):
            request = json.loads(message.decode("utf-8"))
            first = datetime.strptime(request["from"], HistoryAgent._TIME_FORMAT)
            last = datetime.strptime(request["to"], HistoryAgent._TIME_FORMAT)
            group_by = float(request["group-by"]) / 3
            next = first
            response = {"data": []}
            value = 0
            while next < last:
                response["data"].append({"time": next.strftime(HistoryAgent._TIME_FORMAT), "value": value})
                next = next + timedelta(seconds=group_by)
                value += 1

            response["len"] = value
            response["first"] = first.strftime(HistoryAgent._TIME_FORMAT)
            response["last"] = last.strftime(HistoryAgent._TIME_FORMAT)
            response["topic"] = "/topic/test"
            response["version"] = 2
            response["group-by"] = group_by

            self.mqtt_client.publish("/response/topic/test", json.dumps(response))
            event.set()

        self.config["use-dataservice"] = True
        hs = HistoryAgent(self.config, 20, "/topic/test", False, self.update_available, self.mqtt_client, self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        t = time.time() - 100
        hs._aggregation_timestamp = t
        for i in range(101):
            hs.add_value(i, t + i)

        self.assertEqual(hs.history[0]["value"], 4.5)
        self.assertEqual(len(hs.history), 10)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 100)
        self.mqtt_client.subscribe("/request/topic/test", mqtt_request_handler)
        hs._request_dataservice_response()
        event.wait(5)
        time.sleep(2)
        self._time_diff_almost_equal(hs.history, hs._group_by)
        self.assertEqual(len(hs.history), 20)
        self.assertEqual(hs.history[9]["value"], 35)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 100)
        self._no_none_values(hs.history)
        self.mqtt_client.unsubscribe("/request/topic/test", mqtt_request_handler)
        hs.stop()

    def test_04aggregated_import_partial_shift(self):

        if self._TEST_04 == False:
            return None

        event = threading.Event()

        def mqtt_request_handler(message):
            request = json.loads(message.decode("utf-8"))
            first = datetime.strptime(request["from"], HistoryAgent._TIME_FORMAT)
            last = datetime.strptime(request["to"], HistoryAgent._TIME_FORMAT)
            group_by = float(request["group-by"]) / 3
            first -= timedelta(seconds=2 * float(request["group-by"]) / 3)
            last += timedelta(seconds=float(request["group-by"]) / 3)
            next = first
            response = {"data": []}
            value = 0
            while next < last:
                response["data"].append({"time": next.strftime(HistoryAgent._TIME_FORMAT), "value": value})
                next = next + timedelta(seconds=group_by)
                value += 1

            response["len"] = value
            response["first"] = first.strftime(HistoryAgent._TIME_FORMAT)
            response["last"] = last.strftime(HistoryAgent._TIME_FORMAT)
            response["topic"] = "/topic/test"
            response["version"] = 2
            response["group-by"] = group_by

            self.mqtt_client.publish("/response/topic/test", json.dumps(response))
            event.set()

        self.config["use-dataservice"] = True
        hs = HistoryAgent(self.config, 20, "/topic/test", False, self.update_available, self.mqtt_client, self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        t = time.time() - 100
        hs._aggregation_timestamp = t
        for i in range(101):
            hs.add_value(i, t + i)

        self.assertEqual(hs.history[0]["value"], 4.5)
        self.assertEqual(len(hs.history), 10)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 100)

        self.mqtt_client.subscribe("/request/topic/test", mqtt_request_handler)
        hs._request_dataservice_response()
        event.wait(5)
        time.sleep(2)
        self._time_diff_almost_equal(hs.history, hs._group_by)
        self.assertEqual(len(hs.history), 20)
        self.assertEqual(hs.history[9]["value"], 37)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 100)
        self._no_none_values(hs.history)
        self.mqtt_client.unsubscribe("/request/topic/test", mqtt_request_handler)
        hs.stop()

    def test_05aggregated_import_partial_shift_gap(self):

        if self._TEST_05 == False:
            return None

        event = threading.Event()

        def mqtt_request_handler(message):
            request = json.loads(message.decode("utf-8"))
            first = datetime.strptime(request["from"], HistoryAgent._TIME_FORMAT)
            last = datetime.strptime(request["to"], HistoryAgent._TIME_FORMAT)
            group_by = float(request["group-by"]) / 3
            first -= timedelta(seconds=2 * float(request["group-by"]) / 3)
            last += timedelta(seconds=float(request["group-by"]) / 3) - timedelta(seconds=group_by*36)
            next = first
            response = {"data": []}
            value = 0
            while next < last:
                response["data"].append({"time": next.strftime(HistoryAgent._TIME_FORMAT), "value": value})
                next = next + timedelta(seconds=group_by)
                value += 1

            response["len"] = value
            response["first"] = first.strftime(HistoryAgent._TIME_FORMAT)
            response["last"] = last.strftime(HistoryAgent._TIME_FORMAT)
            response["topic"] = "/topic/test"
            response["version"] = 2
            response["group-by"] = group_by

            self.mqtt_client.publish("/response/topic/test", json.dumps(response))
            event.set()

        self.config["use-dataservice"] = True
        hs = HistoryAgent(self.config, 20, "/topic/test", False, self.update_available, self.mqtt_client, self.logger)
        self.assertIsNotNone(hs)
        hs.start()
        t = time.time() - 100
        hs._aggregation_timestamp = t
        for i in range(101):
            hs.add_value(i, t + i)

        self.assertEqual(hs.history[0]["value"], 4.5)
        self.assertEqual(len(hs.history), 10)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 100)

        self.mqtt_client.subscribe("/request/topic/test", mqtt_request_handler)
        hs._request_dataservice_response()
        event.wait(5)
        time.sleep(1)
        self._time_diff_almost_equal(hs.history, hs._group_by)
        self.assertEqual(len(hs.history), 20)
        self.assertEqual(hs.history[8]["value"], 33)
        self._no_none_values(hs.history, pos_from=0, pos_to=8)
        self.assertIsNone(hs.history[9]["value"])
        self._no_none_values(hs.history, pos_from=10)
        self.assertEqual(len(hs._aggregation), 1)
        self.assertEqual(hs._aggregation[0], 100)
        self.mqtt_client.unsubscribe("/request/topic/test", mqtt_request_handler)
        hs.stop()


if __name__ == '__main__':
    unittest.main()
