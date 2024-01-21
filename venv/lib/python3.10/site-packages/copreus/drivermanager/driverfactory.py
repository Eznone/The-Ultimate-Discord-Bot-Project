import copreus.drivers
import importlib
import pelops.logging.mylogger as mylogger


class DriverFactory:
    factory_logger = None
    mqtt_client = None
    logger = None
    spi_lock = None
    i2c_lock = None
    #driver = None

    def __init__(self, mqtt_client=None, logger=None, spi_lock=None, i2c_lock=None):
        self.mqtt_client = mqtt_client
        self.logger = logger
        self.spi_lock = spi_lock
        self.i2c_lock = i2c_lock
        self.factory_logger = mylogger.get_child(logger, self.__class__.__name__)

    def create_drivers(self, config):
        """Static drivers factory - takes a list of driver configs and creates them."""

        self.factory_logger.info("creating drivers")
        self.factory_logger.debug("driver configs: ".format(config["drivers"]))
        drivers = {}
        for driver_config in config["drivers"]:
            if not driver_config["active"]:
                continue
            config["driver"] = driver_config
            driver = self.create_driver(config)
            driver_id = self.get_unique_name(drivers, driver.get_name())
            drivers[driver_id] = driver
            self.factory_logger.info(" - added driver '[{}]: {}.{}'".format(driver_id, driver._type, driver._name))
        self.factory_logger.debug("drivers: {}".format(drivers))
        return drivers

    @staticmethod
    def get_unique_name(drivers, name):
        prefix = name.replace(" ", "").lower()
        suffix = ""
        counter = 0
        name = prefix+suffix
        while name in drivers:
            suffix = "_{}".format(counter)
            counter += 1
            name = prefix + suffix
        return name

    def create_driver(self, config):
        """Static driver factory - takes a driver entry from json/yaml config and instantiates the corresponding
        Class. Classes that are specializations of ASPI are provided with the spi_lock (if one is provided to this
        factory).

        New implemented driver must be added manually."""
        type_name = config["driver"]["type"].upper()

        # it is on purpose that not class names are used to be compared with type_name (as will be done within the
        # constructor of the base class ADriver). This approach allows for late binding - thus, a class is imported
        # if and only if it is needed which results in less dependencies that must be fullfilled although they might
        # not be needed.

        drivers = copreus.drivers.get_drivers()

        try:
            driver = drivers[type_name]
            mod = importlib.import_module(driver["module"])
            klass = getattr(mod, driver["name"])
        except:
            logger = mylogger.get_child(self.logger, __name__)
            logger.error("unknown type name '{}'.".format(type_name))
            raise ValueError("unknown type name '{}'.".format(type_name))

        if "ASPI" in driver["bases"]:
            result = klass(config, self.mqtt_client, self.logger, spi_lock=self.spi_lock, no_gui=True,
                            manage_monitoring_agent=False)
        elif "AI2C" in driver["bases"]:
            result = klass(config, self.mqtt_client, self.logger, i2c_lock=self.i2c_lock, no_gui=True,
                            manage_monitoring_agent=False)
        else:
            result = klass(config, self.mqtt_client, self.logger, no_gui=True,
                            manage_monitoring_agent=False)

        return result

    def reload_driver(self, drivers, driver_id):
        """destroy the driver and creates a new one from scratch"""
        self.factory_logger.info("restarting driver '{}' - start".format(driver_id))
        driver = drivers[driver_id]
        self.factory_logger.info("... {}".format(driver.get_short_info()))
        driver.stop()
        config = {}
        config["driver"] = driver.get_config()
        new_driver = self.create_driver(config)
        drivers[driver_id] = new_driver
        new_driver.start()
        self.factory_logger.info("restarting driver {} - done")

    @staticmethod
    def old_create(config, mqtt_client, logger, spi_lock=None, i2c_lock=None):
        type_name = config["type"].upper()
        if type_name == "ADC":
            from copreus.drivers.adc import ADC
            result = ADC(config, mqtt_client, logger, spi_lock, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "DAC":
            from copreus.drivers.dac import DAC
            result = DAC(config, mqtt_client, logger, spi_lock, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "BME_280":
            from copreus.drivers.bme_280 import BME_280
            result = BME_280(config, mqtt_client, logger, i2c_lock, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "DHT":
            from copreus.drivers.dht import DHT
            result = DHT(config, mqtt_client, logger, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "RFID":
            from copreus.drivers.rfid import RFID
            result = RFID(config, mqtt_client, logger, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "RGBLED":
            from copreus.drivers.rgbled import RGBLed
            result = RGBLed(config, mqtt_client, logger, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "EPAPERDIRECT":
            from copreus.drivers.epaperdirect import EPaperDirect
            result = EPaperDirect(config, mqtt_client, logger, spi_lock, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "EPAPERSIMPLE":
            from copreus.drivers.epapersimple import EPaperSimple
            result = EPaperSimple(config, mqtt_client, logger, spi_lock, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "INPUT":
            from copreus.drivers.input import Input
            result = Input(config, mqtt_client, logger, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "POLLINGINPUT":
            from copreus.drivers.pollinginput import PollingInput
            result = PollingInput(config, mqtt_client, logger, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "OUTPUT":
            from copreus.drivers.output import Output
            result = Output(config, mqtt_client, logger, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "ROTARYENCODER":
            from copreus.drivers.rotaryencoder import RotaryEncoder
            result = RotaryEncoder(config, mqtt_client, logger, no_gui=True, manage_monitoring_agent=False)
        elif type_name == "ROTARYENCODER2":
            from copreus.drivers.rotaryencoder2 import RotaryEncoder2
            result = RotaryEncoder2(config, mqtt_client, logger, no_gui=True, manage_monitoring_agent=False)
        else:
            logger = mylogger.get_child(logger, __name__)
            logger.error("unknown type name '{}'.".format(type_name))
            raise ValueError("unknown type name '{}'.".format(type_name))

        return result


