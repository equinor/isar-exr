from typing import Any, Dict

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
