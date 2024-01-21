def get_schema_parts(propertyname):
    return {
        "properties": {
            propertyname: {
                "description": "calibration",
                "type": "object",
                "properties": {
                    "values": {
                        "description": "list of calibration values",
                        "type": ["array", "null"],
                        "items": {
                            "type": "array",
                            "items": [
                                {"type": "number"},
                                {"type": "number"}
                            ]
                        }
                    },
                    "use-calibration": {
                        "description": "if set to False, calibration will be ommitted.",
                        "type": "boolean"
                    }
                },
                "required": ["values", "use-calibration"],
                "additionalProperties": False
            },
        },
        "required": [propertyname],
    }