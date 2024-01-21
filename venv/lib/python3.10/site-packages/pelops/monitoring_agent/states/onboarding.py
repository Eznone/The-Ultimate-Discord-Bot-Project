from pelops.monitoring_agent.states.aagentstate import AAgentState
from pelops.monitoring_agent.states.event_ids import event_ids


class Onboarding(AAgentState):
    send_onboarding_request = None

    def __init__(self, id, logger, history, sigint):
        AAgentState.__init__(self, id, logger, history, sigint)

    def _on_entry(self):
        if self.sigint.is_set():
            return event_ids.SIGINT

        self.send_onboarding_request()

        return None

    def _on_exit(self):
        pass
