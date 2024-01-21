from pelops.monitoring_agent.states.aagentstate import AAgentState
from pelops.monitoring_agent.states.event_ids import event_ids


class Initialized(AAgentState):
    activate_onboarding_response = None

    def __init__(self, id, logger, history, sigint):
        AAgentState.__init__(self, id, logger, history, sigint)

    def _on_entry(self):
        if self.sigint.is_set():
            return event_ids.SIGINT

        self.activate_onboarding_response()

        return event_ids.ONBOARDING_REQUEST

    def _on_exit(self):
        pass
