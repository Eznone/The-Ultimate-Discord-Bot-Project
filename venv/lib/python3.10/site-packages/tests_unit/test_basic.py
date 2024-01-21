import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tantamount.machine import Machine
from tantamount.simplestate import SimpleState
from time import sleep, time
from threading import Event


class EventState(SimpleState):
    trigger = None
    wait = None
    next_event_id = None

    def __init__(self, id):
        SimpleState.__init__(self, id)
        self.trigger = Event()
        self.trigger.clear()

    def on_entry(self):
        if self.wait is not None:
            sleep(self.wait)
        self.trigger.set()
        return self.next_event_id


class TestBasic(unittest.TestCase):
    def wait4trigger(self, trigger, timeout=1):
        start_time = time()
        self.assertTrue(trigger.wait(timeout=timeout))
        trigger.clear()
        return time() - start_time

    def setUp(self):
        self.m = Machine()
        self.assertIsNotNone(self.m)
        self.states = {
            "a": EventState("a"),
            "b": EventState("b"),
            "c": EventState("c")
        }
        self.m.addstate(self.states["a"])
        self.m.addstate(self.states["b"])
        self.m.addstate(self.states["c"])
        self.assertEqual(len(self.m._transitions), 0)
        self.assertEqual(len(self.m._timeoutevents), 0)
        self.assertEqual(len(self.m._states), 3)

    def tearDown(self):
        if not self.m._stopping:
            self.m.stop()
        self.m = None

    def test00_start_stop(self):
        self.m.addtransition("a", "x", "b")
        self.m.addtransition("b", "x", "c")
        self.m.addtransition("c", "x", "a")

        self.assertFalse(self.m._startdone)
        # set start state not called
        with self.assertRaises(RuntimeError):
            self.m.start()
        self.assertFalse(self.m._startdone)

        self.m.setstartstate("a")
        self.m.start()

        self.assertEqual(self.m.get_active_state(), self.states["a"])

        self.assertTrue(self.m._startdone)
        self.m.stop()

    def test01_manual_sync(self):
        self.m.addtransition("a", "x", "b")
        self.m.addtransition("b", "x", "c")
        self.m.addtransition("c", "x", "a")
        self.m.setstartstate("a")
        self.m.start()
        self.assertEqual(self.m.get_active_state(), self.states["a"])

        self.m.operate("x")
        self.assertEqual(self.m.get_active_state(), self.states["b"])
        self.m.operate("x")
        self.assertEqual(self.m.get_active_state(), self.states["c"])
        self.m.operate("x")
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        self.m.stop()

    def test02_branch_sync(self):
        self.m.addtransition("a", "x", "b")
        self.m.addtransition("b", "y", "a")
        self.m.addtransition("b", "x", "c")
        self.m.addtransition("c", "y", "b")
        self.m.addtransition("c", "x", "a")
        self.m.addtransition("a", "y", "c")
        self.m.setstartstate("a")
        self.m.start()
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        self.m.operate("x")
        self.assertEqual(self.m.get_active_state(), self.states["b"])
        self.m.operate("x")
        self.assertEqual(self.m.get_active_state(), self.states["c"])
        self.m.operate("x")
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        self.m.operate("y")
        self.assertEqual(self.m.get_active_state(), self.states["c"])
        self.m.operate("y")
        self.assertEqual(self.m.get_active_state(), self.states["b"])
        self.m.operate("y")
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        self.m.stop()

    def test03_timer_a(self):
        self.m.addtransition("a", "x", "b")
        self.m.addtransition("a", "y", "c")
        self.m.addtransition("b", "x", "c")
        self.m.addtransition("c", "x", "a")
        self.m.addtimeoutevent("a", "x", 0.5)
        self.m.addtimeoutevent("b", "x", 0.5)
        self.m.setstartstate("a")
        self.m.start()
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        self.states["a"].trigger.clear()
        self.assertGreaterEqual(self.wait4trigger(self.states["b"].trigger), 0.45)
        self.assertEqual(self.m.get_active_state().id, self.states["b"].id)
        self.assertGreaterEqual(self.wait4trigger(self.states["c"].trigger), 0.45)
        self.assertEqual(self.m.get_active_state(), self.states["c"])
        self.m.stop()

    def test03_timer_b(self):
        self.m.addtransition("a", "x", "b")
        self.m.addtransition("a", "y", "c")
        self.m.addtransition("b", "x", "c")
        self.m.addtransition("c", "x", "a")
        self.m.addtimeoutevent("a", "x", 0)
        self.m.addtimeoutevent("b", "x", 0)
        self.m.setstartstate("a")
        self.m.start()
        self.assertTrue(self.states["c"].trigger.wait(1))
        self.assertEqual(self.m.get_active_state(), self.states["c"])
        self.m.stop()

    def test04_restarttimeoutevent(self):
        self.m.addtransition("a", "x", "b")
        self.m.addtimeoutevent("a", "x", 0.5)
        self.m.setstartstate("a")
        self.m.start()
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        sleep(0.275)
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        self.m.restarttimeoutevent()
        self.assertGreaterEqual(self.wait4trigger(self.states["b"].trigger), 0.45)
        self.m.stop()

    def test05_updatetimeoutevent(self):
        self.m.addtransition("a", "x", "b")
        self.m.addtransition("b", "y", "a")
        self.m.addtimeoutevent("a", "x", 0.25)
        self.m.setstartstate("a")
        self.m.start()
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        sleep(0.15)
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        sleep(0.15)
        self.assertEqual(self.m.get_active_state(), self.states["b"])
        self.m.updatetimeoutevent("a", "x", 0.5)
        self.m.operate("y")
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        sleep(0.275)
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        sleep(0.275)
        self.assertEqual(self.m.get_active_state(), self.states["b"])
        self.m.stop()

    def test06_manual_async(self):
        a = self.states["a"]
        b = self.states["b"]
        c = self.states["c"]

        self.m.addtransition("a", "x", "b")
        self.m.addtransition("b", "x", "c")
        self.m.addtransition("c", "x", "a")
        self.m.setstartstate("a")
        self.m.asyncstart()
        self.wait4trigger(a.trigger)
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        self.m.asyncoperate("x")
        self.wait4trigger(b.trigger)
        self.assertEqual(self.m.get_active_state(), self.states["b"])
        self.m.asyncoperate("x")
        self.wait4trigger(c.trigger)
        self.assertEqual(self.m.get_active_state(), self.states["c"])
        self.m.asyncoperate("x")
        self.wait4trigger(a.trigger)
        self.assertEqual(self.m.get_active_state(), self.states["a"])
        self.m.stop()

    def test07_sync_vs_async(self):
        a = self.states["a"]
        a.wait = 0.25
        b = self.states["b"]
        c = self.states["c"]

        self.m.addtransition("a", "x", "b")
        self.m.addtransition("b", "x", "a")
        self.m.setstartstate("a")
        self.m.asyncstart()
        self.assertLess(self.wait4trigger(a.trigger), 0.05)
        self.m.operate("x")
        self.assertEqual(self.m.get_active_state(), self.states["b"])
        self.m.operate("x")
        self.assertLess(self.wait4trigger(a.trigger), 0.05)
        self.m.operate("x")
        self.assertEqual(self.m.get_active_state(), self.states["b"])
        self.m.asyncoperate("x")
        self.assertGreater(self.wait4trigger(a.trigger), 0.2)

        self.m.stop()

    def test08_event_id_sync(self):
        a = self.states["a"]
        b = self.states["b"]
        c = self.states["c"]

        self.m.addtransition("a", "x", "b")
        self.m.addtransition("b", "x", "c")
        self.m.addtransition("c", "x", "a")

        a.next_event_id = "x"
        b.wait = 0.2
        b.next_event_id = "x"
        c.wait = 0.2

        self.m.setstartstate("a")
        start_time = time()
        self.m.start()
        self.assertEqual(self.m.get_active_state(), self.states["c"])
        self.assertGreaterEqual(time()-start_time, 0.4)

        self.m.stop()

    def test09_event_id_async(self):
        a = self.states["a"]
        b = self.states["b"]
        c = self.states["c"]

        self.m.addtransition("a", "x", "b")
        self.m.addtransition("b", "x", "c")

        a.next_event_id = "x"
        b.wait = 0.2
        b.next_event_id = "x"
        c.wait = 0.2

        self.m.setstartstate("a")
        self.m.asyncstart()
        self.assertNotEqual(self.m.get_active_state(), self.states["c"])
        self.assertGreaterEqual(self.wait4trigger(c.trigger), 0.35)

        self.m.stop()

    def test10_transitionaction(self):
        def mysleep(wait=0.2):
            sleep(wait)

        a = self.states["a"]
        b = self.states["b"]
        c = self.states["c"]

        a.next_event_id = "x"
        b.next_event_id = "x"

        self.m.addtransition("a", "x", "b", actionFunc=mysleep)
        self.m.addtransition("b", "x", "c", actionFunc=mysleep, actionArgs=(0.4,))

        self.m.setstartstate("a")
        self.m.asyncstart()
        self.assertNotEqual(self.m.get_active_state(), self.states["c"])
        self.assertGreaterEqual(self.wait4trigger(c.trigger), 0.55)
        self.m.stop()


if __name__ == '__main__':
    unittest.main()
