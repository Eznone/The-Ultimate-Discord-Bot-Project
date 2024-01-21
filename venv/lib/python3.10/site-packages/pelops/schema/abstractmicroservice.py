import pelops.schema.apubsub
import pelops.schema.mylogger
import pelops.schema.monitoring_agent


def get_schema(sub_schema, definitions={}):
    schema = {
        "$schema": "http://json-schema.org/draft-06/schema#",
        "title": "Configuration for pelops mqtt microservices.",
        "type": "object",
        "properties": sub_schema,
        "required": [],
        "definitions": definitions 
    }

    for k in sub_schema.keys():
        schema["required"].append(k)

    key, sub = pelops.schema.apubsub.get_schema()
    schema["properties"][key] = sub
    schema["required"].append(key)

    key, sub = pelops.schema.mylogger.get_schema()
    schema["properties"][key] = sub
    schema["required"].append(key)

    key, sub = pelops.schema.monitoring_agent.get_schema()
    schema["properties"][key] = sub
    #schema["required"].append(key)  - not required. if not present. no monitoring agent will be started

    return schema
