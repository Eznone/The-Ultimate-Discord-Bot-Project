import copreus.schema.adriver as adriver
import copreus.schema.apolling as apolling
import copreus.schema.aspi as aspi
import copreus.schema.calibratedvalue as calibratedvalue


def _add_schema_part(schema, schema_part):
    schema["driver"]["required"].extend(schema_part["required"])
    schema["driver"]["properties"].update(schema_part["properties"])


def get_schema():
    driver_specific_properties = {
        "pin": {
            "description": "gpio pin",
            "type": "integer"
        },
        "physical-closed": {
            "description": " high/low - mapping between logcial states (closed/open) and physical "
                           "output parameters (low/high)",
            "type": "string",
            "enum": ["low", "high"]
        },
        "initially-closed": {
            "description": "True/False - defines if the output is opened or closed after start of driver",
            "type": "boolean"
        }
    }

    topics_pub = {
    }
    topics_sub = {
        "closed": " mqtt-translations.closed-true and mqtt-translations.closed-false"
    }
    mqtt_translations = {
        "closed-true": "value for closed output",
        "closed-false": "value for open output",
    }

    schema = adriver.get_schema("output", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)

    return schema
