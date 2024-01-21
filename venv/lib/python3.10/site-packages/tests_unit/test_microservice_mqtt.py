import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pelops.pubsub.mymqttclient import MyMQTTClient
from pelops.myconfigtools import read_config
from pelops.logging.mylogger import create_logger
from tests_unit.exampleservice import ExampleService
import threading
import time


class TestMicroserviceMQTT(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.filename = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/tests_unit/config_mqtt.yaml"
        cls.main_config = read_config(cls.filename)
        cls.logger = create_logger(cls.main_config["logger"], "test")
        cls.logger.info("start ==============================================")

    @classmethod
    def tearDownClass(cls):
        cls.logger.info("end ================================================")

    def setUp(self):
        self.logger.info("----------------------------------------------------")
        self.mqttclient = MyMQTTClient(self.main_config["pubsub"], self.logger, True)
        self.mqttclient.connect()

    def tearDown(self):
        self.mqttclient.disconnect()

    def test_0init(self):
        t = ExampleService(self.main_config, self.mqttclient, self.logger)
        self.assertIsNotNone(t)

    def test_1start_stop(self):
        a = threading.Event()
        a.clear()
        b = threading.Event()
        b.clear()

        def recv_a(message):
            a.set()

        def recv_b(message):
            b.set()

        self.mqttclient.subscribe(self.main_config["test"]["start"], recv_a)
        self.mqttclient.subscribe(self.main_config["test"]["stop"], recv_b)

        t = ExampleService(self.main_config, self.mqttclient, self.logger)
        self.assertIsNotNone(t)
        self.assertFalse(t._stop_service.is_set())
        self.assertTrue(t._is_stopped.is_set())
        time.sleep(0.5)

        self.assertFalse(a.is_set())
        self.assertFalse(b.is_set())

        t.start()

        self.assertFalse(t._stop_service.is_set())
        self.assertFalse(t._is_stopped.is_set())

        a.wait(0.5)
        b.wait(0.5)
        self.assertTrue(a.is_set())
        self.assertFalse(b.is_set())
        a.clear()

        t.stop()
        self.assertTrue(t._stop_service.is_set())
        a.wait(0.5)
        b.wait(0.5)
        self.assertFalse(a.is_set())
        self.assertTrue(b.is_set())
        self.assertTrue(t._is_stopped.is_set())

    def test_2run(self):
        a = threading.Event()
        a.clear()
        b = threading.Event()
        b.clear()

        def recv_a(message):
            a.set()

        def recv_b(message):
            b.set()

        self.mqttclient.subscribe(self.main_config["test"]["start"], recv_a)
        self.mqttclient.subscribe(self.main_config["test"]["stop"], recv_b)

        t = ExampleService(self.main_config, pubsub_client=None, logger=self.logger)
        thread = threading.Thread(target=t.run, name=__name__)
        self.assertIsNotNone(t)
        self.assertFalse(t._stop_service.is_set())
        self.assertTrue(t._is_stopped.is_set())
        self.assertFalse(t._is_started.is_set())
        self.assertFalse(a.is_set())
        self.assertFalse(b.is_set())

        thread.start()
        t._is_started.wait(20)
        self.assertTrue(t._is_started.is_set())
        self.assertFalse(t._stop_service.is_set())
        self.assertFalse(t._is_stopped.is_set())

        a.wait(1)
        self.assertTrue(a.is_set())

        t.stop()
        t._is_stopped.wait(1)
        self.assertTrue(t._stop_service.is_set())
        self.assertTrue(t._is_stopped.is_set())
        self.assertFalse(t._is_started.is_set())

        b.wait(1)
        self.assertTrue(b.is_set())

        thread.join()

    def test_3standalone(self):
        a = threading.Event()
        a.clear()
        b = threading.Event()
        b.clear()

        def recv_a(message):
            a.set()

        def recv_b(message):
            b.set()

        self.mqttclient.subscribe(self.main_config["test"]["start"], recv_a)
        self.mqttclient.subscribe(self.main_config["test"]["stop"], recv_b)

        thread = threading.Thread(target=ExampleService.standalone, args=[("-c", self.filename, "--no_gui")],
                                  name=__name__)
        thread.start()
        self.logger.info(" ---- started testservice ---- ")
        a.wait(1)
        self.assertTrue(a.is_set())
        self.assertFalse(b.is_set())
        self.mqttclient.publish(self.main_config["test"]["stop-me"], "")
        b.wait(1)
        self.assertTrue(b.is_set())
        thread.join()


if __name__ == '__main__':
    unittest.main()
