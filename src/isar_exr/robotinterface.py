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
    RobotInfeasibleStepException,
    RobotInitializeException,
    RobotMissionNotSupportedException,
    RobotMissionStatusException,
)
from robot_interface.models.initialize import InitializeParams
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus, StepStatus
from robot_interface.models.mission.step import (
    DriveToPose,
    InspectionStep,
    Localize,
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
    AddPointOfInterestInput,
    Point3DInput,
    PointOfInterestActionPhotoInput,
    PointOfInterestActionVideoInput,
    PointOfInterestByCustomerTag,
    PointOfInterestTypeEnum,
    Pose3DInput,
    Pose3DStampedInput,
    QuaternionInput,
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
            map_alignment.map_from, map_alignment.map_to, rot_axes="xyz"
        )

    def create_new_stage(self) -> str:
        current_stage_id = self.api.get_current_site_stage(settings.ROBOT_EXR_SITE_ID)
        if current_stage_id is not None:
            self.api.discard_stage(stage_id=current_stage_id)
        stage_id: str = self.api.create_stage(site_id=settings.ROBOT_EXR_SITE_ID)
        return stage_id

    def update_site_with_tasks(
        self, tasks: List[Task]
    ) -> List[str]:  # Returns a list of POI IDs
        new_stage_id: str = None
        poi_ids: List[str] = []
        is_possible_return_to_home_mission = False
        steps_n = 0
        try:
            for task in tasks:
                for step in task.steps:
                    steps_n += 1
                    if isinstance(step, Localize):
                        steps_n -= 1
                    if isinstance(step, DriveToPose):
                        if (
                            step.pose.position.x == 0.0
                            and step.pose.position.y == 0.0
                            and step.pose.position.z == 0.0
                            and step.pose.orientation.x == 0.0
                            and step.pose.orientation.y == 0.0
                            and step.pose.orientation.z == 0.0
                        ):
                            is_possible_return_to_home_mission = True
                        robot_pose: Pose = step.pose
                    if isinstance(step, InspectionStep):
                        customer_tag: str = task.tag_id + "|" + str(robot_pose)
                        existing_poi_id = (
                            self.api.get_point_of_interest_by_customer_tag(
                                customer_tag=customer_tag,
                                site_id=settings.ROBOT_EXR_SITE_ID,
                            )
                        )
                        if existing_poi_id == None:
                            new_stage_id = self.create_new_stage()
                            poi_id: str = self._create_and_add_poi(
                                task=task,
                                step=step,
                                robot_pose=robot_pose,  # This pose is set by the previously received DriveToStep
                                stage_id=new_stage_id,
                                customer_tag=customer_tag,
                            )
                            poi_ids.append(poi_id)
                        else:
                            poi_ids.append(existing_poi_id)

            if steps_n == 0 or (steps_n == 1 and is_possible_return_to_home_mission):
                time.sleep(
                    settings.API_SLEEP_TIME
                )  # We need to sleep to allow events to reach flotilla in the right order
                raise RobotMissionNotSupportedException(
                    "Robot does not support localisation or return to home mission"
                )

            if new_stage_id is not None:
                # We should only do the following if we changed the site
                snapshot_id: str = self.api.commit_site_to_snapshot(
                    stage_id=new_stage_id
                )

                self.api.set_snapshot_as_head(
                    snapshot_id=snapshot_id, site_id=settings.ROBOT_EXR_SITE_ID
                )
        except Exception as e:
            if new_stage_id is not None:
                self.api.discard_stage(
                    stage_id=new_stage_id
                )  # Discard stage if we did not manage to use it
            raise e

        if new_stage_id is not None:  # Here we wait for the site update to complete
            while not self.api.is_pipeline_completed(
                site_id=settings.ROBOT_EXR_SITE_ID
            ):
                time.sleep(settings.API_SLEEP_TIME)
        return poi_ids

    def create_mission_definition(
        self, mission_name: str, tasks: List[Task], poi_ids: List[str]
    ) -> str:  # Returns a mission definition ID
        # Note that the POI IDs need to be in the same order as inspection steps in the provided mission
        mission_definition_id: str = self.api.create_mission_definition(
            site_id=settings.ROBOT_EXR_SITE_ID,
            mission_name=mission_name,
            robot_id=settings.ROBOT_EXR_ID,
        )

        for task in tasks:
            for step in task.steps:
                if isinstance(step, DriveToPose):
                    self._add_waypoint_task_to_mission(
                        mission_definition_id=mission_definition_id, step=step
                    )
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
        return mission_definition_id

    def initiate_mission(self, mission: Mission) -> None:
        try:
            poi_ids: List[str] = self.update_site_with_tasks(mission.tasks)
        except RobotMissionNotSupportedException:
            return

        mission_definition_id: str = self.create_mission_definition(
            mission.id, mission.tasks, poi_ids
        )

        self.api.start_mission_execution(
            mission_definition_id=mission_definition_id, robot_id=settings.ROBOT_EXR_ID
        )

    def mission_status(self) -> MissionStatus:
        try:
            return self.api.get_mission_status(settings.ROBOT_EXR_ID)
        except NoMissionRunningException:
            # This is a temporary solution until we have mission status by mission id
            return MissionStatus.Successful
        except Exception as e:
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
        # TODO: find endpoint to check if it is stuck, maybe MissionExecutionStatusEnum.PAUSED
        try:
            if not self.api.is_connected(settings.ROBOT_EXR_ID):
                return RobotStatus.Offline
        except Exception as e:
            message: str = f"Could not check if the robot is connected: {e}"
            self.logger.error(message)
            raise RobotCommunicationException(
                error_description=message,
            )

        try:
            mission_status: MissionStatus = self.api.get_mission_status(
                settings.ROBOT_EXR_ID
            )
            if (
                mission_status == MissionStatus.Paused
                or mission_status == MissionStatus.NotStarted
                or mission_status == MissionStatus.InProgress
            ):
                return RobotStatus.Busy
        except NoMissionRunningException as e:
            logging.info(f"There are no running missions: {e}")
            return RobotStatus.Available
        except Exception as e:
            logging.warning(f"Failed to get mission status from robot: {e}")
            return RobotStatus.Offline

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
        self, task: Task, step: Step, robot_pose: Pose, stage_id: str, customer_tag: str
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

        transformed_robot_pose = self.transform.transform_position(
            positions=robot_pose.position,
            from_=robot_pose.position.frame,
            to_=Frame("robot"),
        )

        photo_input_pose: Pose3DInput = Pose3DInput(
            position=Point3DInput(
                x=transformed_robot_pose.x,
                y=transformed_robot_pose.y,
                z=transformed_robot_pose.z,
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
            "customerTag": customer_tag,
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
            timestamp=int(round(datetime.datetime.now().timestamp())),
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
