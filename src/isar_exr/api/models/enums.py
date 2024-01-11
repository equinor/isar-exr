from enum import Enum


class AwakeStatus(str, Enum):
    Awake: str = "AWAKE"
    Asleep: str = "ASLEEP"
    WakingUp: str = "WAKING_UP"
    GoingToSleep: str = "GOING_TO_SLEEP"


class ChargingState(str, Enum):
    Discharging: str = "DISCHARGING"
    Charging: str = "CHARGING"
    Charged: str = "CHARGED"


class ChargerType(str, Enum):
    NotConnected: str = "NOT_CONNECTED"
    WiredCharger: str = "WIRED_CHARGER"
    WirelessCharger: str = "WIRELESS_CHARGER"
