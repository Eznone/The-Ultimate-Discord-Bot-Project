class AState:
    id = None
    groupid = None
    activation_counter = None
    timerevent = None

    def __init__(self, id, groupid="_"):
        self.id = id
        if groupid is None or groupid == "":
            self.groupid = "_"
        else:
            self.groupid = groupid
        self.activation_counter = -1

    def machine_on_entry(self):
        return self.on_entry()

    def on_entry(self):
        """
        called upon entry to this state. may return a event id that triggers a new state transistion immediately.

        :return: eventid or None
        """
        raise NotImplementedError

    def machine_on_exit(self):
        self.activation_counter += 1
        self.on_exit()

    def on_exit(self):
        raise NotImplementedError
