from threading import Lock
from pelops.abstractmicroservice import AbstractMicroservice
from copreus.drivermanager.driverfactory import DriverFactory
from copreus.schema.drivermanager import get_schema
from copreus import version
import pelops.ui.tools


class DriverManager(AbstractMicroservice):
    """Takes a yaml config file, creates all drivers that are set to active, and starts them.

    The DriverManager alters the behavior of the drivers at three points:
      * A single instance of MyMQTTClient is provided to all driver.
      * It overrides the individual topic_sub_handler and provides one central _on_message handler.
      * One spi lock is provided to avoid overallocation of the spi interface (Please be note that a single lock is
      used for all spi instances independent of the bus/drivers parameter. Thus, even in case of two independent spi
      interfaces only one of them can be used at any given time.)

    See copreus.baseclasses.adriver for a brief description of the yaml config file."""

    _version = version

    _drivers = None  # list of instantiated drivers.
    _spi_lock = None  # threading.Lock for spi interface access
    _i2c_lock = None  # threading.Lock for i2c interface access
    _driver_factory = None  # instance of the driver factory

    def __init__(self, config, mqtt_client=None, logger=None, stdout_log_level=None, no_gui=None):
        AbstractMicroservice.__init__(self, config, "drivers", mqtt_client, logger, logger_name=self.__class__.__name__,
                                      stdout_log_level=stdout_log_level, no_gui=no_gui)
        self._spi_lock = Lock()
        self._i2c_lock = Lock()

        self._driver_factory = DriverFactory(self._mqtt_client, self._logger, self._spi_lock, self._i2c_lock)
        # create_drivers needs the full config structure - thus, config instead of self._config is used.
        self._drivers = self._driver_factory.create_drivers(config)

        self._add_driver_ui_commands()
        self._add_ui_command("list_drivers", self._cmd_list_drivers)
        self._add_ui_command("reload_driver", self._cmd_reload_driver)
        self._add_ui_command("stop_driver", self._cmd_stop_driver)
        self._add_ui_command("start_driver", self._cmd_start_driver)
        self._add_ui_command("restart_driver", self._cmd_restart_driver)

    def _get_id_from_arg(self, arg):
        arg = pelops.ui.tools.parse(arg)
        print(arg, len(arg))
        driver_id = None
        if len(arg) != 1:
            print("missing mandatory parameter id. expected: 'reload_driver id'")
        elif arg[0] not in self._drivers:
            print("unknown id '{}'".format(arg[0]))
        else:
            driver_id = arg[0]
        return driver_id

    def _cmd_stop_driver(self, arg):
        """stop_driver id - stops this driver driver. use the id from command 'list': STOP_DRIVER name"""
        driver_id = self._get_id_from_arg(arg)
        if driver_id is not None:
            driver = self._drivers[driver_id]
            if driver.is_stopped.is_set():
                print("[{}] is not running".format(driver_id))
            else:
                print("stopping [{}]: {}".format(driver_id, driver.get_short_info()))
                ch = pelops.ui.tools.get_yes_no()
                if ch == "y":
                    driver.stop()

    def _cmd_start_driver(self, arg):
        """start_driver id - starts this driver driver. use the id from command 'list': START_DRIVER name"""
        driver_id = self._get_id_from_arg(arg)
        if driver_id is not None:
            driver = self._drivers[driver_id]
            if not driver._is_stopped.is_set():
                print("[{}] is already running".format(driver_id))
            else:
                print("starting [{}]: {}".format(driver_id, driver.get_short_info()))
                ch = pelops.ui.tools.get_yes_no()
                if ch == "y":
                    driver.start()

    def _cmd_restart_driver(self, arg):
        """restart_driver id - restarts this driver driver. use the id from command 'list': RESTART_DRIVER name"""
        driver_id = self._get_id_from_arg(arg)
        if driver_id is not None:
            driver = self._drivers[driver_id]
            if driver._is_stopped.is_set():
                print("[{}] is not running".format(driver_id))
            else:
                print("restarting [{}]: {}".format(driver_id, driver.get_short_info()))
                ch = pelops.ui.tools.get_yes_no()
                if ch == "y":
                    driver.restart()

    def _cmd_reload_driver(self, arg):
        """reload_driver id - reload this driver driver. use the id from command 'list': RELOAD_DRIVER name"""
        driver_id = self._get_id_from_arg(arg)
        if driver_id is not None:
            driver = self._drivers[driver_id]
            print("reloading [{}]: {}".format(driver_id, driver.get_short_info()))
            ch = pelops.ui.tools.get_yes_no()
            if ch == "y":
                self._driver_factory.reload_driver(self._drivers, driver_id)

    def _cmd_list_drivers(self, arg):
        """list_driverss - list all drivers: LIST_DRIVERS"""
        text = ""
        for key, driver in self._drivers.items():
            text += "{}: {}\n".format(key, driver.get_short_info())
        pelops.ui.tools.more(text)

    def _start(self):
        """Starts all active drivers."""
        self._logger.warning("DriverManager started")
        for driver in self._drivers.values():
            driver.start()

    def _add_driver_ui_commands(self):
        self._logger.info("loading ui commands")
        for prefix, driver in self._drivers.items():
            prefix = prefix + "_"
            driver.load_ui_commands(prefix)

    def _stop(self):
        """Stops all active drivers."""
        for driver in self._drivers.values():
            driver.stop()
        self._logger.warning("DriverManager stopped")

    @classmethod
    def _get_description(cls):
        return "Device Driver Manager\n" \
               "In Greek mythology, Copreus (Κοπρεύς) was King Eurystheus' herald. He announced Heracles' Twelve " \
               "Labors. This script starts several device driver on a raspberry pi and connects them to MQTT. " \
               "Thus, copreus takes commands from the king (MQTT) and tells the hero (Device) what its labors " \
               "are. Further, copreus reports to the king whatever the hero has to tell him."

    @classmethod
    def _get_schema(cls):
        return get_schema()

    def runtime_information(self):
        info = {
            "drivers": []
        }
        for driver in self._drivers.values():
            info["drivers"].append(driver.runtime_information())
        return info

    def config_information(self):
        info = {
            "drivers": []
        }
        for driver in self._drivers.values():
            info["drivers"].append(driver.config_information())
        return info


def standalone():
    """Calls the static method DriverManager.standalone()."""
    DriverManager.standalone()


if __name__ == "__main__":
    DriverManager.standalone()
