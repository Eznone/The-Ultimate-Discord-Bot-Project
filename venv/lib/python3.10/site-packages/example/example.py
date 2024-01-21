import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from example.examplestate import ExampleState
from tantamount.machine import Machine
from tantamount.fsm2dot import GetDotNotation
import time


machine = Machine()

machine.addstate(ExampleState("A", "State A", "abc"))
machine.addstate(ExampleState("B", "State B", "abc"))
machine.addstate(ExampleState("C", "State C", "abc"))
machine.addstate(ExampleState("D", "State D", "d"))
machine.addstate(ExampleState("E", "State E", "e"))
machine.addstate(ExampleState("F", "State F", "final"))

machine.setstartstate("A")

machine.addtransition("A", 1, "B")
machine.addtransition("A", 2, "C")
machine.addtransition("A", 3, "D")
machine.addtransition("A", 4, "E")
machine.addtransition("A", 5, "F")

machine.addtransition("B", 1, "C")
machine.addtransition("B", 2, "A")
machine.addtransition("B", 3, "D")

machine.addtransition("C", 1, "A")
machine.addtransition("C", 2, "B")
machine.addtransition("C", 3, "D")

machine.addtransition("D", 1, "A")
machine.addtransition("D", 2, "B")
machine.addtransition("D", 3, "C")

machine.addtransition("E", 1, "A")

machine.addtimeoutevent("A", 3, 0.5)
machine.addtimeoutevent("B", 3, 0.5)
machine.addtimeoutevent("C", 3, 0.5)
machine.addtimeoutevent("D", 1, 0.5)
machine.addtimeoutevent("E", 1, 15)

with open("example.dot", "w") as f:
    gdn = GetDotNotation(machine)
    f.write(gdn.getdotnotation())

print(" - start machine")
machine.start()

print(" - loop back and forth")
for eventid in range(1, 3):
    print(" - eventid: {}".format(eventid))
    for loop in range(6):
        print(" -- counter: {}".format(loop+1))
        machine.operate(eventid)

print(" - first timeout")
time.sleep(0.6)
machine.operate(2)

print(" - second timeout")
time.sleep(0.6)
machine.operate(3)

print(" - third timeout")
time.sleep(0.6)
machine.operate(3)

print(" - timeout loop")
time.sleep(1.1)

print(" - long loop via E")
machine.operate(4)
time.sleep(15)

print(" - asnyoperate 3000x")
t_init = time.time()
for i in range(3000):
    machine.asyncoperate(1)
t_started = time.time()

while not machine._async_queue.empty():
    time.sleep(0.001)

t_finished = time.time()
t_init_diff = t_started - t_init
t_process_diff = time.time() - t_started
print(" - asyncoperate finished. timings init: {} s; process: {} s".format(t_init_diff, t_process_diff))

print(" - to final")
machine.operate(5)
machine.stop()
print(" - done")

