import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tantamount.machine import Machine
from tantamount.simplestate import SimpleState
from time import sleep, time
from threading import Event
import threading


def list_threads():
    print("active threads ({}):".format(threading.active_count()))
    for t in threading.enumerate():
        print(" - {} (alive: {}, daemon: {})".format(t.name, t.is_alive(), t.daemon))


class Counter:
    def __init__(self):
        self.counter = 0

    def inc(self):
        self.counter += 1


class EventState(SimpleState):
    trigger = None
    wait = None
    next_event_id = None
    counter = None

    def __init__(self, id, counter):
        SimpleState.__init__(self, id)
        self.trigger = Event()
        self.trigger.clear()
        self.counter = counter

    def on_entry(self):
        if self.wait is not None:
            sleep(self.wait)
        self.counter.inc()
        self.trigger.set()
        return self.next_event_id


# https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
# Print iterations progress
class ProgressBar:
    def __init__(self, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', msg=None):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.length = length
        self.fill = fill
        self.msg = msg
        self.lastpercent = "-1"

    def printProgressBar (self, iteration, msg=None, enforce_message=False):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
        """
        percent = ("{0:." + str(self.decimals) + "f}").format(100 * (iteration / float(self.total)))
        if percent != self.lastpercent or iteration == self.total or (enforce_message and msg is not None):
            if msg is not None:
                self.msg = msg

            filledLength = int(self.length * iteration // self.total)
            bar = self.fill * filledLength + '-' * (self.length - filledLength)
            if self.msg is None:
                print('\r%s |%s| %s%% %s' % (self.prefix, bar, percent, self.suffix), end = '\r')
            else:
                print('\r%s |%s| %s%% %s %s' % (self.prefix, bar, percent, self.suffix, self.msg), end='\r')
            if iteration == self.total:
                print()
            self.lastpercent = percent


class TestLongTerm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.testduration = 30 # test duration for each individual test in seconds
        cls.decimals = 1

    def setUp(self):
        self.m = Machine()
        self.assertIsNotNone(self.m)
        self.counter = Counter()
        self.states = {
            "a": EventState("a", self.counter),
            "b": EventState("b", self.counter),
            "c": EventState("c", self.counter),
            "d": EventState("d", self.counter),
        }
        self.m.addstate(self.states["a"])
        self.m.addstate(self.states["b"])
        self.m.addstate(self.states["c"])
        self.m.addstate(self.states["d"])
        self.m.addtransition("a", "x", "b")
        self.m.addtransition("b", "x", "c")
        self.m.addtransition("c", "x", "a")
        self.m.addtransition("a", "y", "d")
        self.m.addtransition("a", "z", "d")
        self.m.addtransition("b", "z", "d")
        self.m.addtransition("c", "z", "d")
        self.m.setstartstate("a")

        self.assertEqual(len(self.m._transitions), 3)
        self.assertEqual(len(self.m._timeoutevents), 0)
        self.assertEqual(len(self.m._states), 4)

    def tearDown(self):
        list_threads()
        if not self.m._stopping:
            self.m.stop()
        self.m = None

    @classmethod
    def tearDownClass(cls):
        print("tearDownClass ...")
        list_threads()
        print("... done")

    def test0_manual_sync(self):
        print("manual sync with {} s test duration".format(self.testduration))
        pb = ProgressBar(self.testduration, decimals=self.decimals)
        start_time = time()
        self.m.start()
        self.assertEqual(self.m.get_active_state(), self.states["a"])

        i = 0
        msg = ""
        while time()-start_time < self.testduration:
            msg = "{} operations".format(i*3)
            pb.printProgressBar(time()-start_time, msg=msg)
            for j in range(i, i+5000):
                self.m.operate("x")
                self.m.operate("x")
                self.m.operate("x")
                i = j+1
        self.m.operate("y")
        self.assertEqual(self.m.get_active_state(), self.states["d"])
        pb.printProgressBar(self.testduration, msg=" "*len(msg), enforce_message=True)
        self.m.stop()
        print("done {} opertaions in {:.3} s".format(i, time()-start_time))

    def test1_manual_async(self):
        print("manual async with approx. {} s test duration".format(self.testduration))
        fillduration = self.testduration * 0.62
        pb = ProgressBar(fillduration, prefix="filling queue   ", length=100-len("processing queue"),
                         decimals=self.decimals)
        start_time = time()

        self.m.start()
        self.assertEqual(self.m.get_active_state(), self.states["a"])

        i = 0
        msg = ""

        while time()-start_time < fillduration:
            msg = "{} operations".format(i*3)
            pb.printProgressBar(time()-start_time, msg=msg)
            for j in range(i, i+5000):
                self.m.asyncoperate("x")
                self.m.asyncoperate("x")
                self.m.asyncoperate("x")
                i = j+1

        self.m.asyncoperate("y")
        pb.printProgressBar(fillduration, msg=" "*len(msg), enforce_message=True)

        pb2 = ProgressBar((i*3), prefix="processing queue",  length=100-len("processing queue"), decimals=self.decimals)
        while not self.states["d"].trigger.is_set():
            pb2.printProgressBar((i*3)-self.m._async_queue.qsize())
            sleep(0.1)
        self.states["d"].trigger.wait()
        self.assertEqual(self.m.get_active_state(), self.states["d"])
        pb2.printProgressBar((i*3))
        self.m.stop()
        print("done {} opertaions in {:.3} s".format((i*3), time()-start_time))

    def test2_timer_long_wait(self):
        print("timer with {} s test duration".format(self.testduration))
        pb = ProgressBar(self.testduration, decimals=self.decimals)
        start_time = time()

        self.m.addtimeoutevent("a", "x", 0.1)
        self.m.addtimeoutevent("b", "x", 0.1)
        self.m.addtimeoutevent("c", "x", 0.1)

        self.m.start()
        self.assertEqual(self.m.get_active_state(), self.states["a"])

        while time()-start_time < self.testduration:
            sleep(0.1)
            pb.printProgressBar(time()-start_time)

        self.m.asyncoperate("z")
        msg = "waiting (approx. {} in queue)".format(int(self.m._async_queue.qsize()/3))
        pb.printProgressBar(self.testduration-0.1, msg=msg, enforce_message=True)
        self.states["d"].trigger.wait()
        self.assertEqual(self.m.get_active_state(), self.states["d"])
        pb.printProgressBar(self.testduration, msg=" "*len(msg), enforce_message=True)
        self.m.stop()
        print("done {} events in {:.3} s".format(self.counter.counter, time()-start_time))

    def test3_timer_no_wait(self):
        print("timer with {} s test duration".format(self.testduration))
        pb = ProgressBar(self.testduration, decimals=self.decimals)
        start_time = time()

        self.m.addtimeoutevent("a", "x", 0)
        self.m.addtimeoutevent("b", "x", 0)
        self.m.addtimeoutevent("c", "x", 0)

        self.m.start()
        self.assertEqual(self.m.get_active_state(), self.states["a"])

        while time()-start_time < self.testduration:
            sleep(0.1)
            pb.printProgressBar(time()-start_time)

        self.m.operate("z")
        msg = "waiting (approx. {} in queue)".format(int(self.m._async_queue.qsize()/3))
        pb.printProgressBar(self.testduration-0.1, msg=msg, enforce_message=True)
        self.states["d"].trigger.wait()
        self.assertEqual(self.m.get_active_state(), self.states["d"])
        pb.printProgressBar(self.testduration, msg=" "*len(msg), enforce_message=True)
        self.m.stop()
        print("done {} events in {:.3} s".format(self.counter.counter, time()-start_time))


if __name__ == '__main__':
    unittest.main()
    print("__main__ exit")
    list_threads()
    print("done")
