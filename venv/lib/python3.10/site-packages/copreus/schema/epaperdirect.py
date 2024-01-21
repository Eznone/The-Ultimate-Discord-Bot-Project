import copreus.schema.adriver as adriver
import copreus.schema.apolling as apolling
import copreus.schema.aspi as aspi
import copreus.schema.calibratedvalue as calibratedvalue
import copreus.schema.aepaper as aepaper


def _add_schema_part(schema, schema_part):
    schema["driver"]["required"].extend(schema_part["required"])
    schema["driver"]["properties"].update(schema_part["properties"])


def get_schema():
    driver_specific_properties = aepaper.get_schema()

    topics_pub = {
        "message_queue_size": "publishes the number of messages that wait to be processes.",
    }

    topics_sub = {
        "full_image": "a single image covering the whole display to be placed in the current buffer.",
        "partial_image": "list of image covering only parts of the display plus their position to be placed "
                      "into the current buffer.",
        "switch_frame": "if command 'switch_buffer' is received via this topic, switch the frame buffer."
    }

    mqtt_translations = {
        "switch_frame": "command to switch between the two frames."
    }

    schema = adriver.get_schema("epaperdirect", driver_specific_properties, topics_pub, topics_sub, mqtt_translations)
    _add_schema_part(schema, aspi.get_schema_parts())

    return schema
