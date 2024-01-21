import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pelops.pubsub.mymqttclient import MyMQTTClient
from pelops.myconfigtools import read_config
from pelops.logging.mylogger import create_logger
import threading
import time


class TestMyMQTTClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main_config = read_config(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) +
                                 "/tests_unit/config_mqtt.yaml")
        cls.config = cls.main_config["pubsub"]
        cls.config["log-level"] = "DEBUG"
        try:
            del(cls.config["retain-messages"])
        except KeyError:
            pass
        try:
            del(cls.config["qos"])
        except KeyError:
            pass
        cls.logger = create_logger(cls.main_config["logger"], "Test")
        cls.logger.info("start ==============================================")

    @classmethod
    def tearDownClass(cls):
        cls.logger.info("end ================================================")

    def setUp(self):
        self.logger.info("----------------------------------------------------")

    def test_00init(self):
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        self.assertIsNotNone(mc)
        self.assertIsNotNone(mc._qos)
        self.assertIsNotNone(mc._retained_messages)

    def test_01connect_disconnect(self):
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
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

        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        with self.assertRaises(RuntimeWarning):
            mc.publish("/test/a", "a")
        mc.connect()
        mc.subscribe("/test/a", handler_a)
        mc.publish("/test/a", "a")
        event_a.wait(5)
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

        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        mc.connect()
        self.assertEqual(len(mc._topic_handler), 0)
        mc.subscribe("/test/a", handler_a)
        mc.subscribe("/test/b", handler_b)
        self.assertEqual(len(mc._topic_handler), 2)
        mc.publish("/test/a", "a")
        mc.publish("/test/b", "b")
        event_a.wait(5)
        event_b.wait(5)
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

        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        self.assertEqual(len(mc._topic_handler), 0)
        mc.subscribe("/test/a", handler_a)
        mc.subscribe("/test/b", handler_b)
        self.assertEqual(len(mc._topic_handler), 2)
        mc.connect()
        mc.publish("/test/a", "a")
        mc.publish("/test/b", "b")
        event_a.wait(5)
        event_b.wait(5)
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

        mc = MyMQTTClient(self.config, self.logger, quiet=True)
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
        event_a.wait(5)
        event_b.wait(5)
        event_c.wait(5)
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
        event_a.wait(2)
        event_b.wait(2)
        event_c.wait(2)
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
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        self.assertEqual(len(mc._topic_handler), 0)
        mc.subscribe("/test/a1", handler_a)
        mc.subscribe("/test/b1", handler_b)
        mc.subscribe("/test/b1", handler_c)
        self.assertEqual(len(mc._topic_handler), 2)
        self.assertEqual(len(mc._topic_handler["/test/a1"]), 1)
        self.assertEqual(len(mc._topic_handler["/test/b1"]), 2)
        mc.connect()
        time.sleep(1)
        event_a.clear()
        event_b.clear()
        event_c.clear()

        t = time.time()
        mc.publish("/test/a1", "a_"+str(t))
        mc.publish("/test/b1", "b_"+str(t))

        event_a.wait(5)
        event_b.wait(5)
        event_c.wait(5)
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
        event_a.wait(2)
        event_b.wait(2)
        event_c.wait(2)
        self.assertFalse(event_a.is_set())
        self.assertFalse(event_b.is_set())
        self.assertFalse(event_c.is_set())

        mc.disconnect()

    def test_07setwill_direct(self):
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        mc.connect()
        mc.set_will("/topic/will", "will")
        self.assertEqual(mc._will_topic, "/topic/will")
        self.assertEqual(mc._will_message, "will")
        mc.disconnect()

    def test_08setwill_delayed(self):
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        mc.set_will("/topic/will", "will")
        mc.connect()
        self.assertEqual(mc._will_topic, "/topic/will")
        self.assertEqual(mc._will_message, "will")
        mc.disconnect()

    def test_09retain_message(self):
        event_a = threading.Event()
        event_b = threading.Event()
        event_c = threading.Event()
        event_a.clear()
        event_b.clear()
        event_c.clear()
        global akt_a
        global akt_b
        global akt_c
        akt_a = None
        akt_b = None
        akt_c = None
        topic_a = "/test/retain/a"
        topic_b = "/test/retain/b"
        topic_c = "/test/retain/c"

        def handler_a(value):
            global akt_a
            akt_a = value.decode("utf-8")
            event_a.set()

        def handler_b(value):
            global akt_b
            akt_b = value.decode("utf-8")
            event_b.set()

        def handler_c(value):
            global akt_c
            akt_c = value.decode("utf-8")
            event_c.set()

        self.config["retain-messages"] = True
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        mc.connect()
        mc.subscribe(topic_a, handler_a)
        mc.subscribe(topic_b, handler_b)
        mc.subscribe(topic_c, handler_c)
        event_a.clear()
        event_b.clear()
        event_c.clear()
        mc.publish(topic_a, "a")
        mc.publish(topic_b, "b")
        mc.publish(topic_c, "c")
        event_a.wait(5)
        event_b.wait(5)
        event_c.wait(5)
        self.assertTrue(event_a.is_set())
        self.assertTrue(event_b.is_set())
        self.assertTrue(event_c.is_set())
        event_a.clear()
        event_b.clear()
        event_c.clear()
        self.assertEqual(akt_a, "a")
        self.assertEqual(akt_b, "b")
        self.assertEqual(akt_c, "c")
        last_a = akt_a
        last_b = akt_b
        last_c = akt_c
        akt_a = None
        akt_b = None
        akt_c = None
        mc.disconnect()
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        mc.connect()
        self.assertNotEqual(akt_a, last_a)
        self.assertNotEqual(akt_b, last_b)
        self.assertNotEqual(akt_c, last_c)
        mc.subscribe(topic_a, handler_a)
        mc.subscribe(topic_b, handler_b)
        mc.subscribe(topic_c, handler_c)
        event_a.wait(5)
        event_b.wait(5)
        event_c.wait(5)
        self.assertTrue(event_a.is_set())
        self.assertTrue(event_b.is_set())
        self.assertTrue(event_c.is_set())
        self.assertEqual(akt_a, last_a)
        self.assertEqual(akt_b, last_b)
        self.assertEqual(akt_c, last_c)
        mc.disconnect()

    def test_10clear_retained_messages(self):
        event_a = threading.Event()
        event_b = threading.Event()
        event_c = threading.Event()
        event_a.clear()
        event_b.clear()
        event_c.clear()
        global akt_a
        global akt_b
        global akt_c
        akt_a = None
        akt_b = None
        akt_c = None
        topic_a = "/test/retain/a"
        topic_b = "/test/retain/b"
        topic_c = "/test/retain/c"

        def handler_a(value):
            global akt_a
            akt_a = value.decode("utf-8")
            event_a.set()

        def handler_b(value):
            global akt_b
            akt_b = value.decode("utf-8")
            event_b.set()

        def handler_c(value):
            global akt_c
            akt_c = value.decode("utf-8")
            event_c.set()

        self.config["retain-messages"] = True
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        mc.subscribe(topic_a, handler_a)
        mc.subscribe(topic_b, handler_b)
        mc.subscribe(topic_c, handler_c)
        mc.connect()
        event_a.wait(5)
        event_b.wait(5)
        event_c.wait(5)
        self.assertTrue(event_a.is_set())
        self.assertTrue(event_b.is_set())
        self.assertTrue(event_c.is_set())
        self.assertEqual(akt_a, "a")
        self.assertEqual(akt_b, "b")
        self.assertEqual(akt_c, "c")
        event_a.clear()
        event_b.clear()
        event_c.clear()
        mc.disconnect()

        time.sleep(1)
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        mc.subscribe(topic_a, handler_a)
        mc.subscribe(topic_b, handler_b)
        mc.subscribe(topic_c, handler_c)
        mc.clear_retained_messages()

        time.sleep(1)
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        mc.connect()
        event_a.wait(5)
        event_b.wait(5)
        event_c.wait(5)
        self.assertFalse(event_a.is_set())
        self.assertFalse(event_b.is_set())
        self.assertFalse(event_c.is_set())
        mc.disconnect()

    def test_11statistics(self):
        topic_prefix = "/test/"+str(time.time())+"/"
        event = threading.Event()

        def my_handler(value):
            event.set()

        # start test
        pub = MyMQTTClient(self.config, self.logger, quiet=True)
        pub.connect()
        mc = MyMQTTClient(self.config, self.logger, quiet=True)
        self.assertEqual(len(mc._stats.stats), 0)
        mc.subscribe(topic_prefix+"a", my_handler)
        mc.subscribe(topic_prefix+"b", my_handler)
        mc.subscribe(topic_prefix+"c", my_handler)
        mc.connect()
        mc.is_connected.wait()

        time.sleep(0.5)

        id = 0

        self.assertEqual(len(mc._stats.stats), 0)
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
        for i in range(4):
            pub.publish(topic_prefix+"a", id)
            id += 1

        time.sleep(0.5)

        totals = mc._stats.get_totals()
        self.assertEqual(totals.received_messages, 9)
        self.assertEqual(totals.sent_messages, 5)
        self.assertEqual(mc._stats.stats[topic_prefix + "a"].received_messages, 4)
        self.assertEqual(mc._stats.stats[topic_prefix + "a"].sent_messages, 0)
        self.assertEqual(mc._stats.stats[topic_prefix + "b"].received_messages, 2)
        self.assertEqual(mc._stats.stats[topic_prefix + "b"].sent_messages, 0)
        self.assertEqual(mc._stats.stats[topic_prefix + "c"].received_messages, 3)
        self.assertEqual(mc._stats.stats[topic_prefix + "c"].sent_messages, 2)
        self.assertEqual(mc._stats.stats[topic_prefix + "d"].received_messages, 0)
        self.assertEqual(mc._stats.stats[topic_prefix + "d"].sent_messages, 3)

        mc.disconnect()
        pub.disconnect()


if __name__ == '__main__':
    unittest.main()

