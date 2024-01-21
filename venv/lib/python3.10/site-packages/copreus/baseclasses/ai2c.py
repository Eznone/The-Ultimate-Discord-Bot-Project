from threading import Lock


class AI2C:
    _i2c_lock = None  # threading.Lock for i2c interface access

    def __init__(self, i2c_lock):
        if i2c_lock is None:
            self._i2c_lock = Lock()
        else:
            self._i2c_lock = i2c_lock
