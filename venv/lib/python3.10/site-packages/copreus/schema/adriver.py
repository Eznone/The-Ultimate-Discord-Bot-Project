def _add_property_object(schema, key, entries, description):
    if len(entries) > 0:
        prop = {
            "description": description,
            "type": "object",
            "properties": {
            },
            "required": [],
            "additionalItems": False
        }
        for k,v in entries.items():
            prop["properties"][k] = {
                "description": v,
                "type": "string"
            }
            prop["required"].append(k)
        schema["driver"]["properties"][key] = prop
        schema["driver"]["required"].append(key)
    return schema


def _add_properties(schema, properties):
    for k, v in properties.items():
        schema["driver"]["properties"][k] = v
        schema["driver"]["required"].append(k)
    return schema


def get_schema(type, driver_specific_properties, topics_pub, topics_sub, mqtt_translations):
    schema = {
                "driver": {
                    "description": "Driver configuration '{}'.".format(type),
                    "type": "object",
                    "properties": {
                        "name": {
                            "description": "name of driver",
                            "type": "string"
                        },
                        "type": {
                            "description": "type of driver",
                            "type": "string",
                            "enum": [type]
                        },
                    },
                    "required": ["type"],
                    "additionalItems": False
                }
             }

    schema = _add_properties(schema, driver_specific_properties)
    schema = _add_property_object(schema, "topics-pub", topics_pub, "list of topics that the driver publishes to.")
    schema = _add_property_object(schema, "topics-sub", topics_sub, "list of topics that the driver subscribes to.")
    schema = _add_property_object(schema, "mqtt-translations", mqtt_translations, "what are the commands/states-values "
                                                                                  "that are transmitted via mqtt")

    return schema
