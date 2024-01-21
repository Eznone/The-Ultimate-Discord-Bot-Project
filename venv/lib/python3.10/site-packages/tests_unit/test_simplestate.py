import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tantamount.simplestate import SimpleState


class TestSimpleState(unittest.TestCase):
    def test0_create_happy(self):
        s = SimpleState("a")
        self.assertIsNotNone(s)
        self.assertEqual(s.id, "a")
        self.assertEqual(s.groupid, "_")

        p = SimpleState("b", "x")
        self.assertIsNotNone(p)
        self.assertEqual(p.id, "b")
        self.assertEqual(p.groupid, "x")

    def test1_create_unhappy(self):
        with self.assertRaises(TypeError):
            s = SimpleState()
        with self.assertRaises(TypeError):
            s = SimpleState(groupid="x")

    def test3_execute(self):
        s = SimpleState("a")
        s.machine_on_entry()
        s.machine_on_exit()
        s.machine_on_entry()
        s.machine_on_exit()

    def test4_activation_counter(self):
        s = SimpleState("a")
        self.assertEqual(s.activation_counter, -1)
        s.machine_on_entry()
        self.assertEqual(s.activation_counter, -1)
        s.machine_on_exit()
        self.assertEqual(s.activation_counter, 0)
        s.machine_on_entry()
        self.assertEqual(s.activation_counter, 0)
        s.machine_on_exit()
        self.assertEqual(s.activation_counter, 1)


if __name__ == '__main__':
    unittest.main()
