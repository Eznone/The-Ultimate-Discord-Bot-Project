import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pelops.schema.abstractmicroservice
import copreus.drivers


class TestGetDrivers(unittest.TestCase):
    def test_getdrivers_00_basic(self):
        drivers = copreus.drivers.get_drivers()
        self.assertIsNotNone(drivers)
        self.assertGreater(len(drivers), 0)

    def test_getdrivers_01_no_abstract(self):
        drivers = copreus.drivers.get_drivers()
        drivers = drivers.keys()
        self.assertNotIn("ADRIVER", drivers)
        self.assertNotIn("AEPAPER", drivers)
        self.assertNotIn("AEVENTS", drivers)
        self.assertNotIn("APOLLING", drivers)
        self.assertNotIn("AROTARYENCODER", drivers)
        self.assertNotIn("ASPI", drivers)
        self.assertNotIn("AI2C", drivers)

    def test_getdrivers_02_all_drivers(self):
        getdrivers = copreus.drivers.get_drivers()
        getdrivers = getdrivers.keys()
        drivers = ["ADC", "BME_280", "DAC", "DHT", "EPAPERDIRECT", "EPAPERSIMPLE", "INPUT", "POLLINGINPUT",
                   "OUTPUT", "RFID", "ROTARYENCODER", "ROTARYENCODER2"]
        for driver in drivers:
            self.assertIn(driver, getdrivers)


if __name__ == '__main__':
    unittest.main()
