from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.models.step_status import ExrMissionStatus
from robot_interface.models.mission.status import StepStatus
from typing import Any
from isar_exr.models.exceptions import NoMissionRunningException
from isar_exr.config.settings import settings


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

    def get_mission_report_ids_and_endtime_for_robot(
        self, exr_robot_id: str, number_of_latest_reports: str
    ) -> str:
        query_string: str = """
            query missionReports($robot_id: String!, $number_of_latest_reports: Float!) {
                missionReports(input: {robotId: $robot_id}
                filter: {first: $number_of_latest_reports}) {
                  page {    
                    edges {
                      node {
                        endTimestamp
                        id
                      }
                    }
                  }
                }
            }

        """
        params: dict = {
            "robot_id": exr_robot_id,
            "number_of_latest_reports": number_of_latest_reports,
        }
        response_dict: dict = self.client.query(query_string, params)
        return response_dict["missionReports"]["page"]["edges"]

    def _return_latest_mission_report_id(self, response: dict[str, Any]):
        print(response)
        return response[0]["node"]["id"]

    def get_last_mission_report_for_robot(self, exr_robot_id: str):
        reports = self.get_mission_report_ids_and_endtime_for_robot(
            settings.ROBOT_EXR_ID, 1
        )
        latest_report_id = self._return_latest_mission_report_id(reports)

        query_string: str = """
            query missionReport($report_id: String!) {
                missionReport(id: $report_id) {
                  dataPayloads{
                    dataType
                    uri
                  }
                }
            }

        """

        params = {"report_id": latest_report_id}
        response_dict: dict = self.client.query(query_string, params)
        return response_dict


if __name__ == "__main__":
    api = Api()
    print(api.get_last_mission_report_for_robot(settings.ROBOT_EXR_ID))
