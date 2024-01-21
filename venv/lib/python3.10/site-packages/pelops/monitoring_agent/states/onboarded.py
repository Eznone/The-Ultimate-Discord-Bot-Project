from pelops.monitoring_agent.states.aagentstate import AAgentState
from pelops.monitoring_agent.states.event_ids import event_ids


class Onboarded(AAgentState):
    send_config = None
    deactivate_onboarding_response = None
    activate_last_will = None

    def __init__(self, id, logger, history, sigint):
        AAgentState.__init__(self, id, logger, history, sigint)

    def _on_entry(self):
        if self.sigint.is_set():
            return event_ids.SIGINT

        self.deactivate_onboarding_response()
        self.activate_last_will()

        return event_ids.ACTIVATE

    def _on_exit(self):
        self.send_config()

