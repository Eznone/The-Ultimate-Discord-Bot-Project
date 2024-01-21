from threading import Thread


class LoggerThread(Thread):
    """
    Wrapper for threading.Thread that adds log entries for each uncaught exception in method run()
    """

    _logger = None  # instance of logger

    def __init__(self,  group=None, target=None, name=None,
                 args=(), kwargs=None, *, daemon=None, logger=None):
        self._logger = logger
        Thread.__init__(self, group=group, target=target, name=name, args=args, kwargs=kwargs, daemon=daemon)

    def run(self):
        try:
            Thread.run(self)
        except Exception as e:
            print("uncaught exception in LoggerThread '{}': {}".format(self.name, e))
            self._logger.exception(e)
            raise e
