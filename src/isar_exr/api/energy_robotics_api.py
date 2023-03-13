from datetime import datetime
from time import sleep
from typing import Any, Dict
from isar_exr.api.models.models import Point3DInput, Pose3DStampedInput, QuaternionInput

from robot_interface.models.exceptions import RobotException
from robot_interface.models.mission.status import StepStatus

from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.models.exceptions import NoMissionRunningException
from isar_exr.models.step_status import ExrMissionStatus
from isar_exr.api.models.enums import AwakeStatus
from isar_exr.api.models.models import AddPointOfInterestInput

from isar_exr.config.settings import settings
from isar_exr.api.models.models import (
    Point3DInput,
    QuaternionInput,
    Pose3DInput,
    PointOfInterestTypeEnum,
    PointOfInterestActionPhotoInput,
)


class EnergyRoboticsApi:
    def __init__(self):
        self.client = GraphqlClient()

    def get_step_status(self, exr_robot_id: str) -> StepStatus:
        query_string: str = """
            query currentMissionExecution($robot_id: String!) {
                currentMissionExecution(robotID: $robot_id) {
                    status
                    }
                }
        """
        params: dict = {"robot_id": exr_robot_id}
        if not self.is_mission_running(exr_robot_id):
            raise NoMissionRunningException(
                f"Cannot get EXR mission status - No EXR mission is running for robot with id {exr_robot_id}"
            )

        response_dict: dict[str, Any] = self.client.query(query_string, params)
        step_status = ExrMissionStatus(
            response_dict["currentMissionExecution"]["status"]
        )
        return step_status.to_step_status()

    def is_mission_running(self, exr_robot_id: str):
        query_string: str = """
            query isMissionRunning($robot_id: String!) {
                isMissionRunning(robotID: $robot_id)
                }
        """
        params: dict = {"robot_id": exr_robot_id}
        response_dict: dict[str, Any] = self.client.query(query_string, params)
        is_running: bool = response_dict["isMissionRunning"]
        return is_running

    def pause_current_mission(self, exr_robot_id: str) -> None:
        query_string: str = """
            mutation pauseMission($robot_id: String!)
            {
                pauseMissionExecution(robotID:$robot_id)
                {
                    id, status, failures
                }
            }
        """
        params: dict = {"robot_id": exr_robot_id}
        try:
            result: Dict[str, Any] = self.client.query(query_string, params)
        except Exception as e:
            raise RobotException(e)

        status: ExrMissionStatus = ExrMissionStatus(result["status"])
        success: bool = status in [
            ExrMissionStatus.Paused,
            ExrMissionStatus.PauseRequested,
        ]
        if not success:
            raise RobotException(f"Invalid status after pausing mission: '{status}'")

    def create_point_of_interest(
        self, point_of_interest_input: AddPointOfInterestInput
    ) -> str:
        mutation_string: str = """
            mutation addPointOfInterest(
                $name: String!, 
                $site: String!, 
                $frame: String!, 
                $type: PointOfInterestTypeEnum!,
                $position_x: Float!, 
                $position_y: Float!, 
                $position_z: Float!,
                $orientation_w: Float!,
                $orientation_x: Float!, 
                $orientation_y: Float!, 
                $orientation_z: Float!,
                $action_sensor: String!,
                $action_position_x: Float!, 
                $action_position_y: Float!, 
                $action_position_z: Float!,
                $action_orientation_w: Float!,
                $action_orientation_x: Float!, 
                $action_orientation_y: Float!, 
                $action_orientation_z: Float!,
                
            ) {
                addPointOfInterest(input: {
                    name: $name, 
                    site: $site,
                    frame: $frame,
                    type: $type,
                    pose: {
                        position: {
                            x: $position_x
                            y: $position_y
                            z: $position_z
                        }
                        orientation: {
                            w: $orientation_w
                            x: $orientation_x
                            y: $orientation_y
                            z: $orientation_z
                    }   }  
                    photoAction: {
                        robotPose :{
                            position: {
                                x: $action_position_x
                                y: $action_position_y
                                z: $action_position_z
                            }
                            orientation: {
                                w: $action_orientation_w
                                x: $action_orientation_x
                                y: $action_orientation_y
                                z: $action_orientation_z
                        }   }
                        sensor: $action_sensor
                    }
                }) {
                    id
                }
            }
        """
        params: dict = {
            "name": point_of_interest_input.name,
            "site": point_of_interest_input.site,
            "frame": point_of_interest_input.frame,
            "type": point_of_interest_input.type,
            "position_x": point_of_interest_input.pose.position.x,
            "position_y": point_of_interest_input.pose.position.y,
            "position_z": point_of_interest_input.pose.position.z,
            "orientation_w": point_of_interest_input.pose.orientation.w,
            "orientation_x": point_of_interest_input.pose.orientation.x,
            "orientation_y": point_of_interest_input.pose.orientation.y,
            "orientation_z": point_of_interest_input.pose.orientation.z,
            "action_position_x": point_of_interest_input.photoAction.robotPose.position.x,
            "action_position_y": point_of_interest_input.photoAction.robotPose.position.y,
            "action_position_z": point_of_interest_input.photoAction.robotPose.position.z,
            "action_orientation_w": point_of_interest_input.photoAction.robotPose.orientation.w,
            "action_orientation_x": point_of_interest_input.photoAction.robotPose.orientation.x,
            "action_orientation_y": point_of_interest_input.photoAction.robotPose.orientation.y,
            "action_orientation_z": point_of_interest_input.photoAction.robotPose.orientation.z,
            "action_sensor": point_of_interest_input.photoAction.sensor,
        }

        try:
            response_dict: dict[str, Any] = self.client.query(mutation_string, params)
        except Exception as e:
            raise RobotException(e)

        return response_dict["addPointOfInterest"]["id"]

    def create_dock_robot_task_definition(
        self, site_id: str, task_name: str, docking_station_id: str
    ) -> str:
        mutation_string: str = """
            mutation createDockRobotTaskDefinition($site_id: String!, $task_name: String!, $docking_station_id: String!) {
                createDockRobotTaskDefinition(input: {
                    siteId: $site_id, 
                    name: $task_name, 
                    dockingStationId: $docking_station_id
                }) {
                    id
                    isDynamicMission
                    waypoint {
                        waypointId
                    }
                }
            }
        """
        params: dict = {
            "site_id": site_id,
            "task_name": task_name,
            "docking_station_id": docking_station_id,
        }

        try:
            response_dict: dict[str, Any] = self.client.query(mutation_string, params)
        except Exception as e:
            raise RobotException(e)

        return response_dict["createDockRobotTaskDefinition"]["id"]

    def create_point_of_interest_inspection_task_definition(
        self, site_id: str, task_name: str, point_of_interest_id: str
    ) -> str:
        mutation_string: str = """
            mutation createPoiInspectionTaskDefinition($site_id: String!, $task_name: String!, $point_of_interest_id: String!) {
                createPoiInspectionTaskDefinition(input: {
                    siteId: $site_id, 
                    name: $task_name, 
                    poiId: $point_of_interest_id
                }) {
                    id
                }
            }
        """
        params: dict = {
            "site_id": site_id,
            "task_name": task_name,
            "point_of_interest_id": point_of_interest_id,
        }

        try:
            response_dict: dict[str, Any] = self.client.query(mutation_string, params)
        except Exception as e:
            raise RobotException(e)

        return response_dict["createPoiInspectionTaskDefinition"]["id"]

    def create_waypoint_task_definition(
        self, site_id: str, task_name: str, pose_3D_stamped_input: Pose3DStampedInput
    ) -> str:
        mutation_string: str = """
            mutation createWaypointTaskDefinition(
                $site_id: String!, 
                $task_name: String!, 
                $timestamp: Timestamp!, 
                $position_x: Float!, 
                $position_y: Float!, 
                $position_z: Float!,
                $orientation_w: Float!,
                $orientation_x: Float!, 
                $orientation_y: Float!, 
                $orientation_z: Float!,
            ) {
                createWaypointTaskDefinition(input: {
                    siteId: $site_id, 
                    name: $task_name,
                    waypoint: {
                        timestamp: $timestamp
                        position: {
                            x: $position_x
                            y: $position_y
                            z: $position_z
                        }
                        orientation: {
                            w: $orientation_w
                            x: $orientation_x
                            y: $orientation_y
                            z: $orientation_z
                        }
                    }
                }) {
                    id
                }
            }
        """
        params: dict = {
            "site_id": site_id,
            "task_name": task_name,
            "timestamp": pose_3D_stamped_input.timestamp,
            "position_x": pose_3D_stamped_input.position.x,
            "position_y": pose_3D_stamped_input.position.y,
            "position_z": pose_3D_stamped_input.position.z,
            "orientation_w": pose_3D_stamped_input.orientation.w,
            "orientation_x": pose_3D_stamped_input.orientation.x,
            "orientation_y": pose_3D_stamped_input.orientation.y,
            "orientation_z": pose_3D_stamped_input.orientation.z,
        }

        try:
            response_dict: dict[str, Any] = self.client.query(mutation_string, params)
        except Exception as e:
            raise RobotException(e)

        return response_dict["createWaypointTaskDefinition"]["id"]

    def wake_up_robot(
        self, exr_robot_id: str, timeout: int = settings.MAX_TIME_FOR_WAKEUP
    ) -> None:
        query_string: str = """
            mutation wakeUp($robot_id: String!)
            {
                executeAwakeCommand(targetState: AWAKE, robotID:$robot_id)
                {
                    id
                }
            }
        """
        params: dict = {"robot_id": exr_robot_id}
        try:
            result: Dict[str, Any] = self.client.query(query_string, params)
        except Exception as e:
            raise RobotException(e)

        startTime = datetime.today()
        while not self.is_robot_awake(exr_robot_id):
            time_passed_since_function_call = (
                datetime.today() - startTime
            ).total_seconds()
            if time_passed_since_function_call > timeout:
                raise RobotException(
                    f"Not able to wake up robot after '{timeout}' seconds."
                )
            sleep(1)

    def is_robot_awake(self, exr_robot_id: str) -> bool:
        query_string: str = """
            query checkIfAwake($robot_id: String!)
            {
                currentRobotStatus(robotID:$robot_id)
                {
                    awakeStatus
                }
            }
        """
        params: dict = {"robot_id": exr_robot_id}
        try:
            result: Dict[str, Any] = self.client.query(query_string, params)
        except Exception as e:
            raise RobotException(e)

        status: AwakeStatus = AwakeStatus(result["awakeStatus"])
        success: bool = status in [AwakeStatus.Awake]
        return success

    def create_mission_definition(
        self, site_id: str, mission_name: str, robot_id: str
    ) -> str:
        mutation_string: str = """
            mutation createMissionDefinition(
                $site_id:String!, 
                $mission_name:String!,
                $robot_id:String) {
                createMissionDefinition(
                input: { 
                    siteId: $site_id, 
                    name: $mission_name,  
                    requiredRobotConfig:{robotId : $robot_id }}
                ) {
                id
            }}
        """
        params: dict = {
            "site_id": site_id,
            "mission_name": mission_name,
            "robot_id": robot_id,
        }

        try:
            response_dict: dict[str, Any] = self.client.query(mutation_string, params)
        except Exception as e:
            raise RobotException from e

        mission_definition_id = response_dict["createMissionDefinition"]["id"]
        return mission_definition_id

    def start_mission_execution(self, mission_definition_id: str, robot_id: str) -> str:
        mutation_string: str = """
            mutation startMissionExecution($robot_id:ID!, $mission_definition_id:String!) {
                startMissionExecution(
                    input: { robotID: $robot_id, missionDefinitionID: $mission_definition_id }
                ) {
                    id
                }
            }
        """
        params: dict = {
            "robot_id": robot_id,
            "mission_definition_id": mission_definition_id,
        }

        try:
            response_dict: dict[str, Any] = self.client.query(mutation_string, params)
        except Exception as e:
            raise RobotException from e
        mission_execution_id = response_dict["startMissionExecution"]["id"]
        return mission_execution_id

    def create_stage(self, site_id: str) -> str:
        mutation_string: str = """
            mutation openSiteStage($site_id:String!) {
                openSiteStage(
                     siteId: $site_id, 
                ) {
                    id
                }
            }
        """
        params: dict = {
            "site_id": site_id,
        }

        try:
            response_dict: dict[str, Any] = self.client.query(mutation_string, params)
        except Exception as e:
            raise RobotException from e
        mission_execution_id = response_dict["openSiteStage"]["id"]
        return mission_execution_id

    def add_point_of_intrest_to_stage(self, POI_id: str, stage_id: str) -> str:
        mutation_string: str = """
            mutation addPointOfInterestToStage($POI_id:String!,$stage_id:String!) {
                addPointOfInterestToStage(
                     pointOfInterestId: $POI_id, 
                     siteStageId: $stage_id,
                ) {
                    id
                }
            }
        """
        params: dict = {
            "POI_id": POI_id,
            "stage_id": stage_id,
        }

        try:
            response_dict: dict[str, Any] = self.client.query(mutation_string, params)
        except Exception as e:
            raise RobotException from e
        mission_execution_id = response_dict["addPointOfInterestToStage"]["id"]
        return mission_execution_id

    def commit_site_to_snapshot(self, stage_id: str) -> str:
        mutation_string: str = """
            mutation commitSiteChanges($stage_id:String!) {
                commitSiteChanges(
                     siteStageId: $stage_id,
                ) {
                    id
                }
            }
        """
        params: dict = {
            "stage_id": stage_id,
        }

        try:
            response_dict: dict[str, Any] = self.client.query(mutation_string, params)
        except Exception as e:
            raise RobotException from e
        mission_execution_id = response_dict["commitSiteChanges"]["id"]
        return mission_execution_id

    def set_snapshot_as_head(self, snapshot_id: str, site_id: str) -> str:
        mutation_string: str = """
            mutation selectCurrentSiteSnapshotHead($snapshot_id:String!,$site_id:String!) {
                selectCurrentSiteSnapshotHead(
                     siteSnapshotId: $snapshot_id,
                     siteId: $site_id,
                ) {
                    id
                }
            }
        """
        params: dict = {
            "site_id": site_id,
            "snapshot_id": snapshot_id,
        }

        try:
            response_dict: dict[str, Any] = self.client.query(mutation_string, params)
        except Exception as e:
            raise RobotException from e
        mission_execution_id = response_dict["selectCurrentSiteSnapshotHead"]["id"]
        return mission_execution_id
