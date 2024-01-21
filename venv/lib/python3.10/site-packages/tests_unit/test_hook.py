import unittest
from threading import Event
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tantamount.simplestate import SimpleState
from tantamount.machine import Machine


class ForwarderState(SimpleState):
    transition_id = None

    def __init__(self, id, transition_id):
        SimpleState.__init__(self, id)
        self.transition_id = transition_id

    def on_entry(self):
        SimpleState.on_entry(self)
        return self.transition_id


class TestHook(unittest.TestCase):
    def test0_register(self):
        def hook(a, b, c):
            pass

        m = Machine()
        m.registertransitionhook(hook)
        self.assertIsNotNone(m._transition_hook)
        self.assertEqual(hook, m._transition_hook)

    def test1_clear(self):
        def hook(a, b, c):
            pass

        m = Machine()
        m.registertransitionhook(hook)
        self.assertIsNotNone(m._transition_hook)
        self.assertEqual(hook, m._transition_hook)
        m.cleartransitionhook()
        self.assertIsNone(m._transition_hook)

    def test2_one_manual_transition(self):
        global hookresults
        hookresults = []
        global hookevent
        hookevent = Event()
        hookevent.clear()

        def hook(start_state_id, transition_id, target_state_id):
            global hookresults
            hookresults.append({
                "start": start_state_id,
                "target": target_state_id,
                "transition": transition_id
            })
            global hookevent
            hookevent.set()

        a = SimpleState("a")
        b = SimpleState("b")
        m = Machine()
        m.addstate(a)
        m.addstate(b)
        m.addtransition("a", "ab", "b")
        m.setstartstate("a")
        m.registertransitionhook(hook)

        m.start()
        self.assertEqual(len(hookresults), 0)
        m.operate("ab")
        self.assertTrue(hookevent.wait(1))
        self.assertEqual(len(hookresults), 1)
        m.stop()
        self.assertEqual(len(hookresults), 1)
        self.assertEqual({"start": "a", "target": "b", "transition": "ab"}, hookresults[0])

    def test3_one_manual_one_auto_transition(self):
        global hookresults
        hookresults = []
        global hookevent
        hookevent = Event()
        hookevent.clear()

        def hook(start_state_id, transition_id, target_state_id):
            global hookresults
            hookresults.append({
                "start": start_state_id,
                "target": target_state_id,
                "transition": transition_id
            })
            global hookevent
            hookevent.set()

        a = SimpleState("a")
        b = ForwarderState("b", "bc")
        c = SimpleState("c")
        m = Machine()
        m.addstate(a)
        m.addstate(b)
        m.addstate(c)
        m.addtransition("a", "ab", "b")
        m.addtransition("b", "bc", "c")
        m.setstartstate("a")
        m.registertransitionhook(hook)

        m.start()
        self.assertEqual(len(hookresults), 0)
        m.operate("ab")
        self.assertTrue(hookevent.wait(1))
        self.assertEqual(len(hookresults), 2)
        m.stop()
        self.assertEqual(len(hookresults), 2)
        self.assertEqual({"start": "a", "target": "b", "transition": "ab"}, hookresults[0])
        self.assertEqual({"start": "b", "target": "c", "transition": "bc"}, hookresults[1])


if __name__ == '__main__':
    unittest.main()
