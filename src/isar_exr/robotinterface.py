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
    RobotInfeasibleStepException,
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
    PointOfInterestActionPhotoInput,
    PointOfInterestActionVideoInput,
    PointOfInterestByCustomerTag,
    PointOfInterestTypeEnum,
    Pose3DInput,
    Pose3DStampedInput,
    QuaternionInput,
    RobotTypeEnum,
    AddPointOfInterestInput,
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
        updating_site = False
        poi_ids: List[str] = []
        for task in mission.tasks:
            for step in task.steps:
                if isinstance(step, DriveToPose):
                    robot_pose: Pose = step.pose
                if isinstance(step, InspectionStep):
                    existing_poi_id = self.api.get_point_of_interest_by_customer_tag(
                        customer_tag=task.tag_id, site_id=settings.ROBOT_EXR_SITE_ID
                    )
                    if existing_poi_id == None:
                        poi_id: str = self._create_and_add_poi(  # Here we should only create if it does not already exist
                            task=task,
                            step=step,
                            robot_pose=robot_pose,
                            stage_id=stage_id,
                        )
                        poi_ids.append(poi_id)
                        updating_site = True
                    else:
                        poi_ids.append(existing_poi_id)

        if updating_site:
            # We should only do the following if we changed the site
            snapshot_id: str = self.api.commit_site_to_snapshot(stage_id=stage_id)

            self.api.set_snapshot_as_head(
                snapshot_id=snapshot_id, site_id=settings.ROBOT_EXR_SITE_ID
            )

            while not self.api.is_pipeline_completed(
                site_id=settings.ROBOT_EXR_SITE_ID
            ):
                time.sleep(settings.API_SLEEP_TIME)

        mission_definition_id: str = self.api.create_mission_definition(
            site_id=settings.ROBOT_EXR_SITE_ID,
            mission_name=mission.id,
            robot_id=settings.ROBOT_EXR_ID,
        )

        for task in mission.tasks:
            for step in task.steps:
                # TODO: Support task with only DriveToStep
                if isinstance(step, InspectionStep):
                    self._add_point_of_interest_inspection_task_to_mission(
                        task_name=step.id,
                        point_of_interest_id=poi_ids.pop(0),
                        mission_definition_id=mission_definition_id,
                    )

        self._add_dock_robot_task_to_mission(
            task_name="dock",
            mission_definition_id=mission_definition_id,
        )

        self.api.start_mission_execution(
            mission_definition_id=mission_definition_id, robot_id=settings.ROBOT_EXR_ID
        )

        # TODO: maybe store current mission, so that we can interpret idle but with mission as not idle

        time.sleep(
            5
        )  # Waits for mission to start in order to avoid returning Successful to ISAR

    def mission_status(self) -> MissionStatus:
        try:
            return self.api.get_mission_status(settings.ROBOT_EXR_ID)
        except NoMissionRunningException:
            # This is a temporary solution until we have mission status by mission id
            # TODO: query currentRobotStatus to check if it is docking
            return MissionStatus.Successful
        except Exception:
            message: str = "Could not get status of running mission\n"
            self.logger.error(message)
            raise RobotMissionStatusException(
                error_description=message,
            )

    def initiate_step(self, step: Step) -> None:
        self.logger.error("An invalid interface function was called")
        raise NotImplementedError

    def step_status(self) -> StepStatus:
        # TODO: use currentMissionExecution(robotID)
        self.logger.error("An invalid interface function was called")
        raise NotImplementedError

    def stop(self) -> None:
        try:
            self.api.pause_current_mission(self.exr_robot_id)
        except Exception:
            message: str = "Could not stop the running mission\n"
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
            message: str = "Could not initialize robot\n"
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
        # TODO: check if robot is running a task, or check if it is awake?
        # TODO: use currentMissionExecution to see if Busy
        # TODO: find endpoint to check if it is stuck, maybe MissionExecutionStatusEnum.PAUSED
        return RobotStatus.Available

    def _get_pose_telemetry(self, isar_id: str, robot_name: str) -> str:
        pose_payload: TelemetryPosePayload = TelemetryPosePayload(
            pose=self.pose,
            isar_id=isar_id,
            robot_name=robot_name,
            timestamp=datetime.datetime.now(),
        )
        return json.dumps(pose_payload, cls=EnhancedJSONEncoder)

    def _get_battery_telemetry(self, isar_id: str, robot_name: str) -> str:
        battery_level = self.api.get_battery_level(settings.ROBOT_EXR_ID)
        battery_payload: TelemetryBatteryPayload = TelemetryBatteryPayload(
            battery_level=battery_level,
            isar_id=isar_id,
            robot_name=robot_name,
            timestamp=datetime.datetime.now(),
        )
        return json.dumps(battery_payload, cls=EnhancedJSONEncoder)

    def _create_image(self, step: Union[TakeImage, TakeThermalImage]):
        raise NotImplementedError

    def _create_video(self, step: Union[TakeVideo, TakeThermalVideo]):
        raise NotImplementedError

    def _create_and_add_poi(
        self, task: Task, step: Step, robot_pose: Pose, stage_id: str
    ) -> str:
        target: Position = self.transform.transform_position(
            positions=step.target,
            from_=step.target.frame,
            to_=Frame("robot"),
        )
        pose: Pose3DInput = Pose3DInput(
            position=Point3DInput(x=target.x, y=target.y, z=target.z),
            orientation=QuaternionInput(  # Ask Energy Robotics what is this used for
                x=0,
                y=0,
                z=0,
                w=1,
            ),
        )

        photo_input_pose: Pose3DInput = Pose3DInput(
            position=Point3DInput(
                x=robot_pose.position.x,
                y=robot_pose.position.y,
                z=robot_pose.position.z,
            ),
            orientation=QuaternionInput(
                w=robot_pose.orientation.w,
                x=robot_pose.orientation.x,
                y=robot_pose.orientation.y,
                z=robot_pose.orientation.z,
            ),
        )

        add_point_of_interest_input: dict[str, PointOfInterestActionPhotoInput] = {
            "name": task.tag_id if task.tag_id != None else step.id,
            "customerTag": task.tag_id,
            "frame": "map",
            "type": PointOfInterestTypeEnum.GENERIC,
            "site": settings.ROBOT_EXR_SITE_ID,
            "pose": pose,
        }

        if isinstance(step, TakeImage):
            photo_input: PointOfInterestActionPhotoInput = (
                PointOfInterestActionPhotoInput(
                    robotPose=photo_input_pose, sensor="inspection_cam_link"
                )
            )
            add_point_of_interest_input["photoAction"] = photo_input

        elif isinstance(step, TakeVideo):
            video_input: PointOfInterestActionVideoInput = (
                PointOfInterestActionVideoInput(
                    robotPose=photo_input_pose,
                    sensor="inspection_cam_link",
                    duration=step.duration,
                )
            )
            add_point_of_interest_input["videoAction"] = video_input

        else:
            raise RobotInfeasibleStepException(
                error_description=f"Step of type {type(step)} not supported"
            )

        poi_input: AddPointOfInterestInput = AddPointOfInterestInput(
            **add_point_of_interest_input
        )

        poi_id: str = self.api.create_point_of_interest(
            point_of_interest_input=poi_input
        )

        self.api.add_point_of_interest_to_stage(POI_id=poi_id, stage_id=stage_id)

        return poi_id

    def _add_waypoint_task_to_mission(
        self, mission_definition_id: str, step: Step
    ) -> str:
        pose: Pose = self.transform.transform_pose(
            pose=step.pose, from_=step.pose.frame, to_=Frame("robot")
        )
        pose_3d_stamped: Pose3DStampedInput = Pose3DStampedInput(
            timestamp=time.time(),
            frameID="map",
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

    def _add_point_of_interest_inspection_task_to_mission(
        self, task_name: str, point_of_interest_id: str, mission_definition_id: str
    ):
        poi_task_id: str = self.api.create_point_of_interest_inspection_task_definition(
            site_id=settings.ROBOT_EXR_SITE_ID,
            task_name=task_name,
            point_of_interest_id=point_of_interest_id,
        )
        self.api.add_task_to_mission_definition(
            task_id=poi_task_id,
            mission_definition_id=mission_definition_id,
        )

    def _add_dock_robot_task_to_mission(
        self, task_name: str, mission_definition_id: str
    ):
        dock_task_id: str = self.api.create_dock_robot_task_definition(
            site_id=settings.ROBOT_EXR_SITE_ID,
            task_name=task_name,
            docking_station_id=settings.DOCKING_STATION_ID,
        )
        self.api.add_task_to_mission_definition(
            task_id=dock_task_id,
            mission_definition_id=mission_definition_id,
        )
