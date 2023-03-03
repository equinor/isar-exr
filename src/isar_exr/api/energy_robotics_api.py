from typing import Any, Dict
from isar_exr.api.models.models import Point3DInput, Pose3DStampedInput, QuaternionInput

from robot_interface.models.exceptions import RobotException
from robot_interface.models.mission.status import StepStatus

from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.models.exceptions import NoMissionRunningException
from isar_exr.models.step_status import ExrMissionStatus


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
    
    def wake_up_robot(self, exr_robot_id: str) -> None:
        query_string: str = """
            mutation wakeUp($robot_id: String!)
            {
                executeAwakeCommand(targetState: AWAKE, robotID:$robot_id)
                {
                    id
                    startTimestamp
                    result
                    state
                }
            }
        """
        params: dict = {"robot_id": exr_robot_id}
        try:
            result: Dict[str, Any] = self.client.query(query_string, params)
        except Exception as e:
            raise RobotException(e)
        
