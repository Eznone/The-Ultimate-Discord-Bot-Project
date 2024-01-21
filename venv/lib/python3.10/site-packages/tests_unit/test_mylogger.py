import unittest
import os
import sys
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
import logging.handlers
import pelops.logging.mylogger


class TestMyLogger(unittest.TestCase):
    def setUp(self):
        l = logging.getLogger("test")
        for h in l.root.handlers:
            h.flush()
            h.close()
            l.root.removeHandler(h)

    def tearDown(self):
        l = logging.getLogger("test")
        for h in l.root.handlers:
            h.flush()
            h.close()
            l.root.removeHandler(h)

    def test_0getloglevel(self):
        input_values = [
            (logging.CRITICAL, "critical"),
            (logging.CRITICAL, "CRITICAL"),
            (logging.CRITICAL, "Critical"),
            (logging.ERROR, "error"),
            (logging.ERROR, "ERROR"),
            (logging.ERROR, "Error"),
            (logging.WARNING, "warning"),
            (logging.WARNING, "WARNING"),
            (logging.WARNING, "Warning"),
            (logging.INFO, "info"),
            (logging.INFO, "INFO"),
            (logging.INFO, "Info"),
            (logging.DEBUG, "debug"),
            (logging.DEBUG, "DEBUG"),
            (logging.DEBUG, "Debug"),
        ]
        for level, name in input_values:
            self.assertEqual(pelops.logging.mylogger.get_log_level(name), level)

        with self.assertRaises(ValueError):
            pelops.logging.mylogger.get_log_level("fefsvbk")

    def test_1create_logger(self):
        config = {
            "log-level": "INFO",
            "log-file": "test_mylogger.log"
        }
        l = pelops.logging.mylogger.create_logger(config, "test")
        self.assertIsNotNone(l)
        self.assertEqual(l.getEffectiveLevel(), logging.INFO)
        self.assertEqual(1, len(l.root.handlers))
        for handler in l.root.handlers:
            t=type(handler)
            self.assertEqual(t, logging.FileHandler)

    def test_2create_rotate_logger(self):
        config = {
            "log-level": "INFO",
            "log-file": "test_mylogger.log",
            "log-rotation": {
                "maxbytes": 256,
                "backupcount": 3
            }
        }
        l = pelops.logging.mylogger.create_logger(config, "test")
        self.assertIsNotNone(l)
        self.assertEqual(l.getEffectiveLevel(), logging.INFO)
        self.assertEqual(1, len(l.root.handlers))
        for handler in l.root.handlers:
            t = type(handler)
            self.assertEqual(t, logging.handlers.RotatingFileHandler)

    def test_3get_child(self):
        config = {
            "log-level": "INFO",
            "log-file": "test_mylogger.log"
        }
        config_child = {
            "log-level": "DEBUG"
        }
        l = pelops.logging.mylogger.create_logger(config, "test")
        self.assertIsNotNone(l)
        c = pelops.logging.mylogger.get_child(l, "child", config_child)
        self.assertIsNotNone(c)
        self.assertEqual(l.getEffectiveLevel(), logging.INFO)
        self.assertEqual(c.getEffectiveLevel(), logging.DEBUG)

    def test_4write_to_log(self):
        config = {
            "log-level": "INFO",
            "log-file": "test_mylogger.log"
        }
        if os.path.isfile("test_mylogger.log"):
            os.remove("test_mylogger.log")
        self.assertFalse(os.path.isfile("test_mylogger.log"))
        l = pelops.logging.mylogger.create_logger(config, "test")
        self.assertIsNotNone(l)
        for i in range(50):
            l.info(i)
        for h in l.root.handlers:
            h.flush()
            h.close()
            l.removeHandler(h)
            del h
        del l
        time.sleep(1)
        self.assertTrue(os.path.isfile("test_mylogger.log"))
        self.assertEqual(50, sum(1 for line in open("test_mylogger.log", "r")))
        os.remove("test_mylogger.log")

    def test_5rotate_log(self):
        def remove_file(filename):
            if os.path.isfile(filename):
                os.remove(filename)
            self.assertFalse(os.path.isfile(filename))

        config = {
            "log-level": "INFO",
            "log-file": "test_mylogger.log",
            "log-rotation": {
                "maxbytes": 256,
                "backupcount": 2
            }
        }

        remove_file("test_mylogger.log")
        remove_file("test_mylogger.log.1")
        remove_file("test_mylogger.log.2")
        remove_file("test_mylogger.log.3")

        l = pelops.logging.mylogger.create_logger(config, "test")
        self.assertIsNotNone(l)
        for i in range(50):
            l.info(i)
        for h in l.root.handlers:
            h.flush()
            h.close()
            l.removeHandler(h)
            del h
        del l
        self.assertTrue(os.path.isfile("test_mylogger.log"))
        self.assertTrue(os.path.isfile("test_mylogger.log.1"))
        self.assertTrue(os.path.isfile("test_mylogger.log.2"))
        self.assertFalse(os.path.isfile("test_mylogger.log.3"))
        os.remove("test_mylogger.log")
        os.remove("test_mylogger.log.1")
        os.remove("test_mylogger.log.2")


if __name__ == '__main__':
    unittest.main()

