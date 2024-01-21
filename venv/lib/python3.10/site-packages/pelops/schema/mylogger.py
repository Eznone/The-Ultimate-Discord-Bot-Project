def get_schema():
    key = "logger"
    schema = {
        "description": "Logger configuration",
        "type": "object",
        "properties": {
            "log-level": {
                "description": "Log level to be used.",
                "type": "string",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            },
            "log-file": {
                "description": "File name for the logger.",
                "type": "string"
            },
            "log-rotation": {
                "description": "parameters for log rotation (optional)",
                "type": "object",
                "properties": {
                    "maxbytes": {
                        "type": "integer",
                        "minvalue": 1,
                        "description": "Rollover occurs whenever the current log file is nearly maxBytes in length"
                    },
                    "backupcount": {
                        "type": "integer",
                        "minvalue": 1,
                        "description": "With a backupCount of 5 and a base file name of app.log, you would get "
                                       "app.log, app.log.1, app.log.2, up to app.log.5."
                    }
                },
                "required": ["maxbytes", "backupcount"]
            }

        },
        "required": ["log-level", "log-file"]
    }

    return key, schema
