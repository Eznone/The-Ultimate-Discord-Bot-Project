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
        "hold_timeout": {
            "description": "hold time until hold event is triggered",
            "type": "number"
        }
    }

    topics_pub = {
        "button_pressed": "mqtt-translations.button_pressed",
        "button_released": "mqtt-translations.button_released",
        "button_hold": "mqtt-translations.button_hold",
        "button_state": "mqtt-translations.button_state-open and mqtt-translations.button_state-closed"
    }
    topics_sub = {
    }
    mqtt_translations = {
        "button_pressed": "value for button pressed",
        "button_released": "value for button released",
        "button_hold": "value for button hold",
        "button_state-open": "value for button state",
        "button_state-closed": "value for button state",
    }

    schema = adriver.get_schema("input", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)

    return schema

