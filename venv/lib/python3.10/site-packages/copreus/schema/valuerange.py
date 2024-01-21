def get_schema_parts(propertyname):
    return {
        "properties": {
            propertyname: {
                "description": "value range",
                "type": "object",
                "properties": {
                    "use-validation": {
                        "description": "if set to False, validation will be ommitted.",
                        "type": "boolean"
                    },
                    "max": {
                        "description": "if value > max then the value will be dropped.",
                        "type": "number"
                    },
                    "min": {
                        "description": "if value < min then the value will be dropped.",
                        "type": "number"
                    }
                },
                "required": ["max", "min", "use-validation"],
                "additionalProperties": False
            },
        },
        "required": [propertyname],
    }