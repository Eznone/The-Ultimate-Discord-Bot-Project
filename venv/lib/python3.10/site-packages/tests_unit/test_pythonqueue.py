import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pelops.pubsub.pythonqueue import PythonQueue
from pelops.myconfigtools import read_config
from pelops.logging.mylogger import create_logger
import threading
import time


class TestPythonQueue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main_config = read_config(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) +
                                 "/tests_unit/config_queue.yaml")
        cls.config = cls.main_config["pubsub"]
        cls.config["log-level"] = "DEBUG"
        cls.logger = create_logger(cls.main_config["logger"], "Test")
        cls.logger.info("start ==============================================")

    @classmethod
    def tearDownClass(cls):
        cls.logger.info("end ================================================")

    def setUp(self):
        self.logger.info("----------------------------------------------------")

    def test_00init(self):
        mc = PythonQueue(self.config, self.logger, quiet=True)
        self.assertIsNotNone(mc)

    def test_01connect_disconnect(self):
        mc = PythonQueue(self.config, self.logger, quiet=True)
        self.assertFalse(mc.is_connected.is_set())
        self.assertTrue(mc.is_disconnected.is_set())
        mc.connect()
        self.assertTrue(mc.is_connected.is_set())
        self.assertFalse(mc.is_disconnected.is_set())
        mc.disconnect()
        self.assertFalse(mc.is_connected.is_set())
        self.assertTrue(mc.is_disconnected.is_set())

    def test_02publish_subscribe(self):
        event_a = threading.Event()
        event_a.clear()

        def handler_a(value):
            event_a.set()

        mc = PythonQueue(self.config, self.logger, quiet=True)
        with self.assertRaises(RuntimeWarning):
            mc.publish("/test/a", "a")
        mc.connect()
        mc.subscribe("/test/a", handler_a)
        mc.publish("/test/a", "a")
        event_a.wait(0.5)
        self.assertTrue(event_a.is_set())
        mc.disconnect()
        with self.assertRaises(RuntimeWarning):
            mc.publish("/test/a", "a")

    def test_03subscribe_direct(self):
        event_a = threading.Event()
        event_b = threading.Event()
        event_a.clear()
        event_b.clear()

        def handler_a(value):
            event_a.set()

        def handler_b(value):
            event_b.set()

        mc = PythonQueue(self.config, self.logger, quiet=True)
        mc.connect()
        self.assertEqual(len(mc._topic_handler), 0)
        mc.subscribe("/test/a", handler_a)
        mc.subscribe("/test/b", handler_b)
        self.assertEqual(len(mc._topic_handler), 2)
        mc.publish("/test/a", "a")
        mc.publish("/test/b", "b")
        event_a.wait(0.5)
        event_b.wait(0.5)
        self.assertTrue(event_a.is_set())
        self.assertTrue(event_b.is_set())
        mc.disconnect()

    def test_04subscribe_delayed(self):
        event_a = threading.Event()
        event_b = threading.Event()
        event_a.clear()
        event_b.clear()

        def handler_a(value):
            event_a.set()

        def handler_b(value):
            event_b.set()

        mc = PythonQueue(self.config, self.logger, quiet=True)
        self.assertEqual(len(mc._topic_handler), 0)
        mc.subscribe("/test/a", handler_a)
        mc.subscribe("/test/b", handler_b)
        self.assertEqual(len(mc._topic_handler), 2)
        mc.connect()
        mc.publish("/test/a", "a")
        mc.publish("/test/b", "b")
        event_a.wait(0.5)
        event_b.wait(0.5)
        self.assertTrue(event_a.is_set())
        self.assertTrue(event_b.is_set())
        mc.disconnect()

    def test_05unsubscribe(self):
        event_a = threading.Event()
        event_b = threading.Event()
        event_c = threading.Event()
        event_a.clear()
        event_b.clear()
        event_c.clear()

        def handler_a(value):
            event_a.set()

        def handler_b(value):
            event_b.set()

        def handler_c(value):
            event_c.set()

        mc = PythonQueue(self.config, self.logger, quiet=True)
        self.assertEqual(len(mc._topic_handler), 0)
        mc.subscribe("/test/a", handler_a)
        mc.subscribe("/test/b", handler_b)
        mc.subscribe("/test/b", handler_c)
        self.assertEqual(len(mc._topic_handler), 2)
        self.assertEqual(len(mc._topic_handler["/test/a"]), 1)
        self.assertEqual(len(mc._topic_handler["/test/b"]), 2)
        mc.connect()
        mc.publish("/test/a", "a")
        mc.publish("/test/b", "b")
        event_a.wait(0.5)
        event_b.wait(0.5)
        event_c.wait(0.5)
        self.assertTrue(event_a.is_set())
        self.assertTrue(event_b.is_set())
        self.assertTrue(event_c.is_set())
        event_a.clear()
        event_b.clear()
        event_c.clear()

        with self.assertRaises(ValueError):
            mc.unsubscribe("/test/a", handler_b)  # single handler, but wrong handler
        self.assertEqual(len(mc._topic_handler), 2)
        self.assertEqual(len(mc._topic_handler["/test/a"]), 1)
        self.assertEqual(len(mc._topic_handler["/test/b"]), 2)

        with self.assertRaises(KeyError):
            mc.unsubscribe("/test/c", handler_b)  # not exisiting topic
        self.assertEqual(len(mc._topic_handler), 2)
        self.assertEqual(len(mc._topic_handler["/test/a"]), 1)
        self.assertEqual(len(mc._topic_handler["/test/b"]), 2)

        with self.assertRaises(ValueError):
            mc.unsubscribe("/test/b", handler_a)  # two handlers, but wrong handler
        self.assertEqual(len(mc._topic_handler), 2)
        self.assertEqual(len(mc._topic_handler["/test/a"]), 1)
        self.assertEqual(len(mc._topic_handler["/test/b"]), 2)

        mc.unsubscribe("/test/a", handler_a)  # single handler, correct handler
        self.assertEqual(len(mc._topic_handler), 1)
        self.assertNotIn("/test/a", mc._topic_handler.keys())
        self.assertEqual(len(mc._topic_handler["/test/b"]), 2)

        mc.unsubscribe("/test/b", handler_c)  # two handlers, correct handler
        self.assertEqual(len(mc._topic_handler), 1)
        self.assertNotIn("/test/a", mc._topic_handler.keys())
        self.assertEqual(len(mc._topic_handler["/test/b"]), 1)

        event_a.clear()
        event_b.clear()
        event_c.clear()
        mc.publish("/test/a", "a")
        mc.publish("/test/b", "b")
        event_a.wait(0.2)
        event_b.wait(0.2)
        event_c.wait(0.2)
        self.assertFalse(event_a.is_set())
        self.assertTrue(event_b.is_set())
        self.assertFalse(event_c.is_set())

        mc.disconnect()

    def test_06unsubscribe_all(self):
        event_a = threading.Event()
        event_b = threading.Event()
        event_c = threading.Event()
        event_a.clear()
        event_b.clear()
        event_c.clear()

        def handler_a(value):
            event_a.set()

        def handler_b(value):
            event_b.set()

        def handler_c(value):
            event_c.set()

        self.config["qos"] = 0
        self.config["retain-messages"] = False
        mc = PythonQueue(self.config, self.logger, quiet=True)
        self.assertEqual(len(mc._topic_handler), 0)
        mc.subscribe("/test/a1", handler_a)
        mc.subscribe("/test/b1", handler_b)
        mc.subscribe("/test/b1", handler_c)
        self.assertEqual(len(mc._topic_handler), 2)
        self.assertEqual(len(mc._topic_handler["/test/a1"]), 1)
        self.assertEqual(len(mc._topic_handler["/test/b1"]), 2)
        mc.connect()
        time.sleep(0.1)
        event_a.clear()
        event_b.clear()
        event_c.clear()

        t = time.time()
        mc.publish("/test/a1", "a_"+str(t))
        mc.publish("/test/b1", "b_"+str(t))

        event_a.wait(0.5)
        event_b.wait(0.5)
        event_c.wait(0.5)
        self.assertTrue(event_a.is_set())
        self.assertTrue(event_b.is_set())
        self.assertTrue(event_c.is_set())
        event_a.clear()
        event_b.clear()
        event_c.clear()

        mc.unsubscribe_all()
        self.assertEqual(len(mc._topic_handler), 0)

        mc.publish("/test/a1", "1")
        mc.publish("/test/b1", "2")
        event_a.wait(0.2)
        event_b.wait(0.2)
        event_c.wait(0.2)
        self.assertFalse(event_a.is_set())
        self.assertFalse(event_b.is_set())
        self.assertFalse(event_c.is_set())

        mc.disconnect()

    def test_07statistics(self):
        topic_prefix = "/test/"+str(time.time())+"/"
        event = threading.Event()

        def my_handler(value):
            event.set()

        # start test
        pub = PythonQueue(self.config, self.logger, quiet=True)
        pub.connect()
        mc = PythonQueue(self.config, self.logger, quiet=True)
        self.assertEqual(len(mc._stats.stats), 0)
        mc.subscribe(topic_prefix+"a", my_handler)
        mc.subscribe(topic_prefix+"b", my_handler)
        mc.subscribe(topic_prefix+"c", my_handler)
        mc.connect()
        mc.is_connected.wait()

        time.sleep(0.5)

        id = 0

        self.assertEqual(len(mc._stats.stats), 0)
        for i in range(4):
            pub.publish(topic_prefix+"a", id)
            id += 1
        for i in range(1):
            pub.publish(topic_prefix+"c", id)
            id += 1
        for i in range(2):
            pub.publish(topic_prefix+"b", id)
            mc.publish(topic_prefix + "c", id)
            id += 1
        for i in range(3):
            pub.publish(topic_prefix+"d", id)
            mc.publish(topic_prefix+"d", id)
            id += 1

        time.sleep(0.5)

        totals = mc._stats.get_totals()
        self.assertEqual(totals.received_messages, 2)
        self.assertEqual(totals.sent_messages, 5)
        self.assertEqual(mc._stats.stats[topic_prefix + "a"].received_messages, 0)
        self.assertEqual(mc._stats.stats[topic_prefix + "a"].sent_messages, 0)
        self.assertEqual(mc._stats.stats[topic_prefix + "b"].received_messages, 0)
        self.assertEqual(mc._stats.stats[topic_prefix + "b"].sent_messages, 0)
        self.assertEqual(mc._stats.stats[topic_prefix + "c"].received_messages, 2)
        self.assertEqual(mc._stats.stats[topic_prefix + "c"].sent_messages, 2)
        self.assertEqual(mc._stats.stats[topic_prefix + "d"].received_messages, 0)
        self.assertEqual(mc._stats.stats[topic_prefix + "d"].sent_messages, 3)
        mc.disconnect()
        pub.disconnect()


if __name__ == '__main__':
    unittest.main()

