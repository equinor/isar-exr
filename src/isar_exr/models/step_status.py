from enum import Enum

from robot_interface.models.mission.status import MissionStatus


class ExrMissionStatus(str, Enum):
    StartRequested: str = "START_REQUESTED"
    PauseRequested: str = "PAUSE_REQUESTED"
    ResumeRequested: str = "RESUME_REQUESTED"
    Rejected: str = "REJECTED"
    WakingUp: str = "WAKING_UP"
    Starting: str = "STARTING"
    InProgress: str = "IN_PROGRESS"
    Paused: str = "PAUSED"
    Completed: str = "COMPLETED"

    def to_mission_status(self) -> MissionStatus:
        return {
            ExrMissionStatus.StartRequested: MissionStatus.NotStarted,
            ExrMissionStatus.PauseRequested: MissionStatus.InProgress,
            # Current implementation paused is cancelled
            ExrMissionStatus.ResumeRequested: MissionStatus.Cancelled,
            ExrMissionStatus.Rejected: MissionStatus.Failed,
            ExrMissionStatus.WakingUp: MissionStatus.NotStarted,
            ExrMissionStatus.Starting: MissionStatus.NotStarted,
            ExrMissionStatus.InProgress: MissionStatus.InProgress,
            ExrMissionStatus.Paused: MissionStatus.Cancelled,
            ExrMissionStatus.Completed: MissionStatus.Successful,
        }[self]
