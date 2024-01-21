from threading import Lock, Thread
from queue import Queue
from collections import namedtuple
from asyncscheduler import AsyncScheduler


class Machine:
    _start_state = None
    _state = None
    _states = None
    _transitions = None
    _timeoutevent = None
    _timeoutevents = None
    _schedulerthread = None
    _startdone = None
    _scheduler = None
    _lock_operate = None

    _async_thread = None
    _async_queue = None
    _stopping = None

    _ignore_undefined_events = None
    _transition_hook = None

    def __init__(self, ignore_undefined_events=False):
        self.ignore_undefined_events = ignore_undefined_events

        self._states = {}
        self._transitions = {}
        self._timeoutevents = {}
        self._startdone = False
        self._stopping = False

        self._scheduler = AsyncScheduler()

        self._lock_operate = Lock()

        self._async_queue = Queue(maxsize=0)
        self._async_thread = Thread(target=self._async_worker, name=self.__class__.__name__+"._async_thread")

    def setstartstate(self, stateid):
        self._state = self._states[stateid]
        self._start_state = self._state

    def addstate(self, state):
        if state.id is None or state.id == "":
            raise ValueError("Machine.addstate - state id must be set")
        if state.groupid is None or state.groupid == "":
            raise ValueError("Machine.addstate - group id must be set")
        if state.id in self._states:
            raise KeyError("Machine.addstate - state id '{}' already added".format(state.id))
        self._states[state.id] = state

    def addtransition(self, startstateid, eventid, targetstateid, actionFunc=None, actionArgs=None):
        if startstateid not in self._states:
            raise KeyError("Machine.addtransition - unknown start state id: '{}'".format(startstateid))
        if targetstateid not in self._states:
            raise KeyError("Machine.addtransition - unknown target state id: '{}'".format(targetstateid))
        if eventid is None or eventid == "":
            raise ValueError("Machine.addtransition - transition id must be set.")
        if actionFunc is None and actionArgs is not None:
            raise ValueError("Machine.addtransition - actionArgs must only be set if actionFunc is set as well")
        if actionFunc is not None and not callable(actionFunc):
            raise ValueError("Machine.addtransition - actionFunc must be callable")

        if actionArgs is None:
            actionArgs = ()

        Entry = namedtuple('Entry', ['targetstateid', 'actionFunc', 'actionArgs'])
        transition = Entry(targetstateid=targetstateid, actionFunc=actionFunc, actionArgs=actionArgs)

        if startstateid not in self._transitions:
            self._transitions[startstateid] = {}
        if eventid in self._transitions[startstateid]:
            raise KeyError("Machine.addtransition - transition id '{}' with start state '{}' already added.".
                           format(eventid, startstateid))

        self._transitions[startstateid][eventid] = transition

    def addtimeoutevent(self, stateid, eventid, seconds):
        if seconds < 0:
            raise ValueError("Machine.addtimeoutevent - seconds must be >= 0")
        if stateid not in self._states:
            raise KeyError("Machine.addtimeoutevent - unknown state id '{}'".format(stateid))
        if eventid not in self._transitions[stateid]:
            raise KeyError("Machine.addtimeoutevent - unknown transition id '{}' for state id '{}'".
                           format(eventid, stateid))
        if stateid in self._timeoutevents:
            raise KeyError("Machine.addtimeoutevent - already added a timeoutevent with event id '{}' to state id '{}'".
                           format(eventid, stateid))
        try:
            if self._transitions[stateid][eventid]:
                self._timeoutevents[stateid] = (eventid, seconds)
        except KeyError as e:
            raise KeyError("Machine.addtimeoutevent - KeyError. stateid=" + str(stateid) + ", eventid=" + str(eventid)
                           + "; KeyError: " + str(e))

    def updatetimeoutevent(self, stateid, eventid, seconds):
        if seconds < 0:
            raise ValueError("Machine.updatetimeoutevent - seconds must be >= 0")
        if stateid not in self._states:
            raise KeyError("Machine.updatetimeoutevent - unknown state id '{}'".format(stateid))
        if eventid not in self._transitions[stateid]:
            raise KeyError("Machine.updatetimeoutevent - unknown transition id '{}' for state id '{}'".format(eventid, stateid))

        try:
            if self._transitions[stateid][eventid]:
                e, s = self._timeoutevents[stateid]
                if e != eventid:
                    raise KeyError("Machine.updatetimeoutevent - expected eventid='"+str(e)+"', got '"+str(eventid)+"'")
                self._timeoutevents[stateid] = (eventid, seconds)
        except KeyError as e:
            raise KeyError("Machine.updatetimeoutevent - KeyError. stateid=" + str(stateid) + ", eventid=" + str(eventid)
                           + "; KeyError: " + str(e))

    def _gettransition(self, stateid, eventid):
        try:
            transition = self._transitions[stateid][eventid]
        except KeyError as e:
            raise KeyError("Machine._gettransition - transition KeyError. stateid=" +
                  str(stateid) + ", eventid=" + str(eventid))
        try:
            nextstate = self._states[transition.targetstateid]
        except KeyError as e:
            raise KeyError("Machine._gettransition - nextstate KeyError. transition=" +
                  str(transition.targetstateid))

        return nextstate, transition.actionFunc, transition.actionArgs

    def _starttimeoutevent(self):
        if self._state.timerevent is not None:
            raise Exception("machine._starttimeoutevent has been called while "
                            "another timeoutevent has been still active.")

        try:
            (eventid, seconds) = self._timeoutevents[self._state.id]
        except KeyError:
            return  # not timeoutevent for this state

        self._state.timerevent = self._scheduler.\
            enter(seconds, 1, self.asyncoperate, args=(eventid, self._state.id, self._state.activation_counter,))

    def _stoptimeoutevent(self):
        if self._state.timerevent is not None:
            try:
                self._scheduler.cancel(self._state.timerevent)
            except ValueError:
                pass  # the event has fired und is thus not in the scheduler queue any more
            self._state.timerevent = None

    def _async_worker(self):
        while True:
            params = self._async_queue.get()
            if params is None or self._stopping:
                self._async_queue.task_done()
                break
            (eventid, source_stateid, source_activation_counter) = params
            self.operate(eventid, source_stateid, source_activation_counter)
            self._async_queue.task_done()
        if not self._stopping:
            raise ValueError("_async_worker - exited work loop altough _stopping is not set.")

    def restarttimeoutevent(self):
        self._stoptimeoutevent()
        self._starttimeoutevent()

    def get_active_state(self):
        return self._state

    def asyncoperate(self, eventid, source_stateid=None, source_activation_counter=None):
        self._async_queue.put((eventid, source_stateid, source_activation_counter,))

    def registertransitionhook(self, hook):
        """
        registers a function with three parameters (start_state_id, transition_id, target_state_id) that is called
        after previous state has executed on_exit and before the new state has called on_enter.

        only one hook can be set - calling this method a second time overwrites the previously registered hook.

        :param hook: function
        """
        self._transition_hook = hook

    def cleartransitionhook(self):
        """resets the transition hook (see registertransitionhook)"""
        self._transition_hook = None

    def operate(self, eventid, source_stateid=None, source_activation_counter=None):
        # three sources may call machine.operate():
        #    - external events
        #    - states that immediately trigger an event transition in on_entry
        #    - timeouts
        if not self._startdone:
            raise RuntimeError("machine.operate - start must be called before operate is called for the first time")

        with self._lock_operate:
            if source_stateid is not None and source_activation_counter is not None:
                if self._state.id != source_stateid or self._state.activation_counter != source_activation_counter:
                    # racing condition - the timer fired for an state that is no longer the current state.
                    # due to the asnychonous behavior it is not possible to guarantee that the timerevent is canceled
                    # in time on state change
                    return
            while eventid and not self._stopping:
                try:
                    nextState, actionFunc, actionArgs = self._gettransition(self._state.id, eventid)
                except KeyError as e:
                    if not self._ignore_undefined_events:
                        raise e
                    else:
                        break

                self._stoptimeoutevent()
                self._state.machine_on_exit()

                if actionFunc:
                    actionFunc(*actionArgs)
                if self._transition_hook:
                    self._transition_hook(self._state.id, eventid, nextState.id)

                self._state = nextState
                self._starttimeoutevent()
                eventid = self._state.machine_on_entry()

    def start(self):
        self._start(False)

    def asyncstart(self):
        self._start(True)

    def _start(self, async_operate):
        if self._start_state is None:
            raise RuntimeError("machine.start - start state not set. propably setstartstate() not called.")

        if not self._startdone:
            self._startdone = True
            self._async_thread.start()
            self._scheduler.start()
            with self._lock_operate:
                self._starttimeoutevent()
                event_id = self._state.machine_on_entry()
            if event_id:
                if async_operate:
                    self.asyncoperate(event_id)
                else:
                    self.operate(event_id)
        else:
            raise Exception("machine.start must only be called once.")

    def stop(self):
        self._stopping = True
        self._stoptimeoutevent()
        self._async_queue.put(None)
        self._async_thread.join()
        with self._lock_operate:
            self._scheduler.stop(wait=False)

