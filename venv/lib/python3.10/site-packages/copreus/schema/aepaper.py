def get_schema():
    basic_aeschema_properties = {
        "model": {
            "description": "display-type. one of the keys of EPaperMQTTMessageConverter.size. [1.54, 2.13, 2.9, ...]",
            "type": "number",
            "enum": [1.54, 2.13, 2.9]

        },
        "transpose": {
            "description": "0/90/180/270 rotation applied to all received images.",
            "type": "integer",
            "enum": [0, 90, 180, 270]
        },
        "pin_rst": {
            "description": "reset gpio pin. according to data sheet",
            "type": "integer"
        },
        "pin_dc": {
            "description": "data/command pin. flag if value is to be interpreted as command or as data (see "
                           "data sheet).",
            "type": "integer"
        },
        "pin_busy": {
            "description": "busy flag. set by epaper (see data sheet).",
            "type": "integer"
        },
        "autodeepsleep": {
            "description": "if true, epaper is set to deep sleep after each update.",
            "type": "boolean"
        },
        "vcom": {
            "description": "set vcom supply to given level. (-0.2steps - -3.3 in 0.1V steps; value used in waveform "
                           "demo is -3.2V)",
            "type": "number",
            "minimum": -3.3,
            "maximum": -0.2
        },
    }

    return basic_aeschema_properties
