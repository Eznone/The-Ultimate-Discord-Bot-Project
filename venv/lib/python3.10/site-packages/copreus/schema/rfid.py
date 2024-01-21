import copreus.schema.adriver as adriver
import copreus.schema.apolling as apolling


def _add_schema_part(schema, schema_part):
    schema["driver"]["required"].extend(schema_part["required"])
    schema["driver"]["properties"].update(schema_part["properties"])


def get_schema():
    driver_specific_properties = {
        "pins": {
            "description": "rfid reader pins",
            "type": "object",
            "properties": {
                "pin_rst": {
                    "description": "reset pin",
                    "type": "integer"
                },
                "pin_irq": {
                    "description": "card present/absent events",
                    "type": "integer"
                },
                "pin_cs": {
                    "description": "cable select - only necessary if spi-bus 1 or 2 is used (optional)",
                    "type": "integer"
                }
            },
            "required": ["pin_rst", "pin_irq"],
            "additionalItems": False
        },
        "spi": {
            "description": "spi configuration",
            "type": "object",
            "properties": {
                "bus": {
                    "description": "spi bus",
                    "type": "integer"
                },
                "device": {
                    "description": "spi device id",
                    "type": "integer"
                },
                "maxspeed": {
                    "description": "maximum connection speed in Hz",
                    "type": "integer"
                }
            },
            "required": ["bus", "device", "maxspeed"],
            "additionalItems": False
        },
        "pub-pattern": {
            "description": "when to publish the last read result - ONREAD (everytime the sensor has been read), ONCHANGE (only if a new value for any field has been detected)",
            "type": "string",
            "enum": ["ONREAD", "ONCHANGE"]
        }
    }

    topics_pub = {
        "uid": "the current UID or empty string",
        "present": "is a rfid tag present or absent",
        "state": "combined json structure with uid, present, trigger, and timestamp"
    }

    apolling_schema_parts, topics_sub, mqtt_translations = apolling.get_schema_parts()

    topics_sub["poll-forced"] = "listen to this topic to start spontaneus polling - overrides ONREAD"

    mqtt_translations["present-true"] = "TRUE"
    mqtt_translations["present-false"] = "FALSE"
    schema = adriver.get_schema("rfid", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)
    _add_schema_part(schema, apolling_schema_parts)

    return schema

