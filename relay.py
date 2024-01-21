import time

import RPi.GPIO as GPIO

# Default put
OUTPUT = {14:False, 15:False, 18: False}
INPUT = [2]

# Special pins
IN1 = 14
IN2 = 15
U_TRIG = 18
U_ECHO = 2

class WrongPutType(Exception):
    pass

def on(pin: int):
    if pin in INPUT: raise WrongPutType
    OUTPUT[pin] = True
    GPIO.output(pin, GPIO.LOW)

def off(pin: int):
    if pin in INPUT: raise WrongPutType
    OUTPUT[pin] = False
    GPIO.output(pin, GPIO.HIGH)

def toggle(pin: int):
    if pin in INPUT: raise WrongPutType
    if OUTPUT[pin]:
        OUTPUT[pin] = False
        GPIO.output(pin, GPIO.LOW)
    else:
        OUTPUT[pin] = True
        GPIO.output(pin, GPIO.HIGH)


def state(pin: int):
    if pin in INPUT:
        return GPIO.input(pin)
    elif pin in OUTPUT.keys():
        return OUTPUT[pin]
    GPIO.output(pin, GPIO.LOW)

def put(pin: int, putmode: str):
    """
    :param pin: BCM GPIO pin number
    :param putmode: "in" or "out" determines which put mode it will be in (output/input).
    :return: None
    """
    if pin in OUTPUT.keys() or pin in INPUT:
        del OUTPUT[pin]
        INPUT.remove(pin)
    if putmode.lower() == "out":
        OUTPUT[pin] = False

def cleanup(force=False):
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    if force:
        for i in range(2,28):
            GPIO.setup(i, GPIO.IN)

GPIO.setmode(GPIO.BCM)
for i in OUTPUT:
    GPIO.setup(i, GPIO.OUT)
    off(i)
for i in INPUT:
    GPIO.setup(i, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)