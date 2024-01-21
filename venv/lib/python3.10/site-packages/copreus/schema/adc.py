import copreus.schema.adriver as adriver
import copreus.schema.apolling as apolling
import copreus.schema.aspi as aspi
import copreus.schema.calibratedvalue as calibratedvalue


def _add_schema_part(schema, schema_part):
    schema["driver"]["required"].extend(schema_part["required"])
    schema["driver"]["properties"].update(schema_part["properties"])


def get_schema():
    driver_specific_properties = {
        "maxvalue": {
            "description": "maximum value in volt. result will be normalized towards this value.",
            "type": "number"
        },
        "bit": {
            "description": "how many bits are used. typical values are 8, 10, and 12.",
            "type": "integer"
        },
    }

    topics_pub = {
        "raw": "raw (=integer value returned from adc)",
        "volt": "volt (=converted and calibrated value)"
    }

    apolling_schema_parts, topics_sub, mqtt_translations = apolling.get_schema_parts()
    schema = adriver.get_schema("adc", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)
    _add_schema_part(schema, apolling_schema_parts)
    _add_schema_part(schema, aspi.get_schema_parts())
    _add_schema_part(schema, calibratedvalue.get_schema_parts("calibration"))

    return schema
