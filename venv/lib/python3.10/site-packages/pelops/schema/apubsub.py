def get_schema():
    key = "pubsub"
    schema = {
        "description": "pubsub servuce configuration",
        "type": "object",
        "oneOf": [
            _mymqttclient(),
            _pythonqueue()
                 ],
        "additionalItems": False
    }

    return key, schema


def _mymqttclient():
    return {
        "properties": {
            "type": {
                "description": "which pub-sub-service should be used",
                "type": "string",
                "enum": ["MQTT", "mqtt", "Mqtt"]
            },
            "log-level": {
                "description": "Log level to be used (optional).",
                "type": "string",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            },
            "mqtt-address": {
                "description": "URL of mqtt broker",
                "type": "string"
            },
            "mqtt-port": {
                "description": "Port of mqtt broker",
                "type": "integer",
                "minimum": 0,
                "exclusiveMinimum": True
            },
            "retain-messages": {
                "description": "Signal mqtt broker that messages should be retained.",
                "type": "boolean"
            },
            "qos": {
                "description": "Set quality of service for subscribe, publish, and last will.",
                "type": "integer",
                "minimum": 0,
                "maximum": 2
            },
            "credentials-file": {
                "description": "File containing the credentials (optional).",
                "type": "string"
            },
            "mqtt-user": {
                "description": "User name for mqtt broker (optional).",
                "type": "string"
            },
            "mqtt-password": {
                "description": "Password for mqtt broker (optional).",
                "type": "string"
            }
        },
        "required": ["type", "mqtt-address", "mqtt-port"],
        "additionalItems": False
    }


def _pythonqueue():
    return {
        "properties": {
            "type": {
                "description": "which pub-sub-service should be used",
                "type": "string",
                "enum": ["QUEUE", "queue", "Queue"]
            },
            "log-level": {
                "description": "Log level to be used (optional).",
                "type": "string",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            }
        },
        "required": ["type"],
        "additionalItems": False
    }
