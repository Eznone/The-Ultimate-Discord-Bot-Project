from pelops.monitoring_agent.states.aagentstate import AAgentState
from pelops.monitoring_agent.states.event_ids import event_ids
from asyncscheduler import AsyncScheduler


class Active(AAgentState):
    send_config = None
    send_config_interval = 0
    send_ping = None
    send_ping_interval = 0
    send_runtime = None
    send_runtime_interval = 0

    activate_config_on_request = None
    deactivate_config_on_request = None
    activate_end_on_request = None
    deactivate_end_on_request = None
    activate_ping_on_request = None
    deactivate_ping_on_request = None
    activate_runtime_on_request = None
    deactivate_runtime_on_request = None
    activate_reonboarding_request = None
    deactivate_reonboarding_request = None
    activate_forward_logger = None
    deactivate_forward_logger = None
    activate_receive_heartbeat = None
    deactivate_receive_heartbeat = None

    _scheduler = None

    def __init__(self, id, logger, history, sigint):
        AAgentState.__init__(self, id, logger, history, sigint)
        self._scheduler = AsyncScheduler()

    def _on_entry(self):
        if self.sigint.is_set():
            return event_ids.SIGINT

        self.activate_forward_logger()
        self.activate_runtime_on_request()
        self.activate_ping_on_request()
        self.activate_config_on_request()
        self.activate_end_on_request()
        self.activate_reonboarding_request()
        self.activate_receive_heartbeat()

        self._scheduler.start()
        if self.send_config_interval > 0:
            self._scheduler.repeat(self.send_config_interval, 1, self.send_config)
        if self.send_runtime_interval > 0:
            self._scheduler.repeat(self.send_runtime_interval, 1, self.send_runtime)
        if self.send_ping_interval > 0:
            self._scheduler.repeat(self.send_ping_interval, 1, self.send_ping)

        return None

    def _on_exit(self):
        self._scheduler.stop(wait=False)

        self.deactivate_runtime_on_request()
        self.deactivate_ping_on_request()
        self.deactivate_config_on_request()
        self.deactivate_end_on_request()
        self.deactivate_reonboarding_request()
        self.deactivate_receive_heartbeat()
        self.deactivate_forward_logger()
