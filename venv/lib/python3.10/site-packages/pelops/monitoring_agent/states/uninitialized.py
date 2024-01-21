from pelops.monitoring_agent.states.aagentstate import AAgentState
from pelops.monitoring_agent.states.event_ids import event_ids


class Uninitialized(AAgentState):
    update_uuid = None
    decativate_last_will = None
    deactivate_onboarding_response = None

    def __init__(self, id, logger, history, sigint):
        AAgentState.__init__(self, id, logger, history, sigint)

    def _on_entry(self):
        if self.sigint.is_set():
            return event_ids.SIGINT

        self.deactivate_onboarding_response()  # remove subscription
        self.update_uuid()
        self.decativate_last_will()

        return event_ids.NEW_UUID

    def _on_exit(self):
        pass
