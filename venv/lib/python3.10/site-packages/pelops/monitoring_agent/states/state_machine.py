#from tantamount.machine import Machine
from pelops.monitoring_agent.states.machinelogger import MachineLogger
from tantamount.fsm2dot import GetDotNotation

from pelops.monitoring_agent.states.active import Active
from pelops.monitoring_agent.states.initialized import Initialized
from pelops.monitoring_agent.states.onboarding import Onboarding
from pelops.monitoring_agent.states.onboarded import Onboarded
from pelops.monitoring_agent.states.terminiating import Terminating
from pelops.monitoring_agent.states.uninitialized import Uninitialized
from pelops.monitoring_agent.states.event_ids import event_ids
from pelops.monitoring_agent.states.state_ids import state_ids

import pelops.logging.mylogger

import threading
import collections


def create(sigint, onboarding_timeout, restart_timeout, logger):
    logger.info("creating state machine - start")

    logger.info("creating state machine - creating states")
    history = collections.deque(maxlen=50)
    states = {
        state_ids.UNINITIALIZED: Uninitialized(state_ids.UNINITIALIZED, logger, history, sigint),
        state_ids.INITIALIZED: Initialized(state_ids.INITIALIZED, logger, history, sigint),
        state_ids.ONBOARDING: Onboarding(state_ids.ONBOARDING, logger, history, sigint),
        state_ids.ONBOARDED: Onboarded(state_ids.ONBOARDED, logger, history, sigint),
        state_ids.ACTIVE: Active(state_ids.ACTIVE, logger, history, sigint),
        state_ids.TERMINATING: Terminating(state_ids.TERMINATING, logger, history),
    }

    machine = MachineLogger(logger)

    logger.info("creating state machine - adding states")
    for state in states.values():
        machine.addstate(state)

    logger.info("creating state machine - set start states")
    machine.setstartstate(state_ids.UNINITIALIZED)

    logger.info("creating state machine - adding transitions")
    machine.addtransition(state_ids.UNINITIALIZED, event_ids.NEW_UUID, state_ids.INITIALIZED)
    machine.addtransition(state_ids.UNINITIALIZED, event_ids.SIGINT, state_ids.TERMINATING)
    machine.addtransition(state_ids.UNINITIALIZED, event_ids.REONBOARDING_REQUEST, state_ids.UNINITIALIZED)

    machine.addtransition(state_ids.INITIALIZED, event_ids.SIGINT, state_ids.TERMINATING)
    machine.addtransition(state_ids.INITIALIZED, event_ids.ONBOARDING_REQUEST, state_ids.ONBOARDING)
    machine.addtransition(state_ids.INITIALIZED, event_ids.REONBOARDING_REQUEST, state_ids.UNINITIALIZED)

    machine.addtransition(state_ids.ONBOARDING, event_ids.SIGINT, state_ids.TERMINATING)
    machine.addtransition(state_ids.ONBOARDING, event_ids.TIMEOUT, state_ids.INITIALIZED)
    machine.addtransition(state_ids.ONBOARDING, event_ids.ONBOARDING_RESPONSE, state_ids.ONBOARDED)
    machine.addtransition(state_ids.ONBOARDING, event_ids.REONBOARDING_REQUEST, state_ids.UNINITIALIZED)

    machine.addtransition(state_ids.ONBOARDED, event_ids.SIGINT, state_ids.TERMINATING)
    machine.addtransition(state_ids.ONBOARDED, event_ids.ACTIVATE, state_ids.ACTIVE)
    machine.addtransition(state_ids.ONBOARDED, event_ids.REONBOARDING_REQUEST, state_ids.UNINITIALIZED)

    machine.addtransition(state_ids.ACTIVE, event_ids.SIGINT, state_ids.TERMINATING)
    machine.addtransition(state_ids.ACTIVE, event_ids.REONBOARDING_REQUEST, state_ids.UNINITIALIZED)
    machine.addtransition(state_ids.ACTIVE, event_ids.TIMEOUT, state_ids.UNINITIALIZED)

    machine.addtransition(state_ids.TERMINATING, event_ids.RESTART, state_ids.UNINITIALIZED)

    logger.info("creating state machine - set timeout events")
    machine.addtimeoutevent(state_ids.ONBOARDING, event_ids.TIMEOUT, onboarding_timeout)
    machine.addtimeoutevent(state_ids.TERMINATING, event_ids.RESTART, restart_timeout)
    machine.addtimeoutevent(state_ids.ACTIVE, event_ids.TIMEOUT, onboarding_timeout)  # set to an arbitrary value > 0
    # otherwise in case of a problem during onboarding it might happend that the timeoutevent triggers with 0 seconds
    # which would lead to a runtime error

    logger.info("creating state machine - done")
    return machine, states, history


def dot2file(filename):
    class NoLogger:
        def info(self, message):
            pass

        def debug(self, message):
            pass

        def warning(self, message):
            pass

        def error(self, message):
            pass

    config = {"log-level": "CRITICAL", "log-file": "hippodamia-agent.log"}
    logger = pelops.logging.mylogger.create_logger(config, "dot2file")
    #logger = NoLogger()
    sigint = threading.Event()
    machine, states, history = create(sigint, 60, 120, logger)

    gdn = GetDotNotation(machine, getStateId=(lambda x:x.name), getStateName=(lambda x:x.name),
                         getTransitionName=(lambda x:x.name))
    new_dotnotation = gdn.getdotnotation()


    try:
        with open(filename, 'r') as f:
            old_dotnotation = f.read()
    except OSError:
        old_dotnotation = ""

    if new_dotnotation != old_dotnotation:
        print("updating {} to latest version.".format(filename))
        with open(filename, "w") as f:
            f.write(new_dotnotation)
