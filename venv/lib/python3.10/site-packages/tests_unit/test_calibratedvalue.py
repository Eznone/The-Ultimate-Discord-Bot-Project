from pelops import myconfigtools
from pelops.logging import mylogger
import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestCalibratedValue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._config = myconfigtools.read_config(
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))+"/tests_unit/config_calibratedvalue.yaml")
        cls.logger = mylogger.create_logger(cls._config["logger"], __name__)
        cls.logger.info("TestCalibratedValue - start")

    @classmethod
    def tearDownClass(cls):
        cls.logger.info("TestCalibratedValue - stop")



if __name__ == '__main__':
    unittest.main()
