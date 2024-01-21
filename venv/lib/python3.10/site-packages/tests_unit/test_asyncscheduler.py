import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from asyncscheduler import AsyncScheduler
import time
from threading import Event


class TestAsyncScheduler(unittest.TestCase):
    def test00_init(self):
        a = AsyncScheduler()
        self.assertIsNotNone(a)

    def test01_start_stop(self):
        a = AsyncScheduler()
        self.assertIsNotNone(a)
        self.assertFalse(a._stop.is_set())
        a.start()
        self.assertFalse(a._stop.is_set())
        time.sleep(0.1)
        a.stop()
        self.assertTrue(a._stop.is_set())

    def test02_add_event_a(self):
        event1 = Event()

        a = AsyncScheduler()
        a.enter(0.1, 1, event1.set)
        a.start()
        self.assertTrue(event1.wait(0.2))
        a.stop()

    def test02_add_event_b(self):
        event1 = Event()

        a = AsyncScheduler()
        a.start()
        a.enter(0.1, 1, event1.set)
        self.assertTrue(event1.wait(0.2))
        a.stop()

    def test03_add_eventabs_a(self):
        event1 = Event()

        a = AsyncScheduler()
        a.enterabs(time.time()+0.1, 1, event1.set)
        a.start()
        self.assertTrue(event1.wait(0.2))
        a.stop()

    def test03_add_eventabs_b(self):
        event1 = Event()

        a = AsyncScheduler()
        a.start()
        a.enterabs(time.time()+0.1, 1, event1.set)
        self.assertTrue(event1.wait(0.2))
        a.stop()

    def test04_remove_event_a(self):
        event1 = Event()

        a = AsyncScheduler()
        e = a.enter(0.1, 1, event1.set)
        a.cancel(e)
        a.start()
        self.assertFalse(event1.wait(0.11))
        a.stop()

    def test04_remove_event_b(self):
        event1 = Event()

        a = AsyncScheduler()
        e = a.enter(0.1, 1, event1.set)
        a.start()
        a.cancel(e)
        self.assertFalse(event1.wait(0.11))
        a.stop()

    def test05_clear_scheduler_a(self):
        event1 = Event()
        event2 = Event()

        a = AsyncScheduler()
        a.enter(0.05, 1, event1.set)
        a.enter(0.07, 1, event2.set)
        a.clear_scheduler()
        self.assertTrue(a.scheduler.empty())
        a.start()
        self.assertFalse(event1.wait(0.06))
        self.assertFalse(event1.wait(0.03))
        a.stop()

    def test05_clear_scheduler_b(self):
        event1 = Event()
        event2 = Event()

        a = AsyncScheduler()
        a.enter(0.05, 1, event1.set)
        a.enter(0.07, 1, event2.set)
        a.start()
        a.clear_scheduler()
        self.assertTrue(a.scheduler.empty())
        self.assertFalse(event1.wait(0.06))
        self.assertFalse(event1.wait(0.03))
        a.stop()

    def test06_stop_wait(self):
        event1 = Event()
        event2 = Event()

        a = AsyncScheduler()
        a.enter(0.1, 1, event1.set)
        a.enter(0.1, 1, event2.set)
        start_time = time.time()
        a.start()
        self.assertFalse(event1.is_set())
        self.assertFalse(event2.is_set())
        self.assertTrue(len(a.scheduler.queue), 2)
        a.stop()
        time_diff = time.time() - start_time
        self.assertEqual(len(a.scheduler.queue), 0)
        self.assertTrue(event1.is_set())
        self.assertTrue(event2.is_set())
        self.assertGreaterEqual(time_diff, 0.1)
        self.assertLess(time_diff, 0.1*1.1)

    def test07_stop_nowait(self):
        event1 = Event()
        event2 = Event()

        a = AsyncScheduler()
        a.enter(0.1, 1, event1.set)
        a.enter(0.1, 1, event2.set)
        start_time = time.time()
        a.start()
        self.assertFalse(event1.is_set())
        self.assertFalse(event2.is_set())
        self.assertTrue(len(a.scheduler.queue), 2)
        a.stop(wait=False)
        time_diff = time.time() - start_time
        self.assertEqual(len(a.scheduler.queue), 0)
        self.assertFalse(event1.is_set())
        self.assertFalse(event2.is_set())
        self.assertLess(time_diff, 0.05)

    def test08_enter_args(self):
        def wait(event, duration):
            time.sleep(duration)
            event.set()

        event1 = Event()

        a = AsyncScheduler()
        a.enter(0.5, 1, wait, args=(event1, 0.5,))
        start_time = time.time()
        a.start()
        self.assertTrue(event1.wait(1.5))
        time_diff = time.time() - start_time
        self.assertLess(time_diff, 1.2)
        a.stop()

    def test09_enter_kwargs(self):
        def wait(event, duration):
            time.sleep(duration)
            event.set()

        event1 = Event()

        a = AsyncScheduler()
        a.enter(0.5, 1, wait, kwargs={"event":event1, "duration":0.5})
        start_time = time.time()
        a.start()
        self.assertTrue(event1.wait(1.5))
        time_diff = time.time() - start_time
        self.assertLess(time_diff, 1.2)
        a.stop()

    def test10_enter_args_kwargs(self):
        def wait(event, duration):
            time.sleep(duration)
            event.set()

        event1 = Event()

        a = AsyncScheduler()
        a.enter(0.5, 1, wait, args=(event1,), kwargs={"duration":0.5})
        start_time = time.time()
        a.start()
        self.assertTrue(event1.wait(1.5))
        time_diff = time.time() - start_time
        self.assertLess(time_diff, 1.2)
        a.stop()

    def test11_priorities(self):
        def add_to_list(list, name):
            list.append(name)

        l = []

        a = AsyncScheduler()
        t = time.time() + 0.05
        a.enterabs(t, action=add_to_list, args=(l, "a"), priority=2)
        a.enterabs(t, action=add_to_list, args=(l, "b"), priority=0)
        a.enterabs(t, action=add_to_list, args=(l, "c"), priority=1)

        a.start()
        a.stop()

        self.assertEqual(len(l), 3)
        self.assertListEqual(l, ["b", "c", "a"])

    def test12_insert_event_before_last_event(self):
        event1 = Event()
        event2 = Event()

        a = AsyncScheduler()
        a.start()
        a.enter(1, 1, event1.set)
        time.sleep(0.1)
        a.enter(0.4, 1, event2.set)
        self.assertFalse(event1.is_set())
        self.assertFalse(event2.is_set())
        self.assertTrue(len(a.scheduler.queue), 2)
        self.assertTrue(event2.wait(timeout=0.5))
        time.sleep(0.1)
        self.assertFalse(event1.is_set())
        self.assertTrue(event1.wait(timeout=0.5))
        self.assertEqual(len(a.scheduler.queue), 0)
        a.stop()

    def test13_repeat_nowait(self):
        global events
        events = []

        def action():
            global events
            events.append(time.time())

        a = AsyncScheduler()
        a.start()
        repeat = 0.25
        start_time = time.time()
        wait_time = repeat * 4 + repeat / 2
        a.repeat(repeat, 1, action)
        time.sleep(wait_time)
        a.stop(wait=False)
        self.assertEqual(len(events), 4)
        self.assertLess((time.time()-start_time), repeat*5)

    def test14_repeat_wait(self):
        global events
        events = []

        def action():
            global events
            events.append(time.time())

        a = AsyncScheduler()
        a.start()
        repeat = 0.25
        start_time = time.time()
        wait_time = repeat * 4 + repeat / 2
        a.repeat(repeat, 1, action)
        time.sleep(wait_time)
        a.stop(wait=True)
        self.assertEqual(len(events), 5)
        self.assertGreaterEqual((time.time()-start_time), repeat*5)

    def test15_repeat_cancel_a(self):
        global events
        events = []

        def action():
            global events
            events.append(time.time())

        a = AsyncScheduler()
        a.start()
        repeat = 0.25
        start_time = time.time()
        wait_time = repeat * 4 + repeat / 2
        e = a.repeat(repeat, 1, action)
        time.sleep(wait_time)
        a.cancel(e)
        a.stop(wait=True)
        self.assertEqual(len(events), 4)
        self.assertLess((time.time()-start_time), repeat*5)

    def test15_repeat_cancel_b(self):
        global events
        events = []

        def action():
            global events
            events.append(time.time())

        a = AsyncScheduler()
        a.start()
        repeat = 0.25
        start_time = time.time()
        wait_time = repeat * 4 + repeat / 2 - 0.1
        e = a.repeat(repeat, 1, action)
        a.repeat(repeat, 1, action)
        time.sleep(wait_time)
        a.cancel(e)
        time.sleep(wait_time)
        self.assertEqual(len(events), 12)
        a.stop(wait=True)
        self.assertEqual(len(events), 13)

    def test16_performance(self):
        def action():
            pass

        a = AsyncScheduler()

        process_start = time.process_time()
        time_start = time.time()
        a.start()
        a.enter(0.25, 1, action)
        time.sleep(0.5)
        a.stop(wait=False)
        process_diff = time.process_time() - process_start
        time_diff = time.time() - time_start

        self.assertGreaterEqual(time_diff, 0.5)
        self.assertLess(process_diff, 0.001)

    def test17_repeatabs(self):
        global events
        events = []

        def action():
            global events
            t = time.time()
            events.append(t)

        a = AsyncScheduler()
        a.start()
        repeat = 0.25
        start_time = time.time()
        wait_time = repeat * 8 + repeat / 2
        timeabs = time.time() + (10 - time.time() % 10)
        a.repeatabs(timeabs, repeat, 1, action)
        time.sleep((timeabs-time.time()) + wait_time)
        a.stop(wait=False)
        prev = events[0]-start_time
        for e in events[1:]:
            diff = e-start_time-prev
            self.assertGreaterEqual(diff, 0.24)
            self.assertLessEqual(diff, 0.26)
            prev = e-start_time
        self.assertEqual(len(events), 9)
        self.assertLess((time.time()-timeabs), repeat*10)


if __name__ == '__main__':
    unittest.main()



