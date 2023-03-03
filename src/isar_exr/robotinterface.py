import logging
from logging import Logger
from queue import Queue
from threading import Thread
from typing import List, Sequence, Union

from alitra import Frame, Orientation, Pose, Position
from robot_interface.models.exceptions import RobotException
from robot_interface.models.initialize import InitializeParams
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission import (
    InspectionStep,
    Step,
    StepStatus,
    TakeImage,
    TakeThermalImage,
    TakeThermalVideo,
    TakeVideo,
)
from robot_interface.models.mission.status import RobotStatus
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttTelemetryPublisher

from isar_exr.api.energy_robotics_api import EnergyRoboticsApi
from isar_exr.config.settings import settings
from isar_exr.models.exceptions import NoMissionRunningException


class ExrRobot(RobotInterface):
    def __init__(self):
        self.logger: Logger = logging.getLogger(ExrRobot.__name__)
        self.api: EnergyRoboticsApi = EnergyRoboticsApi()
        self.exr_robot_id: str = settings.ROBOT_EXR_ID

        self.position: Position = Position(x=1, y=1, z=1, frame=Frame("asset"))
        self.orientation: Orientation = Orientation(
            x=0, y=0, z=0, w=1, frame=Frame("asset")
        )
        self.pose: Pose = Pose(
            position=self.position, orientation=self.orientation, frame=Frame("asset")
        )

    def initiate_step(self, step: Step) -> None:
        raise NotImplementedError

    def step_status(self) -> StepStatus:
        try:
            return self.api.get_step_status(settings.ROBOT_EXR_ID)
        except NoMissionRunningException:
            # This is a temporary solution until we have step status by mission id
            return StepStatus.Successful
        except Exception as e:
            raise RobotException from e

    def stop(self) -> None:
        try:
            self.api.pause_current_mission(self.exr_robot_id)
        except RobotException:
            raise
        except Exception as e:
            raise RobotException from e

    def get_inspections(self, step: InspectionStep) -> Sequence[Inspection]:
        raise NotImplementedError

    def initialize(self, params: InitializeParams) -> None:
        raise NotImplementedError

    def get_telemetry_publishers(self, queue: Queue, robot_id: str) -> List[Thread]:
        publisher_threads: List[Thread] = []

        pose_publisher: MqttTelemetryPublisher = MqttTelemetryPublisher(
            mqtt_queue=queue,
            telemetry_method=self._get_pose_telemetry,
            topic=f"isar/{robot_id}/pose",
            interval=1,
            retain=False,
        )
        pose_thread: Thread = Thread(
            target=pose_publisher.run,
            args=[robot_id],
            name="ISAR Exr Pose Publisher",
            daemon=True,
        )
        publisher_threads.append(pose_thread)

        battery_publisher: MqttTelemetryPublisher = MqttTelemetryPublisher(
            mqtt_queue=queue,
            telemetry_method=self._get_battery_telemetry,
            topic=f"isar/{robot_id}/battery",
            interval=5,
            retain=False,
        )
        battery_thread: Thread = Thread(
            target=battery_publisher.run,
            args=[robot_id],
            name="ISAR Exr Battery Publisher",
            daemon=True,
        )
        publisher_threads.append(battery_thread)

        return publisher_threads

    def robot_status(self) -> RobotStatus:
        raise NotImplementedError

    def _get_pose_telemetry(self, robot_id: str) -> str:
        raise NotImplementedError

    def _get_battery_telemetry(self, robot_id: str) -> str:
        raise NotImplementedError

    def _create_image(self, step: Union[TakeImage, TakeThermalImage]):
        raise NotImplementedError

    def _create_video(self, step: Union[TakeVideo, TakeThermalVideo]):
        raise NotImplementedError
