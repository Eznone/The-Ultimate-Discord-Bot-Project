import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pelops.myconfigtools import read_config, validate_config
import pelops.schema.abstractmicroservice


class TestValidateConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prefix = ""
        if not os.getcwd().endswith("tests_unit"):
            cls.prefix = "tests_unit/"

    def test_validate_adcdac(self):
        import copreus.schema.drivermanager as schema
        config = read_config(self.prefix + "config_adcdac.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_adc(self):
        import copreus.schema.adc as schema
        config = read_config(self.prefix + "config_adc.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_dac(self):
        import copreus.schema.dac as schema
        config = read_config(self.prefix + "config_dac.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_bme_280(self):
        import copreus.schema.bme_280 as schema
        config = read_config(self.prefix + "config_bme_280.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_dht(self):
        import copreus.schema.dht as schema
        config = read_config(self.prefix + "config_dht.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_epaperdirect(self):
        import copreus.schema.epaperdirect as schema
        config = read_config(self.prefix + "config_epaperdirect.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_epapersimple(self):
        import copreus.schema.epapersimple as schema
        config = read_config(self.prefix + "config_epapersimple.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_input(self):
        import copreus.schema.input as schema
        config = read_config(self.prefix + "config_input.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_pollinginput(self):
        import copreus.schema.pollinginput as schema
        config = read_config(self.prefix + "config_pollinginput.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_output(self):
        import copreus.schema.output as schema
        config = read_config(self.prefix + "config_output.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_rfid(self):
        import copreus.schema.rfid as schema
        config = read_config(self.prefix + "config_rfid.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_rgbled(self):
        import copreus.schema.rgbled as schema
        config = read_config(self.prefix + "config_rgbled.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_rotaryencoder(self):
        import copreus.schema.rotaryencoder as schema
        config = read_config(self.prefix + "config_rotaryencoder.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_rotaryencoder2(self):
        import copreus.schema.rotaryencoder2 as schema
        config = read_config(self.prefix + "config_rotaryencoder2.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)

    def test_validate_drivermanager(self):
        import copreus.schema.drivermanager as schema
        config = read_config(self.prefix + "config.yaml")
        validation_result = validate_config(config, pelops.schema.abstractmicroservice.get_schema(schema.get_schema()))
        self.assertIsNone(validation_result)


if __name__ == '__main__':
    unittest.main()
