import copreus.schema.adriver as adriver
import copreus.schema.apolling as apolling
import copreus.schema.aspi as aspi
import copreus.schema.calibratedvalue as calibratedvalue


def _add_schema_part(schema, schema_part):
    schema["driver"]["required"].extend(schema_part["required"])
    schema["driver"]["properties"].update(schema_part["properties"])


def get_schema():
    driver_specific_properties = {
        "pin-red": {
            "description": "gpio pin red",
            "type": "integer"
        },
        "pin-green": {
            "description": "gpio pin green",
            "type": "integer"
        },
        "pin-blue": {
            "description": "gpio pin blue",
            "type": "integer"
        },
        "physical-closed-red": {
            "description": " high/low - mapping between logcial states (closed/open) and physical "
                           "output parameters (low/high)",
            "type": "string",
            "enum": ["low", "high"]
        },
        "physical-closed-green": {
            "description": " high/low - mapping between logcial states (closed/open) and physical "
                           "output parameters (low/high)",
            "type": "string",
            "enum": ["low", "high"]
        },
        "physical-closed-blue": {
            "description": " high/low - mapping between logcial states (closed/open) and physical "
                           "output parameters (low/high)",
            "type": "string",
            "enum": ["low", "high"]
        },
        "initial-color": {
            "description": "color at startup",
            "type": "string",
            "enum": ["BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "AQUA", "MAGENTA"]
        }
    }

    topics_pub = {
    }
    topics_sub = {
        "command": "/test/rgbled"  # four different message types are accepted: rgb, color, blink_symmetric, blink_asymmetric
    }
    mqtt_translations = {
    }

    schema = adriver.get_schema("rgbled", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)

    return schema
