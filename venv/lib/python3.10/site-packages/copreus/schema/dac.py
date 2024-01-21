import copreus.schema.adriver as adriver
import copreus.schema.aspi as aspi
import copreus.schema.calibratedvalue as calibratedvalue


def _add_schema_part(schema, schema_part):
    schema["driver"]["required"].extend(schema_part["required"])
    schema["driver"]["properties"].update(schema_part["properties"])


def get_schema():
    driver_specific_properties = {
        "maxvalue": {
            "description": "maximum value in volt. volt will be normalized towards this value.",
            "type": "number"
        },
        "bit": {
            "description": "how many bits are used. typical values are 8, 10, and 12.",
            "type": "integer"
        },
        "config_dac": {
            "description": "configuration bit-sequence according to datasheet (0 if none)",
            "type": "integer"
        },
    }

    topics_pub = {
    }
    topics_sub = {
        "raw": "raw (=integer value for the dac)",
        "volt": "volt (=converted and calibrated value)",
    }
    mqtt_translations = {
    }

    schema = adriver.get_schema("dac", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)
    _add_schema_part(schema, aspi.get_schema_parts())
    _add_schema_part(schema, calibratedvalue.get_schema_parts("calibration"))

    return schema
