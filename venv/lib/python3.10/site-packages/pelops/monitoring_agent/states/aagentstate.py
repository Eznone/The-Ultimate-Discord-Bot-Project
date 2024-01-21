from tantamount.astate import AState
import pelops.logging.mylogger
import datetime
from pelops.monitoring_agent.states.history_type import HistoryEntry


class AAgentState(AState):
    logger = None
    sigint = None
    history = None

    def __init__(self, id, logger, history, sigint):
        AState.__init__(self, id)
        self.logger = pelops.logging.mylogger.get_child(logger, self.__class__.__name__)
        self.sigint = sigint
        self.history = history
        self.logger.info("create state '{}'".format(self.__class__.__name__))

    def on_entry(self):
        self.logger.info("on_entry - start")
        self.history.append(HistoryEntry(datetime.datetime.now(), self.__class__.__name__))
        result = self._on_entry()
        self.logger.info("on_entry - finished")
        return result

    def on_exit(self):
        self.logger.info("on_exit - start")
        self._on_exit()
        self.logger.info("on_exit - finished")

    def _on_entry(self):
        raise NotImplementedError

    def _on_exit(self):
        raise NotImplementedError
