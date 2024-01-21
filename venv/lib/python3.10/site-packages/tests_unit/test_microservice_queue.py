import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pelops.pubsub.pythonqueue import PythonQueue
from pelops.myconfigtools import read_config
from pelops.logging.mylogger import create_logger
from tests_unit.exampleservice import ExampleService
import threading
import time


class TestMicroserviceQueue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.filename = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + "/tests_unit/config_queue.yaml"
        cls.main_config = read_config(cls.filename)
        cls.logger = create_logger(cls.main_config["logger"], "test")
        cls.logger.info("start ==============================================")

    @classmethod
    def tearDownClass(cls):
        cls.logger.info("end ================================================")

    def setUp(self):
        self.logger.info("----------------------------------------------------")
        self.queueclient = PythonQueue(self.main_config["pubsub"], self.logger, True)
        self.queueclient.connect()

    def tearDown(self):
        self.queueclient.disconnect()

    def test_0init(self):
        t = ExampleService(self.main_config, self.queueclient, self.logger)
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

        self.queueclient.subscribe(self.main_config["test"]["start"], recv_a)
        self.queueclient.subscribe(self.main_config["test"]["stop"], recv_b)

        t = ExampleService(self.main_config, self.queueclient, self.logger)
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

        self.queueclient.subscribe(self.main_config["test"]["start"], recv_a)
        self.queueclient.subscribe(self.main_config["test"]["stop"], recv_b)

        t = ExampleService(self.main_config, pubsub_client=self.queueclient, logger=self.logger)
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


if __name__ == '__main__':
    unittest.main()
