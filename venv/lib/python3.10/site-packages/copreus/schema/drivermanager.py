import copreus.schema.adc
import copreus.schema.bme_280
import copreus.schema.dac
import copreus.schema.dht
import copreus.schema.epaperdirect
import copreus.schema.epapersimple
import copreus.schema.input
import copreus.schema.pollinginput
import copreus.schema.output
import copreus.schema.rotaryencoder
import copreus.schema.rotaryencoder2
import copreus.schema.rfid
import copreus.schema.rgbled


def _add_driver_schema(schema, driver_schema):
    driver_schema["driver"]["properties"]["active"] = {
        "description": "if set to false, the driver will not be loaded",
        "type": "boolean"
    }
    driver_schema["driver"]["required"].append("name")
    driver_schema["driver"]["required"].append("active")
    schema["drivers"]["items"]["oneOf"].append(driver_schema["driver"])


def get_schema():
    schema = {
                "drivers": {
                    "description": "Drivermanager configuration.",
                    "type": "array",
                    "items": {
                        "oneOf": [
                        ]
                    },
                    "additionalItems": False
                }
            }

    _add_driver_schema(schema, copreus.schema.adc.get_schema())
    _add_driver_schema(schema, copreus.schema.bme_280.get_schema())
    _add_driver_schema(schema, copreus.schema.dac.get_schema())
    _add_driver_schema(schema, copreus.schema.dht.get_schema())
    _add_driver_schema(schema, copreus.schema.epaperdirect.get_schema())
    _add_driver_schema(schema, copreus.schema.epapersimple.get_schema())
    _add_driver_schema(schema, copreus.schema.input.get_schema())
    _add_driver_schema(schema, copreus.schema.pollinginput.get_schema())
    _add_driver_schema(schema, copreus.schema.output.get_schema())
    _add_driver_schema(schema, copreus.schema.rotaryencoder.get_schema())
    _add_driver_schema(schema, copreus.schema.rotaryencoder2.get_schema())
    _add_driver_schema(schema, copreus.schema.rfid.get_schema())
    _add_driver_schema(schema, copreus.schema.rgbled.get_schema())


    return schema

