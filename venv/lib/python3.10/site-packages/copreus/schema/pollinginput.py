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
        "stability-timespan": {
            "description": "for how many seconds must a new value be measured at the pin to trigger a state change",
            "type": "integer",
            "minimum": 1
        }
    }

    topics_pub = {
        "button_pressed": "mqtt-translations.button_pressed",
        "button_state": "mqtt-translations.button_state-open and mqtt-translations.button_state-closed",
        "state_undefined": "if set, a list containting the last n (defined by stability-timespan) measured values"
    }
    topics_sub = {
    }
    mqtt_translations = {
        "button_pressed": "value for button pressed",
        "button_state-open": "value for button state",
        "button_state-closed": "value for button state",
    }

    apolling_schema_parts, topics_sub, mqtt_translations_apolling = apolling.get_schema_parts()
    mqtt_translations.update(mqtt_translations_apolling)
    schema = adriver.get_schema("pollinginput", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)
    _add_schema_part(schema, apolling_schema_parts)

    return schema
