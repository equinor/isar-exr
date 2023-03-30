from enum import Enum

from robot_interface.models.mission.status import StepStatus


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

    def to_step_status(self) -> StepStatus:
        return {
            ExrMissionStatus.StartRequested: StepStatus.NotStarted,
            ExrMissionStatus.PauseRequested: StepStatus.InProgress,
            # Current implementation paused is cancelled
            ExrMissionStatus.ResumeRequested: StepStatus.Cancelled,
            ExrMissionStatus.Rejected: StepStatus.Failed,
            ExrMissionStatus.WakingUp: StepStatus.NotStarted,
            ExrMissionStatus.Starting: StepStatus.NotStarted,
            ExrMissionStatus.InProgress: StepStatus.InProgress,
            ExrMissionStatus.Paused: StepStatus.Cancelled,
            ExrMissionStatus.Completed: StepStatus.Successful,
        }[self]
