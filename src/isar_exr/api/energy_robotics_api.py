from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.models.step_status import ExrMissionStatus
from robot_interface.models.mission.status import StepStatus
from typing import Any
from isar_exr.models.exceptions import NoMissionRunningException


class Api:
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
