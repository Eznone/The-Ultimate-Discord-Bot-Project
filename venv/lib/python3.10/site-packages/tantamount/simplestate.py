from tantamount.astate import AState


class SimpleState(AState):
    def __init__(self, id, groupid="_"):
        AState.__init__(self, id, groupid)

    def on_entry(self):
        pass

    def on_exit(self):
        pass
