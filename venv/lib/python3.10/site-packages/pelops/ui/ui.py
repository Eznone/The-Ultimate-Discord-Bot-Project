from cmd import Cmd
from pelops.mythreading import LoggerThread
from pelops.logging.mylogger import get_child


class UI(Cmd):
    intro = None
    prompt = None
    _stop_service_cmd = None
    _service_is_stopping = None
    _stopping = None
    _logger = None

    def __init__(self, intro, prompt, stop_service_cmd, service_is_stopping, logger):
        self._logger = get_child(logger, __class__.__name__)
        self.intro = intro
        self.prompt = prompt
        self._stopping = False

        Cmd.__init__(self)

        self._stop_service_cmd = stop_service_cmd
        self._service_is_stopping = service_is_stopping
        self._main_thread = LoggerThread(target=self._wrapper, name=__class__.__name__+".wrapper", logger=self._logger)

    def start(self):
        self._main_thread.start()

    def stop(self):
        if not self._stopping:
            self.onecmd("exit")
        self._main_thread.join()

    def _wrapper(self):
        self._stopping = False
        self.cmdloop()
        self._stopping = True
        if not self._service_is_stopping.is_set():
            stop_daemon = LoggerThread(target=self._stop_service_cmd, name=__class__.__name__+" stop command",
                                       logger=self._logger)
            stop_daemon.daemon = True
            stop_daemon.start()

    def onecmd(self, line): 
        try:
            return super().onecmd(line)
        except Exception as e:
            self._logger.exception(e)
            print("Caught exception: {}".format(e))

    def do_exit(self, arg):
        """exit - stops the monitoring service: EXIT"""
        return True

    def do_e(self, arg):
        # """shortcut for 'exit'"""
        return True

    def do_q(self, arg):
        # """shortcut for 'exit'"""
        return True

    @classmethod
    def add_command(cls, name, function):
        cmd_name = "do_"+name

        try:
            getattr(cls, cmd_name)
            raise ValueError("command '{}' already defined".format(name))
        except AttributeError:
            pass  # expected behavior

        if not callable(function):
            raise AttributeError("parameter function must be callable")

        setattr(cls, cmd_name, function)
