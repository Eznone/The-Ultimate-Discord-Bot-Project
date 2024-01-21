import copreus.schema.adriver as adriver
import copreus.schema.apolling as apolling
import copreus.schema.aspi as aspi
import copreus.schema.calibratedvalue as calibratedvalue


def _add_schema_part(schema, schema_part):
    schema["driver"]["required"].extend(schema_part["required"])
    schema["driver"]["properties"].update(schema_part["properties"])


def get_schema():
    driver_specific_properties = {
        "pin_sw": {
            "description": "gpio pin",
            "type": "integer"
        },
        "pin_dt": {
            "description": "gpio pin",
            "type": "integer"
        },
        "pin_clk": {
            "description": "gpio pin",
            "type": "integer"
        },
    }

    topics_pub = {
        "rotate": "mqtt-translations.rotate-left and mqtt-translations.rotate-right",
        "button_pressed": "mqtt-translations.button_pressed",
        "button_state": "mqtt-translations.button_state-open and mqtt-translations.button_state-closed"
    }
    topics_sub = {
    }
    mqtt_translations = {
        "rotate-left": "value for rotate left",
        "rotate-right": "value for rotate right",
        "button_pressed": "value for button pressed",
        "button_state-open": "value for button state",
        "button_state-closed": "value for button state",
    }

    schema = adriver.get_schema("rotaryencoder", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)

    return schema
