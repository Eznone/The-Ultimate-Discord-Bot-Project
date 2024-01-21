from collections import namedtuple
from collections import defaultdict


class StatEntry:
    """
    Counter for sent and received messages.
    """
    sent_messages = None
    received_messages = None

    def __init__(self):
        self.sent_messages = 0
        self.received_messages = 0

    def received(self):
        """increase received message counter"""
        self.received_messages += 1

    def sent(self):
        """increase sent message counter"""
        self.sent_messages += 1


class Statistics:
    """
    Holds sent/received statistics for all topics. Provides a total of received and sent messages.
    """

    def __init__(self):
        self.stats = defaultdict(StatEntry)
        self.tuple = namedtuple("Totals", ("received_messages", "sent_messages"))

    def sent(self, topic):
        """increase sent message counter for provided topic."""
        self.stats[topic].sent_messages += 1

    def recv(self, topic):
        """increase received message counter for provided topic"""
        self.stats[topic].received_messages += 1

    def get_totals(self):
        """
        sums all counter and returns a named tuple
        :return: named tuple(received_messages, sentmessages)
        """
        s = 0
        r = 0
        for stat in self.stats.values():
            s += stat.sent_messages
            r += stat.received_messages
        return self.tuple(received_messages=r, sent_messages=s)

    def get_stats(self):
        overview = {}
        recv, sent = self.get_totals()
        overview["received"] = recv
        overview["sent"] = sent

        overview["topics"] = {}
        for topic, stats in self.stats.items():
            entry = {
                "messages-received": stats.received_messages,
                "messages-sent": stats.sent_messages
            }
            overview["topics"][topic] = entry

        return overview
