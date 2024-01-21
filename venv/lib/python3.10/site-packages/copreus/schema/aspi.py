def get_schema_parts():
    return {
                "properties": {
                    "spi": {
                        "description": "spi configuration",
                        "type": "object",
                        "properties": {
                            "pin_cs": {
                                "description": "cable select gpio pin (if -1 or not pressent than spi-driver "
                                               "internal cs will be used. e.g. SPI_CE0_N/GPIO08 for device 0.)",
                                "type": "integer"
                            },
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
                        "required": ["pin_cs", "bus", "device", "maxspeed"],
                        "additionalItems": False
                    },
                },
                "required": ["spi"],
           }
