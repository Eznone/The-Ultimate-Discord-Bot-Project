import copreus.schema.adriver as adriver
import copreus.schema.apolling as apolling
import copreus.schema.calibratedvalue as calibratedvalue
import copreus.schema.valuerange as valuerange


def _add_schema_part(schema, schema_part):
    schema["driver"]["required"].extend(schema_part["required"])
    schema["driver"]["properties"].update(schema_part["properties"])


def get_schema():
    driver_specific_properties = {
        "port": {
            "description": "i2c port",
            "type": "number"
        },
        "address": {
            "description": "i2c address",
            "type": "number"
        },
        "event-pin": {
            "description": "input pin trigger for poll_now (optional)",
            "type": "object",
            "properties": {
                "pin": {
                    "description": "gpio pin",
                    "type": "integer"
                },
                "flank": {
                    "description": "trigger poll_now on which flank of the pin signal",
                    "type": "string",
                    "enum": ["rising", "falling", "both"]
                },
                "topics-pub": {
                    "description": "list of topics that the driver publishes to.",
                    "type": "object",
                    "properties": {
                        "button_pressed": {
                            "description": "mqtt-translations.button_pressed",
                            "type": "string"
                        },
                        "button_state": {
                            "description": "mqtt-translations.button_state-open and mqtt-translations.button_state-closed",
                            "type": "string"
                        }
                    },
                    "required": [
                        "button_pressed",
                        "button_state"
                    ],
                    "additionalItems": False
                },
                "mqtt-translations": {
                    "description": "what are the commands/states-values that are transmitted via mqtt",
                    "type": "object",
                    "properties": {
                        "button_pressed": {
                            "description": "value for button pressed",
                            "type": "string"
                        },
                        "button_state-open": {
                            "description": "value for button state",
                            "type": "string"
                        },
                        "button_state-closed": {
                            "description": "value for button state",
                            "type": "string"
                        }
                    },
                    "required": [
                        "button_pressed",
                        "button_state-open",
                        "button_state-closed"
                    ],
                    "additionalItems": False
                },
            },
            "required": ["pin", "flank"],
            "additionalProperties": False
        }
    }

    topics_pub = {
        "temperature": "raw temperature",
        "humidity": "raw humidity",
        "pressure": "raw pressure"
    }

    apolling_schema_parts, topics_sub, mqtt_translations = apolling.get_schema_parts()
    schema = adriver.get_schema("bme_280", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)
    schema["driver"]["required"].remove("event-pin")
    _add_schema_part(schema, apolling_schema_parts)
    _add_schema_part(schema, calibratedvalue.get_schema_parts("calibration-temperature"))
    _add_schema_part(schema, calibratedvalue.get_schema_parts("calibration-humidity"))
    _add_schema_part(schema, calibratedvalue.get_schema_parts("calibration-pressure"))

    _add_schema_part(schema, valuerange.get_schema_parts("valuerange-humidity"))
    _add_schema_part(schema, valuerange.get_schema_parts("valuerange-temperature"))
    _add_schema_part(schema, valuerange.get_schema_parts("valuerange-pressure"))

    return schema
