from gql import gql
from graphql import DocumentNode
from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.models.step_status import ExrMissionStatus
from robot_interface.models.mission.status import StepStatus
from typing import Any



class Api():
    def __init__(self):
        self.client = GraphqlClient()

    def get_step_status(self, exr_robot_id: str) -> StepStatus:
        query_string: str = '''
            query currentMissionExecution($robot_id: String!) {
                currentMissionExecution(robotID: $robot_id) {
                    status
                    }
                }
        '''
        params: dict = {"robot_id": exr_robot_id}
        document: DocumentNode = gql(query_string)
        #this returns null if there is no mission being run
        response_dict: dict[str, Any] = self.client.query(document, params)
        print(response_dict)
        step_status = ExrMissionStatus(response_dict["currentMissionExecution"]["status"])
        return step_status.to_step_status()
