from enum import Enum


class AwakeStatus(str, Enum):
    Awake: str = "AWAKE"
    Asleep: str = "ASLEEP"
    WakingUp: str = "WAKING_UP"
    GoingToSleep: str = "GOING_TO_SLEEP"
