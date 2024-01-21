import sched
import threading
from time import time as timefunc


class AsyncScheduler:
    """
    AsyncScheduler is a wrapper for sched.scheduler that provides asynchronous operation out of the box. Thus, starting
    the scheduler does not block the execution of the next statements. Further, adding and removing events can be done
    without manually stopping/starting the scheduler.

    The event itself is executed synchronously. Consequently, it the execution of the calling method takes longer than
    the delay to the next event, execution of the next method is postponed until the previous method returns.
    """

    scheduler = None  # instance of sched.scheduler
    _thread = None  # thread that runs the scheduler
    _delayfunc = None  # delay function for scheduler. using Event instead of sleep enables to interrupt the scheduler
    _stop = None  # stop signal - if set, the AsyncScheduler shuts down
    _repeat_event_mapping = None  # map the first event instance of an repeating event with the current event instance
    _lock = None  # locks the repeat methods - ensures that a new entry is setup correctly before it is triggered

    def __init__(self):
        self._repeat_event_mapping = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._delayfunc = threading.Event()
        self.scheduler = sched.scheduler(timefunc, self._delayfunc.wait)

    def _run(self):
        """thread method - runs the scheduler until stop signal is set"""
        while not (self._stop.is_set() and self.scheduler.empty()):
            # continue only iff we are not stopping and the event queue is empty. this allows to delay shutdown until
            # the last event has been triggered.
            delay = self.scheduler.run(blocking=False)
            if delay is not None:
                self._delayfunc.wait(delay)
            if self.scheduler.empty() and not self._stop.is_set():
                # scheduler.run() exits immediately if the event queue is empty.
                # wait until some method call changes the queue
                self._delayfunc.clear()
                self._delayfunc.wait()
            self._delayfunc.clear()

    def stop(self, wait=True):
        """
        Stops the scheduler and clears the event queue. If wait is true, enter and enterabs events are continued as
        usual. Repeating events are allowed to fire one last time.

        :param wait: if set to False, the queue is cleared. otherwise, the method does not return until the last event
        has been triggered.
        """
        self._stop.set()
        if not wait:
            self.clear_scheduler()
        else:
            self._delayfunc.set()
        self._thread.join()

    def enterabs(self, time, priority, action, args=(), kwargs={}):
        """
        Add an event to the scheduler. It will be executed at the provided time with 'action(*argument, **kwargs)'.
        In case of two events scheduled for the same time the priority is used for execution order. A lower number
        means a higher priority.

        :param time: call the action at this time stamp.
        :param priority: events scheduled for the same time are processed according to their priority.
        :param action: function that is called upon expirey
        :param args: tuple of arguments for this function
        :param kwargs: dict of arguments for this function
        :return: instance of the event
        """
        event = self.scheduler.enterabs(time, priority, action, argument=args, kwargs=kwargs)
        self._delayfunc.set()
        return event

    def enter(self, delay, priority, action, args=(), kwargs={}):
        """
        Add an event to the scheduler. It will be executed after the provided delay with 'func(*argument, **kwargs)'.
        In case of two events scheduled for the same time the priority is used for execution order. A lower number
        means a higher priority.

        :param delay: delay call of func for this amount of seconds. e.g. 12.34
        :param priority: events scheduled for the same time are processed according to their priority.
        :param action: function that is called upon expirey
        :param args: tuple of arguments for this function
        :param kwargs: dict of arguments for this function
        :return: instance of the event
        """
        event = self.scheduler.enter(delay, priority, action, argument=args, kwargs=kwargs)
        self._delayfunc.set()
        return event

    def _repeat_event_hash(self, event):
        """
        Creates a hash for the provided event. Sched.Event itself is not hashable. Furthermore, the kwargs for an
        repeating event contain the field 'event_hash' that must be ommited (event_hash is set _after_ the event hash
        has been calculated which changes the hash for this event and thus a new has has to be generated and attached
        to the event which ...).

        :param event: instance of an event as returned by enter, enterab, and repeat.
        :return: hash value for this event
        """
        hashes = [hash(event.time), hash(event.priority), hash(event.action)]
        for a in event.argument:
            try:
                hashes.append(hash(a))
            except TypeError:
                pass
        for k, v in event.kwargs.items():
            if k != "event_hash":
                # skip event_id - event_id is set _after_ the event hash has been calculated which would lead to a
                # new hash value that must be updated which leads again to a new hash value ...
                try:
                    hashes.append(hash(v))
                except TypeError:
                    pass
        return frozenset(hashes).__hash__()

    def repeatabs(self, time, every, priority, action, args=(), kwargs={}):
        """
        Add a repeating event to the scheduler. It will be executed each time the provided delay (every-n-seconds) has
        expired with 'func(*argument, **kwargs)'. The first event is triggered at the provided time. In case of two
        events scheduled for the same time the priority is used for execution order. A lower number means a higher
        priority.

        A repeating event will trigger one last time in case of a regular stop with wait=False (=default).

        Note: the returned event instance is the instance of the first iteration only. Thus, after the first iteration
        it will not be part of scheduler.queue no more. Instead a new event for this repeating event has been created.
        AsyncScheduler keeps track of the current instance and uses the first instance for identification of which
        event to cancel. This is done with the method _repeat_event_hash and the map _repeat_event_mapping.

        :param time: call the action at this time stamp.
        :param every: every-n-seconds call action. e.g. 12.34
        :param priority: events scheduled for the same time are processed according to their priority.
        :param action: function that is called upon expirey
        :param args: tuple of arguments for this function
        :param kwargs: dict of arguments for this function
        :return: instance of the event
        """
        with self._lock:
            next_abs = time
            params = {
                "now": next_abs,
                "every": every,
                "priority": priority,
                "action": action,
                "args": args,
                "kwargs": kwargs,
                "event_hash": ""
            }
            event = self.enterabs(next_abs, priority, self._repeat_handler, kwargs=params)
            hash_value = self._repeat_event_hash(event)
            event.kwargs["event_hash"] = hash_value
            self._repeat_event_mapping[hash_value] = event
        return event

    def repeat(self, every, priority, action, args=(), kwargs={}):
        """
        Add a repeating event to the scheduler. It will be executed each time the provided delay (every-n-seconds) has
        expired with 'func(*argument, **kwargs)'. In case of two events scheduled for the same time the priority is
        used for execution order. A lower number means a higher priority.

        See repeatabs for more information.

        :param every: every-n-seconds call action. e.g. 12.34
        :param priority: events scheduled for the same time are processed according to their priority.
        :param action: function that is called upon expirey
        :param args: tuple of arguments for this function
        :param kwargs: dict of arguments for this function
        :return: instance of the event
        """
        with self._lock:
            next_abs = timefunc() + every
            params = {
                "now": next_abs,
                "every": every,
                "priority": priority,
                "action": action,
                "args": args,
                "kwargs": kwargs,
                "event_hash": ""
            }
            event = self.enterabs(next_abs, priority, self._repeat_handler, kwargs=params)
            hash_value = self._repeat_event_hash(event)
            event.kwargs["event_hash"] = hash_value
            self._repeat_event_mapping[hash_value] = event
        return event

    def _repeat_handler(self, now, every, priority, action, args, kwargs, event_hash):
        """
        Executes the repeating event by calculating the next absolute time stamp, scheduling a new event for this time,
        and updating the mapping to the latest event instance.

        :param now: absolute timestamp of the last iteration
        :param every: every-n-seconds call action. e.g. 12.34
        :param priority: events scheduled for the same time are processed according to their priority.
        :param action: function that is called upon expirey
        :param args: tuple of arguments for this function
        :param kwargs: dict of arguments for this function
        :param event_hash: hash of the first created event instance for this repeating event
        """
        with self._lock:
            if not self._stop.is_set():
                next_abs = now + every
                params = (next_abs, every, priority, action, args, kwargs, event_hash)
                event = self.enterabs(next_abs, priority, self._repeat_handler, args=params)
                self._repeat_event_mapping[event_hash] = event
            action(*args, **kwargs)

    def cancel(self, event):
        """
        Removes the provided event from the scheduler. In case of an unknown event, a ValueError will be raised.

        :param event: event instance as returned from enter, enterabs, or repeat.
        """
        with self._lock:
            event_hash = self._repeat_event_hash(event)
            try:
                event = self._repeat_event_mapping[event_hash]
                del self._repeat_event_mapping[event_hash]
            except KeyError:
                pass

            self.scheduler.cancel(event)
            self._delayfunc.set()

    def clear_scheduler(self):
        """Cancels all scheduled events."""
        with self._lock:
            self._repeat_event_mapping.clear()
            for event in self.scheduler.queue:
                self.scheduler.cancel(event)
            self._delayfunc.set()

    def start(self):
        """Starts the scheduler."""
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=self.__class__.__name__)
        self._thread.start()



