import datetime
import json
import logging
import os
import time
from logging import Logger
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import List, Sequence, Union

from alitra import (
    Frame,
    MapAlignment,
    Orientation,
    Pose,
    Position,
    Transform,
    align_maps,
)
from robot_interface.models.exceptions.robot_exceptions import (
    RobotCommunicationException,
    RobotInitializeException,
    RobotMissionStatusException,
)
from robot_interface.models.initialize import InitializeParams
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus, StepStatus
from robot_interface.models.mission.step import (
    DriveToPose,
    InspectionStep,
    Step,
    TakeImage,
    TakeThermalImage,
    TakeThermalVideo,
    TakeVideo,
)
from robot_interface.models.mission.task import Task
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttTelemetryPublisher
from robot_interface.telemetry.payloads import (
    TelemetryBatteryPayload,
    TelemetryPosePayload,
)
from robot_interface.utilities.json_service import EnhancedJSONEncoder

from isar_exr.api.energy_robotics_api import EnergyRoboticsApi
from isar_exr.api.models.models import (
    Point3DInput,
    PointOfInterestProducerInput,
    PointOfInterestProducerTypeEnum,
    PointOfInterestTypeEnum,
    Pose3DStampedInput,
    QuaternionInput,
    RobotTypeEnum,
    UpsertPointOfInterestInput,
)
from isar_exr.config.settings import settings
from isar_exr.models.exceptions import NoMissionRunningException


class Robot(RobotInterface):
    def __init__(self) -> None:
        self.logger: Logger = logging.getLogger(Robot.__name__)
        self.api: EnergyRoboticsApi = EnergyRoboticsApi()
        self.exr_robot_id: str = settings.ROBOT_EXR_ID

        self.position: Position = Position(x=1, y=1, z=1, frame=Frame("asset"))
        self.orientation: Orientation = Orientation(
            x=0, y=0, z=0, w=1, frame=Frame("asset")
        )
        self.pose: Pose = Pose(
            position=self.position, orientation=self.orientation, frame=Frame("asset")
        )

        map_alignment: MapAlignment = MapAlignment.from_config(
            Path(
                os.path.dirname(os.path.realpath(__file__)),
                f"config/maps/{settings.MAP}.json",
            )
        )
        self.transform: Transform = align_maps(
            map_alignment.map_from, map_alignment.map_to, rot_axes="z"
        )

    def initiate_mission(self, mission: Mission) -> None:
        curent_stage_id = self.api.get_current_site_stage(settings.ROBOT_EXR_SITE_ID)
        if curent_stage_id is not None:
            self.api.discard_stage(stage_id=curent_stage_id)
        stage_id: str = self.api.create_stage(site_id=settings.ROBOT_EXR_SITE_ID)
        poi_ids: List[str] = []
        for task in mission.tasks:
            for step in task.steps:
                if isinstance(step, InspectionStep):
                    poi_id: str = self._upsert_and_add_poi(
                        task=task, step=step, stage_id=stage_id
                    )
                    poi_ids.append(poi_id)

        snapshot_id: str = self.api.commit_site_to_snapshot(stage_id=stage_id)
        _ = self.api.set_snapshot_as_head(
            snapshot_id=snapshot_id, site_id=settings.ROBOT_EXR_SITE_ID
        )

        mission_definition_id: str = self.api.create_mission_definition(
            site_id=settings.ROBOT_EXR_SITE_ID,
            mission_name=mission.id,
            robot_id=settings.ROBOT_EXR_ID,
        )

        for task in mission.tasks:
            for step in task.steps:
                if isinstance(step, DriveToPose):
                    _ = self._add_waypoint_task_to_mission(
                        mission_definition_id=mission_definition_id, step=step
                    )
                if isinstance(step, InspectionStep):
                    poi_task_id: str = (
                        self.api.create_point_of_interest_inspection_task_definition(
                            site_id=settings.ROBOT_EXR_SITE_ID,
                            task_name=step.id,
                            point_of_interest_id=poi_ids.pop(0),
                        )
                    )
                    _ = self.api.add_task_to_mission_definition(
                        task_id=poi_task_id,
                        mission_definition_id=mission_definition_id,
                    )

        dock_task_id: str = self.api.create_dock_robot_task_definition(
            site_id=settings.ROBOT_EXR_SITE_ID,
            task_name="dock",
            docking_station_id=settings.DOCKING_STATION_ID,
        )
        _ = self.api.add_task_to_mission_definition(
            task_id=dock_task_id,
            mission_definition_id=mission_definition_id,
        )

        _ = self.api.start_mission_execution(
            mission_definition_id=mission_definition_id, robot_id=settings.ROBOT_EXR_ID
        )

    def mission_status(self) -> MissionStatus:
        try:
            return self.api.get_mission_status(settings.ROBOT_EXR_ID)
        except NoMissionRunningException:
            # This is a temporary solution until we have mission status by mission id
            return MissionStatus.Successful
        except Exception:
            message: str = "Could not get status of running mission"
            self.logger.error(message)
            raise RobotMissionStatusException(
                error_description=message,
            )

    def initiate_step(self, step: Step) -> None:
        self.logger.error("An invalid interface function was called")
        raise NotImplementedError

    def step_status(self) -> StepStatus:
        self.logger.error("An invalid interface function was called")
        raise NotImplementedError

    def stop(self) -> None:
        try:
            self.api.pause_current_mission(self.exr_robot_id)
        except Exception:
            message: str = "Could not stop the running mission"
            self.logger.error(message)
            raise RobotCommunicationException(
                error_description=message,
            )

    def get_inspections(self, step: InspectionStep) -> Sequence[Inspection]:
        raise NotImplementedError

    def initialize(self, params: InitializeParams) -> None:
        try:
            self.api.wake_up_robot(self.exr_robot_id)
        except Exception:
            message: str = "Could not initialize robot"
            self.logger.error(message)
            raise RobotInitializeException(
                error_description=message,
            )

    def get_telemetry_publishers(
        self, queue: Queue, isar_id: str, robot_name: str
    ) -> List[Thread]:
        publisher_threads: List[Thread] = []

        pose_publisher: MqttTelemetryPublisher = MqttTelemetryPublisher(
            mqtt_queue=queue,
            telemetry_method=self._get_pose_telemetry,
            topic=f"isar/{isar_id}/pose",
            interval=1,
            retain=False,
        )
        pose_thread: Thread = Thread(
            target=pose_publisher.run,
            args=[isar_id, robot_name],
            name="ISAR Exr Pose Publisher",
            daemon=True,
        )
        publisher_threads.append(pose_thread)

        battery_publisher: MqttTelemetryPublisher = MqttTelemetryPublisher(
            mqtt_queue=queue,
            telemetry_method=self._get_battery_telemetry,
            topic=f"isar/{isar_id}/battery",
            interval=5,
            retain=False,
        )
        battery_thread: Thread = Thread(
            target=battery_publisher.run,
            args=[isar_id, robot_name],
            name="ISAR Exr Battery Publisher",
            daemon=True,
        )
        publisher_threads.append(battery_thread)

        return publisher_threads

    def robot_status(self) -> RobotStatus:
        return RobotStatus.Available

    def _get_pose_telemetry(self, isar_id: str, robot_name: str) -> str:
        pose_payload: TelemetryPosePayload = TelemetryPosePayload(
            pose=self.pose,
            isar_id=isar_id,
            robot_name=robot_name,
            timestamp=datetime.datetime.now(),
        )
        return json.dumps(pose_payload, cls=EnhancedJSONEncoder)

    @staticmethod
    def _get_battery_telemetry(isar_id: str, robot_name: str) -> str:
        battery_payload: TelemetryBatteryPayload = TelemetryBatteryPayload(
            battery_level=55,
            isar_id=isar_id,
            robot_name=robot_name,
            timestamp=datetime.datetime.now(),
        )
        return json.dumps(battery_payload, cls=EnhancedJSONEncoder)

    def _create_image(self, step: Union[TakeImage, TakeThermalImage]):
        raise NotImplementedError

    def _create_video(self, step: Union[TakeVideo, TakeThermalVideo]):
        raise NotImplementedError

    def _upsert_and_add_poi(self, task: Task, step: Step, stage_id: str) -> str:
        target: Position = self.transform.transform_position(
            positions=step.target,
            from_=step.target.frame,
            to_=Frame("asset"),
        )
        pose: Pose3DStampedInput = Pose3DStampedInput(
            timestamp=time.time(),
            frameID="don't know",
            position=Point3DInput(x=target.x, y=target.y, z=target.z),
            orientation=QuaternionInput(
                x=0,
                y=0,
                z=0,
                w=1,
            ),
        )

        poi_producer: PointOfInterestProducerInput = PointOfInterestProducerInput(
            type=PointOfInterestProducerTypeEnum.MANUAL_IMPORT,
            robotNumber=1,
            robotType=RobotTypeEnum.EXR2,
        )
        poi_input: UpsertPointOfInterestInput = UpsertPointOfInterestInput(
            key=task.tag_id if task.tag_id else "default_poi",
            name="insert_name_here",
            type=PointOfInterestTypeEnum.GENERIC,
            siteId=settings.ROBOT_EXR_SITE_ID,
            pose=pose,
            producer=poi_producer,
            inspectionParameters={},
        )

        poi_id: str = self.api.upsert_point_of_interest(
            point_of_interest_input=poi_input
        )

        _ = self.api.add_point_of_interest_to_stage(POI_id=poi_id, stage_id=stage_id)

        return poi_id

    def _add_waypoint_task_to_mission(
        self, mission_definition_id: str, step: Step
    ) -> str:
        pose: Pose = self.transform.transform_pose(
            pose=step.pose, from_=step.pose.frame, to_=Frame("asset")
        )
        pose_3d_stamped: Pose3DStampedInput = Pose3DStampedInput(
            timestamp=time.time(),
            frameID="don't know",
            position=Point3DInput(
                x=pose.position.x, y=pose.position.y, z=pose.position.z
            ),
            orientation=QuaternionInput(
                x=pose.orientation.x,
                y=pose.orientation.y,
                z=pose.orientation.z,
                w=pose.orientation.w,
            ),
        )
        waypoint_id: str = self.api.create_waypoint_task_definition(
            site_id=settings.ROBOT_EXR_SITE_ID,
            task_name=step.id,
            pose_3D_stamped_input=pose_3d_stamped,
        )
        add_task_id: str = self.api.add_task_to_mission_definition(
            task_id=waypoint_id,
            mission_definition_id=mission_definition_id,
        )

        return add_task_id
