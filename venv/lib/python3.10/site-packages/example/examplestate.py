from tantamount.astate import AState
import time


class ExampleState(AState):
    name = ""
    count_entry = 0
    count_exit = 0
    start_time = 0

    def __init__(self, id, name, groupid):
        AState.__init__(self, id, groupid)
        self.name = name

    def on_entry(self):
        self.start_time = time.time()
        self.count_entry += 1
        print("{}.on_entry - name: {}, counter: {}".format(self.id, self.name, self.count_entry))

    def on_exit(self):
        time.sleep(0.001)
        diff = time.time() - self.start_time
        self.count_exit += 1
        print("{}.on_exit - name: {}, counter: {}, diff: {:0.2}".format(self.id, self.name, self.count_exit, diff))
