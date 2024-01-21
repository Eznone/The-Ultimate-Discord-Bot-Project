from enum import Enum


class state_ids(Enum):
    UNINITIALIZED = 1
    INITIALIZED = 2
    ONBOARDING = 3
    ONBOARDED = 4
    ACTIVE = 5
    TERMINATING = 6
