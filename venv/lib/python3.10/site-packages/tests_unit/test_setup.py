import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tantamount.machine import Machine
from tantamount.simplestate import SimpleState


class TestSetup(unittest.TestCase):
    def test0_create_1(self):
        m = Machine()
        self.assertIsNotNone(m)
        self.assertFalse(m.ignore_undefined_events)
        self.assertEqual(len(m._states), 0)
        self.assertEqual(len(m._transitions), 0)
        self.assertEqual(len(m._timeoutevents), 0)
        self.assertFalse(m._startdone)
        self.assertFalse(m._stopping)
        self.assertIsNone(m._start_state)
        self.assertIsNone(m._state)

    def test0_create_2(self):
        m = Machine(ignore_undefined_events=False)
        self.assertIsNotNone(m)
        self.assertFalse(m.ignore_undefined_events)

    def test0_create_3(self):
        m = Machine(ignore_undefined_events=True)
        self.assertIsNotNone(m)
        self.assertTrue(m.ignore_undefined_events)

    def test1_add_state(self):
        m = Machine(ignore_undefined_events=True)
        self.assertIsNotNone(m)

        # happy case
        m.addstate(SimpleState("a"))
        m.addstate(SimpleState("b"))
        m.addstate(SimpleState("c"))
        self.assertEqual(len(m._states), 3)
        a = m._states["a"]
        self.assertIsNotNone(a)
        self.assertEqual(a.id, "a")
        self.assertEqual(a.groupid, "_")
        b = m._states["b"]
        self.assertIsNotNone(b)
        self.assertEqual(b.id, "b")
        self.assertEqual(b.groupid, "_")
        c = m._states["c"]
        self.assertIsNotNone(c)
        self.assertEqual(c.id, "c")
        self.assertEqual(c.groupid, "_")

        # add duplicates
        with self.assertRaises(KeyError):
            m.addstate(SimpleState("a"))
        with self.assertRaises(KeyError):
            m.addstate(SimpleState("b"))
        with self.assertRaises(KeyError):
            m.addstate(SimpleState("c"))

        # add empty id
        with self.assertRaises(ValueError):
            m.addstate(SimpleState(""))
        with self.assertRaises(ValueError):
            m.addstate(SimpleState(id=None))

    def test2_set_start_state(self):
        m = Machine(ignore_undefined_events=True)
        self.assertIsNotNone(m)
        m.addstate(SimpleState("a"))
        b = SimpleState("b")
        m.addstate(b)
        m.addstate(SimpleState("c"))
        self.assertIsNone(m._start_state)
        self.assertIsNone(m._state)
        m.setstartstate("b")
        self.assertEqual(b, m._state)
        self.assertEqual(b, m._start_state)
        x = m.get_active_state()
        self.assertEqual(x, b)

    def test3_add_transition_simple(self):
        m = Machine()
        self.assertIsNotNone(m)
        m.addstate(SimpleState("a"))
        m.addstate(SimpleState("b"))
        m.addstate(SimpleState("c"))

        # happy case
        m.addtransition("a", "ab", "b")
        m.addtransition("a", "ab2", "b")
        m.addtransition("a", "ac", "c")
        m.addtransition("a", "aa", "a")
        m.addtransition("b", "ba", "a")
        m.addtransition("b", "bc", "c")
        m.addtransition("b", "bb", "b")
        m.addtransition("c", "ca", "a")
        m.addtransition("c", "cb", "b")
        m.addtransition("c", "cc", "c")

        self.assertEqual(len(m._transitions), 3)
        self.assertEqual(len(m._transitions["a"]), 4)
        self.assertEqual(len(m._transitions["b"]), 3)
        self.assertEqual(len(m._transitions["c"]), 3)
        self.assertEqual(m._transitions["a"]["ab"].targetstateid, "b")
        self.assertEqual(m._transitions["a"]["ab2"].targetstateid, "b")
        self.assertEqual(m._transitions["a"]["ac"].targetstateid, "c")
        self.assertEqual(m._transitions["a"]["aa"].targetstateid, "a")
        self.assertEqual(m._transitions["b"]["ba"].targetstateid, "a")
        self.assertEqual(m._transitions["b"]["bc"].targetstateid, "c")
        self.assertEqual(m._transitions["b"]["bb"].targetstateid, "b")
        self.assertEqual(m._transitions["c"]["ca"].targetstateid, "a")
        self.assertEqual(m._transitions["c"]["cb"].targetstateid, "b")
        self.assertEqual(m._transitions["c"]["cc"].targetstateid, "c")

        # wrong states
        with self.assertRaises(KeyError):
            m.addtransition("x", "xb", "b")
        with self.assertRaises(KeyError):
            m.addtransition("a", "ax", "x")
        with self.assertRaises(KeyError):
            m.addtransition("x", "xy", "y")

        # wrong transition name
        with self.assertRaises(ValueError):
            m.addtransition("a", "", "b")
        with self.assertRaises(ValueError):
            m.addtransition("a", eventid=None, targetstateid="b")

        # duplication transition ids
        with self.assertRaises(KeyError):
            m.addtransition("a", "ab", "b")
        with self.assertRaises(KeyError):
            m.addtransition("a", "ab", "c")

        # same transition id but different startstateids
        m.addtransition("a", "tt", "b")
        m.addtransition("b", "tt", "b")
        m.addtransition("c", "tt", "b")

    def test4_add_transition_actions(self):
        def func_a():
            pass

        def func_b(x, y):
            pass

        m = Machine()
        self.assertIsNotNone(m)
        m.addstate(SimpleState("a"))
        m.addstate(SimpleState("b"))
        m.addstate(SimpleState("c"))

        # happy case
        m.addtransition("a", "ab", "b", actionFunc=func_a)
        m.addtransition("a", "ac", "c", actionFunc=func_b, actionArgs=("x", "y"))

        trans_ab = m._transitions["a"]["ab"]
        trans_ac = m._transitions["a"]["ac"]

        self.assertIsNotNone(trans_ab)
        self.assertIsNotNone(trans_ac)
        self.assertEqual(trans_ab.actionFunc, func_a)
        self.assertEqual(trans_ab.actionArgs, ())
        self.assertEqual(trans_ac.actionFunc, func_b)
        self.assertEqual(trans_ac.actionArgs, ("x", "y"))

        # not callable
        with self.assertRaises(ValueError):
            m.addtransition("b", "xx", "c", actionFunc="a")

        # arguments but no function
        with self.assertRaises(ValueError):
            m.addtransition("b", "xx", "c", actionArgs=("x", "y"))

    def test5_add_timeout_event(self):
        m = Machine()
        self.assertIsNotNone(m)
        m.addstate(SimpleState("a"))
        m.addstate(SimpleState("b"))
        m.addstate(SimpleState("c"))

        m.addtransition("a", "ab", "b")
        m.addtransition("a", "aa", "a")
        m.addtransition("b", "bc", "c")
        m.addtransition("c", "ca", "a")

        # happy case
        m.addtimeoutevent("a", "ab", 0)
        m.addtimeoutevent("b", "bc", 0.002)
        m.addtimeoutevent("c", "ca", 3600)

        self.assertEqual(len(m._timeoutevents), 3)
        self.assertEqual(m._timeoutevents["a"], ("ab", 0))
        self.assertEqual(m._timeoutevents["b"], ("bc", 0.002))
        self.assertEqual(m._timeoutevents["c"], ("ca", 3600))

        # wrong seconds
        with self.assertRaises(ValueError):
            m.addtimeoutevent("a", "aa", -1)

        # unknown stateid
        with self.assertRaises(KeyError):
            m.addtimeoutevent("x", "aa", 12)

        # unknown eventid
        with self.assertRaises(KeyError):
            m.addtimeoutevent("a", "xx", 11)

        # second timeoutevent from same start state
        with self.assertRaises(KeyError):
            m.addtimeoutevent("a", "aa", 10)
        with self.assertRaises(KeyError):
            m.addtimeoutevent("b", "bc", 9)

    def test6_update_timeout_event(self):
        m = Machine()
        self.assertIsNotNone(m)
        m.addstate(SimpleState("a"))
        m.addstate(SimpleState("b"))
        m.addstate(SimpleState("c"))

        m.addtransition("a", "ab", "b")
        m.addtransition("a", "aa", "a")
        m.addtransition("b", "bc", "c")
        m.addtransition("c", "ca", "a")

        m.addtimeoutevent("a", "ab", 0)
        m.addtimeoutevent("b", "bc", 0.002)

        self.assertEqual(len(m._timeoutevents), 2)
        self.assertEqual(m._timeoutevents["a"], ("ab", 0))
        self.assertEqual(m._timeoutevents["b"], ("bc", 0.002))

        # happy case
        m.updatetimeoutevent("a", "ab", 27)
        self.assertEqual(m._timeoutevents["a"], ("ab", 27))

        # wrong seconds
        with self.assertRaises(ValueError):
            m.updatetimeoutevent("a", "ab", -1)

        # unknown stateid
        with self.assertRaises(KeyError):
            m.updatetimeoutevent("x", "aa", 12)

        # unknown eventid
        with self.assertRaises(KeyError):
            m.updatetimeoutevent("a", "xx", 11)

        # no timeout event added to this state
        with self.assertRaises(KeyError):
            m.updatetimeoutevent("c", "ca", 15)


if __name__ == '__main__':
    unittest.main()

