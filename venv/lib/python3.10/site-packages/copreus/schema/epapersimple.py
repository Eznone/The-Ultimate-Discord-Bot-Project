import copreus.schema.aepaper as aepaper
import copreus.schema.adriver as adriver
import copreus.schema.apolling as apolling
import copreus.schema.aspi as aspi
import copreus.schema.calibratedvalue as calibratedvalue


def _add_schema_part(schema, schema_part):
    schema["driver"]["required"].extend(schema_part["required"])
    schema["driver"]["properties"].update(schema_part["properties"])


def get_schema():
    driver_specific_properties = aepaper.get_schema()

    driver_specific_properties["wipe-screen"] = {
        "description": "wipe (display black/white images) the screen regularly",
        "type": "object",
        "properties": {
            "every-nth-day": {
                "description": "run wipe screen every day, every second day. 0 for no scheduled wipe events",
                "type": "integer",
                "minimum": 0
            },
            "time": {
                "description": "HH:MM",
                "type": "string"
            },
            "at-start-up": {
                "description": "run wipe at startup",
                "type": "boolean"
            }
        },
        "required": ["every-nth-day", "time", "at-start-up"],
        "additionalItems": False
    }

    topics_pub = {
        "message_queue_size": "publishes the number of messages that wait to be processes.",
    }

    topics_sub = {
        "image": "a single image covering the whole display to be placed in the current buffer.",
    }

    mqtt_translations = {}

    schema = adriver.get_schema("epapersimple", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)
    _add_schema_part(schema, aspi.get_schema_parts())

    return schema