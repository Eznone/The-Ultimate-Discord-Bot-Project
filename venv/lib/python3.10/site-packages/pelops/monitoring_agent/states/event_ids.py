from enum import Enum


class event_ids(Enum):
    SIGINT = 1
    NEW_UUID = 2
    TIMEOUT = 3
    ONBOARDING_REQUEST = 4
    ONBOARDING_RESPONSE = 5
    REONBOARDING_REQUEST = 6
    TERMINATION = 7
    ACTIVATE = 8
    RESTART = 9
