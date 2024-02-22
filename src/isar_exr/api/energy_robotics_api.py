import json
import logging
from datetime import datetime
from logging import Logger
from time import sleep
from typing import Any, Dict, Optional

from gql.dsl import DSLMutation, DSLQuery, DSLSchema, DSLVariableDefinitions, dsl_gql
from robot_interface.models.exceptions.robot_exceptions import (
    RobotAPIException,
    RobotCommunicationException,
    RobotInfeasibleMissionException,
    RobotMapException,
    RobotMissionStatusException,
)
from robot_interface.models.mission.status import MissionStatus

from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.api.models.enums import AwakeStatus
from isar_exr.api.models.models import (
    AddPointOfInterestInput,
    BatteryStatusType,
    Pose3DStampedInput,
    UpsertPointOfInterestInput,
)
from isar_exr.config.settings import settings
from isar_exr.models.exceptions import NoMissionRunningException
from isar_exr.models.step_status import ExrMissionStatus


def to_dict(obj):
    return json.loads(json.dumps(obj, default=lambda o: o.__dict__))


class EnergyRoboticsApi:
    def __init__(self) -> None:
        self.client: GraphqlClient = GraphqlClient()
        self.schema: DSLSchema = self.client.schema
        self.logger: Logger = logging.getLogger(EnergyRoboticsApi.__name__)

    def get_mission_status(self, exr_robot_id: str) -> MissionStatus:
        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        current_mission_execution_query: DSLQuery = DSLQuery(
            self.schema.Query.currentMissionExecution.args(
                robotID=variable_definitions_graphql.robotID
            ).select(self.schema.MissionExecutionType.status)
        )

        current_mission_execution_query.variable_definitions = (
            variable_definitions_graphql
        )

        params: dict = {"robotID": exr_robot_id}

        if not self.is_mission_running(exr_robot_id):
            raise NoMissionRunningException(
                f"Cannot get EXR mission status - No EXR mission is running for robot "
                f"with id {exr_robot_id}"
            )

        response_dict: dict[str, Any] = self.client.query(
            dsl_gql(current_mission_execution_query), params
        )

        if response_dict["currentMissionExecution"] is None:
            raise NoMissionRunningException(
                f"Cannot get EXR mission status - No EXR mission is running for robot "
                f"with id {exr_robot_id}"
            )

        step_status = ExrMissionStatus(
            response_dict["currentMissionExecution"]["status"]
        )
        return step_status.to_mission_status()

    def is_mission_running(self, exr_robot_id: str) -> bool:
        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        is_mission_running_query: DSLQuery = DSLQuery(
            self.schema.Query.isMissionRunning.args(
                robotID=variable_definitions_graphql.robotID
            )
        )

        is_mission_running_query.variable_definitions = variable_definitions_graphql

        params: dict = {"robotID": exr_robot_id}
        response_dict: dict[str, Any] = self.client.query(
            dsl_gql(is_mission_running_query), params
        )

        return response_dict["isMissionRunning"]

    def pause_current_mission(self, exr_robot_id: str) -> None:
        params: dict = {"robotID": exr_robot_id}

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        pause_current_mission_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.pauseMissionExecution.args(
                robotID=variable_definitions_graphql.robotID
            ).select(
                self.schema.MissionExecutionType.id,
                self.schema.MissionExecutionType.status,
                self.schema.MissionExecutionType.failures,
            )
        )

        pause_current_mission_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            result: Dict[str, Any] = self.client.query(
                dsl_gql(pause_current_mission_mutation), params
            )
        except Exception:
            raise RobotCommunicationException(
                error_description="Could not pause the running mission",
            )

        status: ExrMissionStatus = ExrMissionStatus(result["status"])
        success: bool = status in [
            ExrMissionStatus.Paused,
            ExrMissionStatus.PauseRequested,
        ]
        if not success:
            raise RobotMissionStatusException(
                error_description=f"Invalid status after pausing mission: '{status}'"
            )

    def get_point_of_interest_by_customer_tag(
        self, customer_tag: str, site_id: str
    ) -> str:
        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        point_of_interest_query: DSLQuery = DSLQuery(
            self.schema.Query.pointOfInterestByCustomerTag.args(
                customerTag=variable_definitions_graphql.customerTag,
                siteId=variable_definitions_graphql.siteId,
            ).select(self.schema.PointOfInterestType.id)
        )

        point_of_interest_query.variable_definitions = variable_definitions_graphql

        params: dict = {"customerTag": customer_tag, "siteId": site_id}

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(point_of_interest_query), params
            )
        except Exception:
            return None

        if response_dict["pointOfInterestByCustomerTag"] is None:
            raise None

        return response_dict["pointOfInterestByCustomerTag"]["id"]

    def create_point_of_interest(
        self, point_of_interest_input: AddPointOfInterestInput
    ) -> str:
        params: dict[str, Any] = {
            "AddPointOfInterestInput": to_dict(point_of_interest_input),
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        create_point_of_interest_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.addPointOfInterest.args(
                input=variable_definitions_graphql.AddPointOfInterestInput
            ).select(self.schema.PointOfInterestType.id)
        )

        create_point_of_interest_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(create_point_of_interest_mutation), params
            )
        except Exception:
            message: str = "Could not create POI"
            self.logger.error(message)
            raise RobotMapException(
                error_description=message,
            )

        return response_dict["addPointOfInterest"]["id"]

    def upsert_point_of_interest(
        self, point_of_interest_input: UpsertPointOfInterestInput
    ) -> str:
        upsert_point_of_interest_input: Dict[str, Any] = to_dict(
            point_of_interest_input
        )
        upsert_point_of_interest_input["inspectionParameters"] = json.dumps(
            upsert_point_of_interest_input["inspectionParameters"]
        )
        params: dict[str, Any] = {
            "UpsertPointOfInterestInput": upsert_point_of_interest_input,
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        upsert_point_of_interest_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.upsertPointOfInterest.args(
                input=variable_definitions_graphql.UpsertPointOfInterestInput
            ).select(self.schema.PointOfInterestType.id)
        )

        upsert_point_of_interest_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(upsert_point_of_interest_mutation), params
            )
        except Exception:
            message: str = "Could not upsert POI"
            self.logger.error(message)
            raise RobotMapException(
                error_description=message,
            )

        return response_dict["upsertPointOfInterest"]["id"]

    def create_dock_robot_task_definition(
        self, site_id: str, task_name: str, docking_station_id: str
    ) -> str:
        params: dict[str, Any] = {
            "siteId": site_id,
            "name": task_name,
            "dockingStationId": docking_station_id,
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        mutation_args: dict[str, Any] = {
            "input": {
                "siteId": variable_definitions_graphql.siteId,
                "name": variable_definitions_graphql.name,
                "dockingStationId": variable_definitions_graphql.dockingStationId,
            }
        }

        create_dock_robot_task_definition_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.createDockRobotTaskDefinition.args(
                **mutation_args
            ).select(self.schema.DockRobotTaskDefinitionType.id)
        )

        create_dock_robot_task_definition_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(create_dock_robot_task_definition_mutation), params
            )
        except Exception:
            message: str = "Could not create dock task definition"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        return response_dict["createDockRobotTaskDefinition"]["id"]

    def create_point_of_interest_inspection_task_definition(
        self, site_id: str, task_name: str, point_of_interest_id: str
    ) -> str:
        params: dict[str, Any] = {
            "siteId": site_id,
            "name": task_name,
            "poiId": point_of_interest_id,
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        mutation_args: dict[str, Any] = {
            "input": {
                "siteId": variable_definitions_graphql.siteId,
                "name": variable_definitions_graphql.name,
                "poiId": variable_definitions_graphql.poiId,
            }
        }

        create_poi_inspection_task_definition_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.createPoiInspectionTaskDefinition.args(
                **mutation_args
            ).select(self.schema.PoiInspectionTaskDefinitionType.id)
        )

        create_poi_inspection_task_definition_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(create_poi_inspection_task_definition_mutation), params
            )
        except Exception:
            message: str = "Could not create dock task definition"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        return response_dict["createPoiInspectionTaskDefinition"]["id"]

    def create_waypoint_task_definition(
        self, site_id: str, task_name: str, pose_3D_stamped_input: Pose3DStampedInput
    ) -> str:
        params: dict[str, Any] = {
            "siteId": site_id,
            "name": task_name,
            "waypoint": to_dict(pose_3D_stamped_input),
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        mutation_args: dict[str, Any] = {
            "input": {
                "siteId": variable_definitions_graphql.siteId,
                "name": variable_definitions_graphql.name,
                "waypoint": variable_definitions_graphql.waypoint,
            }
        }
        create_waypoint_task_definition_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.createWaypointTaskDefinition.args(
                **mutation_args
            ).select(self.schema.WaypointTaskDefinitionType.id)
        )

        create_waypoint_task_definition_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(create_waypoint_task_definition_mutation), params
            )
        except Exception:
            message: str = "Could not create waypoint task definition"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        return response_dict["createWaypointTaskDefinition"]["id"]

    def add_task_to_mission_definition(
        self, task_id: str, mission_definition_id: str, index: int = -1
    ):
        params: dict[str, Any] = {
            "missionTaskDefinitionId": task_id,
            "missionDefinitionId": mission_definition_id,
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()
        mutation_args: dict[str, Any] = {
            "missionTaskDefinitionId": variable_definitions_graphql.missionTaskDefinitionId,
            "missionDefinitionId": variable_definitions_graphql.missionDefinitionId,
        }
        if index >= 0:
            mutation_args["index"] = variable_definitions_graphql.index
            params["index"] = index

        add_task_to_mission_definition_mutation: DSLMutation = DSLMutation(
            self.client.schema.Mutation.addTaskToMissionDefinition.args(
                **mutation_args
            ).select(self.client.schema.MissionDefinitionType.id)
        )

        add_task_to_mission_definition_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(add_task_to_mission_definition_mutation), params
            )
        except Exception:
            message: str = "Could not add task to mission definition"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        return response_dict["addTaskToMissionDefinition"]["id"]

    def remove_task_from_mission_definition(
        self, task_id: str, mission_definition_id: str
    ):
        params: dict[str, Any] = {
            "missionTaskDefinitionId": task_id,
            "missionDefinitionId": mission_definition_id,
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()
        mutation_args: dict[str, Any] = {
            "missionTaskDefinitionId": variable_definitions_graphql.missionTaskDefinitionId,
            "missionDefinitionId": variable_definitions_graphql.missionDefinitionId,
        }

        remove_task_from_mission_definition_mutation: DSLMutation = DSLMutation(
            self.client.schema.Mutation.removeTaskFromMissionDefinition.args(
                **mutation_args
            ).select(self.client.schema.MissionDefinitionType.id)
        )

        remove_task_from_mission_definition_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(remove_task_from_mission_definition_mutation), params
            )
        except Exception:
            message: str = "Could not remove task from mission definition"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        return response_dict["removeTaskFromMissionDefinition"]["id"]

    def wake_up_robot(
        self, exr_robot_id: str, timeout: int = settings.MAX_TIME_FOR_WAKEUP
    ) -> None:
        params: dict = {"robotID": exr_robot_id}

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        wake_up_robot_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.executeAwakeCommand.args(
                targetState=AwakeStatus.Awake,
                robotID=variable_definitions_graphql.robotID,
            ).select(
                self.schema.RobotCommandExecutionType.id,
            )
        )

        wake_up_robot_mutation.variable_definitions = variable_definitions_graphql

        try:
            result: Dict[str, Any] = (
                self.client.query(  # TODO: consider checking if request was accepted
                    dsl_gql(wake_up_robot_mutation), params
                )
            )
        except Exception:
            message: str = "Could not wake up robot"
            self.logger.error(message)
            raise RobotMissionStatusException(
                error_description=message,
            )

        startTime = datetime.today()
        while not self.is_robot_awake(exr_robot_id):
            time_passed_since_function_call = (
                datetime.today() - startTime
            ).total_seconds()
            if time_passed_since_function_call > timeout:
                raise RobotMissionStatusException(
                    error_description=f"Not able to wake up robot after '{timeout}' seconds.",
                )
            sleep(1)

    def is_robot_awake(self, exr_robot_id: str) -> bool:
        params: dict = {"robotID": exr_robot_id}

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        check_if_awake_query: DSLQuery = DSLQuery(
            self.schema.Query.currentRobotStatus.args(
                robotID=variable_definitions_graphql.robotID
            ).select(
                self.schema.RobotStatusType.isConnected,
                self.schema.RobotStatusType.awakeStatus,
            )
        )

        check_if_awake_query.variable_definitions = variable_definitions_graphql

        try:
            result: Dict[str, Any] = self.client.query(
                dsl_gql(check_if_awake_query), params
            )
        except Exception:
            message: str = "Could not check if robot is awake"
            self.logger.error(message)
            raise RobotMissionStatusException(
                error_description=message,
            )

        if not result["currentRobotStatus"]["isConnected"]:
            raise RobotMissionStatusException(
                error_description="Robot is not connected",
            )

        status: AwakeStatus = AwakeStatus(result["currentRobotStatus"]["awakeStatus"])
        success: bool = status in [AwakeStatus.Awake]
        return success

    def get_battery_level(self, exr_robot_id: str) -> Optional[float]:
        params: dict = {"robotID": exr_robot_id}

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        check_battery_query: DSLQuery = DSLQuery(
            self.schema.Query.currentRobotStatus.args(
                robotID=variable_definitions_graphql.robotID
            ).select(
                self.schema.RobotStatusType.isConnected,
                self.schema.RobotStatusType.batteryStatus.select(
                    self.schema.BatteryStatusType.percentage
                ),
            )
        )

        check_battery_query.variable_definitions = variable_definitions_graphql

        try:
            result: Dict[str, Any] = self.client.query(
                dsl_gql(check_battery_query), params
            )
        except TimeoutError as e:
            self.logger.error(
                "Could not check robot battery level due to request timeout"
            )
            return None
        except Exception as e:
            message: str = "Could not check robot battery level"
            self.logger.error(message)
            raise RobotMissionStatusException(
                error_description=message,
            )

        if not result["currentRobotStatus"]["isConnected"]:
            return None

        battery_level: float = result["currentRobotStatus"]["batteryStatus"][
            "percentage"
        ]
        return battery_level

    def is_connected(self, exr_robot_id: str) -> bool:
        params: dict = {"robotID": exr_robot_id}

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        check_is_connected_query: DSLQuery = DSLQuery(
            self.schema.Query.currentRobotStatus.args(
                robotID=variable_definitions_graphql.robotID
            ).select(
                self.schema.RobotStatusType.isConnected,
            )
        )

        check_is_connected_query.variable_definitions = variable_definitions_graphql

        try:
            result: Dict[str, Any] = self.client.query(
                dsl_gql(check_is_connected_query), params
            )
        except TimeoutError:
            return False
        except Exception:
            message: str = "Could not check if the robot is connected"
            self.logger.error(message)
            raise RobotCommunicationException(
                error_description=message,
            )

        return result["currentRobotStatus"]["isConnected"]

    def create_mission_definition(
        self, site_id: str, mission_name: str, robot_id: str
    ) -> str:
        params: dict[str, Any] = {
            "siteId": site_id,
            "name": mission_name,
            "requiredRobotConfig": {"robotId": robot_id},
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        mutation_args: dict[str, Any] = {
            "input": {
                "siteId": variable_definitions_graphql.siteId,
                "name": variable_definitions_graphql.name,
                "requiredRobotConfig": variable_definitions_graphql.requiredRobotConfig,
            }
        }
        create_mission_definition_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.createMissionDefinition.args(**mutation_args).select(
                self.schema.MissionDefinitionType.id
            )
        )

        create_mission_definition_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(create_mission_definition_mutation), params
            )
        except Exception:
            message: str = "Could not create mission definition"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        mission_definition_id = response_dict["createMissionDefinition"]["id"]
        return mission_definition_id

    def start_mission_execution(self, mission_definition_id: str, robot_id: str) -> str:
        params: dict[str, Any] = {
            "robotID": robot_id,
            "missionDefinitionID": mission_definition_id,
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        mutation_args: dict[str, Any] = {
            "input": {
                "robotID": variable_definitions_graphql.robotID,
                "missionDefinitionID": variable_definitions_graphql.missionDefinitionID,
            }
        }
        start_mission_execution_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.startMissionExecution.args(**mutation_args).select(
                self.schema.MissionExecutionType.id
            )
        )

        start_mission_execution_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(start_mission_execution_mutation), params
            )
        except Exception:
            message: str = "Could not start mission execution"
            self.logger.error(message)
            raise RobotInfeasibleMissionException(
                error_description=message,
            )

        mission_execution_id = response_dict["startMissionExecution"]["id"]
        return mission_execution_id

    def discard_stage(self, stage_id: str) -> str:
        params: dict[str, Any] = {
            "siteStageId": stage_id,
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        discard_stage_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.discardSiteStage.args(
                siteStageId=variable_definitions_graphql.siteStageId,
            ).select(self.schema.SiteStageType.id)
        )

        discard_stage_mutation.variable_definitions = variable_definitions_graphql

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(discard_stage_mutation), params
            )
        except Exception:
            raise RobotAPIException(
                error_description="Could not discard stage",
            )

        return response_dict["discardSiteStage"]["id"]

    def create_stage(self, site_id: str) -> str:
        params: dict[str, Any] = {
            "siteId": site_id,
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        create_stage_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.openSiteStage.args(
                siteId=variable_definitions_graphql.siteId,
            ).select(self.schema.SiteStageType.id)
        )

        create_stage_mutation.variable_definitions = variable_definitions_graphql

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(create_stage_mutation), params
            )
        except Exception:
            message: str = "Could not create stage"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        return response_dict["openSiteStage"]["id"]

    def add_point_of_interest_to_stage(self, POI_id: str, stage_id: str) -> str:
        params: dict[str, Any] = {"siteStageId": stage_id, "pointOfInterestId": POI_id}

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        add_point_of_interest_to_stage_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.addPointOfInterestToStage.args(
                siteStageId=variable_definitions_graphql.siteStageId,
                pointOfInterestId=variable_definitions_graphql.pointOfInterestId,
            ).select(self.schema.SiteStageType.id)
        )

        add_point_of_interest_to_stage_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(add_point_of_interest_to_stage_mutation), params
            )
        except Exception:
            raise RobotAPIException(
                error_description="Could not add POI to stage",
            )

        return response_dict["addPointOfInterestToStage"]["id"]

    def commit_site_to_snapshot(self, stage_id: str) -> str:
        params: dict[str, Any] = {
            "siteStageId": stage_id,
        }

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        commit_site_to_snapshot_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.commitSiteChanges.args(
                siteStageId=variable_definitions_graphql.siteStageId,
            ).select(self.schema.SiteSnapshotType.id)
        )

        commit_site_to_snapshot_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(commit_site_to_snapshot_mutation), params
            )
        except Exception:
            message: str = "Could not commit site to snapshot"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        return response_dict["commitSiteChanges"]["id"]

    def is_pipeline_completed(self, site_id: str) -> bool:
        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        current_processing_pipeline: DSLQuery = DSLQuery(
            self.schema.Query.currentSiteSnapshotHeadSelectionProcessingPipeline.args(
                siteId=variable_definitions_graphql.siteId
            ).select(
                self.schema.ProcessingPipelineType.stages.select(
                    self.schema.ProcessingPipelineStageType.state
                )
            )
        )

        current_processing_pipeline.variable_definitions = variable_definitions_graphql

        params: dict = {"siteId": site_id}

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(current_processing_pipeline), params
            )
        except Exception as e:
            message: str = "Could not get current processing pipeline"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        if (
            response_dict["currentSiteSnapshotHeadSelectionProcessingPipeline"][
                "stages"
            ][0]["state"]
            == "COMPLETED"
        ):
            return True
        return False

    def set_snapshot_as_head(self, snapshot_id: str, site_id: str) -> str:
        params: dict[str, Any] = {"siteId": site_id, "siteSnapshotId": snapshot_id}

        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        set_snapshot_as_head_mutation: DSLMutation = DSLMutation(
            self.schema.Mutation.processSiteSnapshotHeadSelection.args(
                siteId=variable_definitions_graphql.siteId,
                siteSnapshotId=variable_definitions_graphql.siteSnapshotId,
            ).select(self.schema.ProcessingPipelineType.id)
        )

        set_snapshot_as_head_mutation.variable_definitions = (
            variable_definitions_graphql
        )

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(set_snapshot_as_head_mutation), params
            )
        except Exception:
            message: str = "Could not set snapshop as head"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        return response_dict["processSiteSnapshotHeadSelection"]["id"]

    def get_current_site_stage(self, site_id: str) -> str:
        variable_definitions_graphql: DSLVariableDefinitions = DSLVariableDefinitions()

        current_site_stage_query: DSLQuery = DSLQuery(
            self.schema.Query.currentSiteStage.args(
                siteId=variable_definitions_graphql.siteId
            ).select(self.schema.SiteStageType.id)
        )

        current_site_stage_query.variable_definitions = variable_definitions_graphql

        params: dict = {"siteId": site_id}

        try:
            response_dict: dict[str, Any] = self.client.query(
                dsl_gql(current_site_stage_query), params
            )

            if response_dict["currentSiteStage"] is not None:
                return response_dict["currentSiteStage"]["id"]
        except Exception as e:
            message: str = "Could not get current site stage"
            self.logger.error(message)
            raise RobotAPIException(
                error_description=message,
            )

        return None
