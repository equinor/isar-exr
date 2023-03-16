from datetime import datetime, timedelta
from typing import Any, Dict
from unittest import mock
from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.api.models.enums import AwakeStatus

import pytest
from gql import Client

from isar_exr.api.energy_robotics_api import EnergyRoboticsApi
from robot_interface.models.exceptions import RobotException
from isar_exr.config.settings import settings
from isar_exr.api.models.models import (
    AddPointOfInterestInput,
    Point3DInput,
    QuaternionInput,
    Pose3DInput,
    PointOfInterestTypeEnum,
    PointOfInterestActionPhotoInput,
)


@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
class TestPauseMission:
    pause_requested_response: Dict[str, Any] = {"status": "PAUSE_REQUESTED"}
    paused_response: Dict[str, Any] = {"status": "PAUSED"}
    wrong_response: Dict[str, Any] = {"status": "REJECTED"}

    @mock.patch.object(Client, "execute", mock.Mock(return_value=paused_response))
    def test_succeeds_if_status_is_paused(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        api.pause_current_mission("test_exr_robot_id")

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=pause_requested_response)
    )
    def test_succeeds_if_status_is_paused_requested(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        api.pause_current_mission("test_exr_robot_id")

    @mock.patch.object(Client, "execute", mock.Mock(return_value=wrong_response))
    def test_fails_if_status_is_anything_else(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=Exception):
            api.pause_current_mission("test_exr_robot_id")


@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
class TestCreatePointOfinterest:
    expected_return_id = "point_of_interest_type_id"
    api_point_of_interest_response: Dict[str, Any] = {
        "addPointOfInterest": {"id": expected_return_id}
    }

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=api_point_of_interest_response)
    )
    def test_succeeds_if_id_returned(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        position: Point3DInput = Point3DInput(x=0, y=0, z=0)
        orientation: QuaternionInput = QuaternionInput(x=0, y=0, z=0, w=0)
        pose: Pose3DInput = Pose3DInput(position=position, orientation=orientation)
        action: PointOfInterestActionPhotoInput = PointOfInterestActionPhotoInput(
            robotPose=pose, sensor="mock_sensor"
        )
        poi: AddPointOfInterestInput = AddPointOfInterestInput(
            name="mock_name",
            site="mock_site",
            frame="mock_frame",
            type=PointOfInterestTypeEnum.GENERIC,
            pose=pose,
            photoAction=action,
        )
        return_value = api.create_point_of_interest(point_of_interest_input=poi)
        assert return_value == self.expected_return_id

    @mock.patch.object(Client, "execute", mock.Mock(side_effect=Exception))
    def test_api_return_exeption(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        position: Point3DInput = Point3DInput(x=0, y=0, z=0)
        orientation: QuaternionInput = QuaternionInput(x=0, y=0, z=0, w=0)
        pose: Pose3DInput = Pose3DInput(position=position, orientation=orientation)
        action: PointOfInterestActionPhotoInput = PointOfInterestActionPhotoInput(
            robotPose=pose, sensor="mock_sensor"
        )
        poi: AddPointOfInterestInput = AddPointOfInterestInput(
            name="mock_name",
            site="mock_site",
            frame="mock_frame",
            type=PointOfInterestTypeEnum.GENERIC,
            pose=pose,
            photoAction=action,
        )
        with pytest.raises(expected_exception=RobotException):
            api.create_point_of_interest(point_of_interest_input=poi)


@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
@mock.patch(
    "isar_exr.api.energy_robotics_api.to_dict",
    mock.Mock(return_value="mocked_dict_version"),
)
class TestTaskCreatorFunctions:
    site_id = "Costa Nova"
    task_name = "dummy task"
    docking_station_id = "dummy docking station id"
    point_of_interest_id = "dummy poi id"
    pose_3d_stamped_input = mock.Mock()

    dock_robot_mocked_response: Dict[str, Any] = {
        "createDockRobotTaskDefinition": {"id": "dummy_task_id"}
    }
    point_of_interest_inspection_mocked_response: Dict[str, Any] = {
        "createPoiInspectionTaskDefinition": {"id": "dummy_task_id"}
    }
    waypoint_mocked_response: Dict[str, Any] = {
        "createWaypointTaskDefinition": {"id": "dummy_task_id"}
    }

    @mock.patch.object(
        GraphqlClient, "query", mock.Mock(return_value=dock_robot_mocked_response)
    )
    def test_create_dock_robot_task_definition_success(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        received_task_id: str = api.create_dock_robot_task_definition(
            site_id=self.site_id,
            task_name=self.task_name,
            docking_station_id=self.docking_station_id,
        )
        assert (
            received_task_id
            == self.dock_robot_mocked_response["createDockRobotTaskDefinition"]["id"]
        )

    @mock.patch.object(GraphqlClient, "query", mock.Mock(side_effect=Exception()))
    def test_create_dock_robot_task_definition_error(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.create_dock_robot_task_definition(
                site_id=self.site_id,
                task_name=self.task_name,
                docking_station_id=self.docking_station_id,
            )

    @mock.patch.object(
        GraphqlClient,
        "query",
        mock.Mock(return_value=point_of_interest_inspection_mocked_response),
    )
    def test_create_point_of_interest_inspection_task_definition_success(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        received_task_id: str = api.create_point_of_interest_inspection_task_definition(
            site_id=self.site_id,
            task_name=self.task_name,
            point_of_interest_id=self.point_of_interest_id,
        )
        assert (
            received_task_id
            == self.point_of_interest_inspection_mocked_response[
                "createPoiInspectionTaskDefinition"
            ]["id"]
        )

    @mock.patch.object(GraphqlClient, "query", mock.Mock(side_effect=Exception()))
    def test_create_point_of_interest_inspection_task_definition_error(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.create_point_of_interest_inspection_task_definition(
                site_id=self.site_id,
                task_name=self.task_name,
                point_of_interest_id=self.point_of_interest_id,
            )

    @mock.patch.object(
        GraphqlClient, "query", mock.Mock(return_value=waypoint_mocked_response)
    )
    def test_create_waypoint_task_definition_success(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        received_task_id: str = api.create_waypoint_task_definition(
            site_id=self.site_id,
            task_name=self.task_name,
            pose_3D_stamped_input=self.pose_3d_stamped_input,
        )
        assert (
            received_task_id
            == self.waypoint_mocked_response["createWaypointTaskDefinition"]["id"]
        )

    @mock.patch.object(GraphqlClient, "query", mock.Mock(side_effect=Exception()))
    def test_create_waypoint_task_definition_error(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.create_waypoint_task_definition(
                site_id=self.site_id,
                task_name=self.task_name,
                pose_3D_stamped_input=self.pose_3d_stamped_input,
            )


@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
class TestWakeUpRobot:
    wake_up_requested_response: Dict[str, Any] = {"id": "command_id"}

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=wake_up_requested_response)
    )
    @mock.patch.object(
        EnergyRoboticsApi, "is_robot_awake", mock.Mock(return_value=True)
    )
    def test_succeeds_if_robot_is_awake(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        api.wake_up_robot("test_exr_robot_id")

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=wake_up_requested_response)
    )
    @mock.patch.object(
        EnergyRoboticsApi, "is_robot_awake", mock.Mock(return_value=False)
    )
    def test_fails_if_robot_is_not_awake_after_max_time(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.wake_up_robot("test_exr_robot_id", 1)


@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
class TestRobotAwakeQuery:
    mocked_response_awake: Dict[str, Any] = {
        "currentRobotStatus": {"isConnected": True, "awakeStatus": AwakeStatus.Awake}
    }
    mocked_response_waking_up: Dict[str, Any] = {
        "currentRobotStatus": {"isConnected": True, "awakeStatus": AwakeStatus.WakingUp}
    }
    mocked_response_going_to_sleep: Dict[str, Any] = {
        "currentRobotStatus": {
            "isConnected": True,
            "awakeStatus": AwakeStatus.GoingToSleep,
        }
    }
    mocked_response_asleep: Dict[str, Any] = {
        "currentRobotStatus": {"isConnected": True, "awakeStatus": AwakeStatus.Asleep}
    }
    mocked_response_not_connected: Dict[str, Any] = {
        "currentRobotStatus": {"isConnected": False, "awakeStatus": AwakeStatus.Asleep}
    }

    @mock.patch.object(Client, "execute", mock.Mock(return_value=mocked_response_awake))
    def test_returns_true_if_robot_is_awake(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        assert api.is_robot_awake("test_exr_robot_id") == True

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=mocked_response_waking_up)
    )
    def test_returns_false_if_robot_is_waking_up(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        assert api.is_robot_awake("test_exr_robot_id") == False

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=mocked_response_asleep)
    )
    def test_returns_false_if_robot_is_asleep(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        assert api.is_robot_awake("test_exr_robot_id") == False

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=mocked_response_going_to_sleep)
    )
    def test_returns_false_if_robot_is_going_to_awake_status_going_to_sleep(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        assert api.is_robot_awake("test_exr_robot_id") == False

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=mocked_response_not_connected)
    )
    def test_raises_exception_if_robot_is_not_connected(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.is_robot_awake("test_exr_robot_id")


@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
class TestCreateMissionDefinition:
    expected_return_id = "mission_definition"
    api_execute_response: Dict[str, Any] = {
        "createMissionDefinition": {"id": expected_return_id}
    }

    @mock.patch.object(Client, "execute", mock.Mock(return_value=api_execute_response))
    def test_succeeds_if_id_returned(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        return_value = api.create_mission_definition(
            site_id="mock_site_id",
            mission_name="mock_mission_name",
            robot_id="mock_robot_id",
        )
        assert return_value == self.expected_return_id

    @mock.patch.object(Client, "execute", mock.Mock(side_effect=Exception))
    def test_api_return_exeption(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.create_mission_definition(
                site_id="mock_site_id",
                mission_name="mock_mission_name",
                robot_id="mock_robot_id",
            )


@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
class TestStartMissionExecution:
    expected_return_id = "mission_execution_id"
    api_execute_response: Dict[str, Any] = {
        "startMissionExecution": {"id": expected_return_id}
    }

    @mock.patch.object(Client, "execute", mock.Mock(return_value=api_execute_response))
    def test_succeeds_if_id_returned(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        return_value = api.start_mission_execution(
            mission_definition_id="mock:mission:definition_id",
            robot_id="mock_robot_id",
        )
        assert return_value == self.expected_return_id

    @mock.patch.object(Client, "execute", mock.Mock(side_effect=Exception))
    def test_api_return_exeption(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.start_mission_execution(
                mission_definition_id="mock:mission:definition_id",
                robot_id="mock_robot_id",
            )


@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
class TestStageAndSnapshot:
    create_stage_expected_return_id = "stage_id"
    api_execute_response_crate_stage: Dict[str, Any] = {
        "openSiteStage": {"id": create_stage_expected_return_id}
    }
    add_poi_to_stage_expected_return_id = "stage_id"
    api_execute_response_add_poi_to_stage: Dict[str, Any] = {
        "addPointOfInterestToStage": {"id": add_poi_to_stage_expected_return_id}
    }
    commit_site_expected_return_id = "snapshot_id"
    api_execute_response_commit_site: Dict[str, Any] = {
        "commitSiteChanges": {"id": commit_site_expected_return_id}
    }
    set_head_expected_return_id = "snapshot_id"
    api_execute_response_set_head: Dict[str, Any] = {
        "selectCurrentSiteSnapshotHead": {"id": set_head_expected_return_id}
    }

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=api_execute_response_crate_stage)
    )
    def test_create_stage_succeeds_if_id_returned(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        return_value = api.create_stage(site_id="mock_site_id")
        assert return_value == self.create_stage_expected_return_id

    @mock.patch.object(Client, "execute", mock.Mock(side_effect=Exception))
    def test_create_stage_api_return_exeption(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.create_stage(site_id="mock_site_id")

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=api_execute_response_add_poi_to_stage)
    )
    def test_add_poi_succeeds_if_id_returned(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        return_value = api.add_point_of_interest_to_stage(
            stage_id="mock_stage_id", POI_id="mock_poi_id"
        )
        assert return_value == self.add_poi_to_stage_expected_return_id

    @mock.patch.object(Client, "execute", mock.Mock(side_effect=Exception))
    def test_add_poi_api_return_exeption(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.add_point_of_interest_to_stage(
                stage_id="mock_stage_id", POI_id="mock_poi_id"
            )

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=api_execute_response_commit_site)
    )
    def test_commit_site_succeeds_if_id_returned(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        return_value = api.commit_site_to_snapshot(stage_id="mock_stage_id")
        assert return_value == self.commit_site_expected_return_id

    @mock.patch.object(Client, "execute", mock.Mock(side_effect=Exception))
    def test_commit_site_api_return_exeption(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.commit_site_to_snapshot(stage_id="mock_stage_id")

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=api_execute_response_set_head)
    )
    def test_set_head_succeeds_if_id_returned(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        return_value = api.set_snapshot_as_head(
            snapshot_id="mock_snapshot_id", site_id="mock_site_id"
        )
        assert return_value == self.set_head_expected_return_id

    @mock.patch.object(Client, "execute", mock.Mock(side_effect=Exception))
    def test_set_head_api_return_exeption(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.set_snapshot_as_head(
                snapshot_id="mock_snapshot_id", site_id="mock_site_id"
            )


@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
class TestAddRemoveTaskToFromMissionDefinition:
    task_id = "dummy_task_id"
    mission_definition_id = "dummy_mission_id"
    index = 2

    add_task_response: Dict[str, Any] = {
        "addTaskToMissionDefinition": {"id": "dummy_mission_id"}
    }

    remove_task_response: Dict[str, Any] = {
        "removeTaskFromMissionDefinition": {"id": "dummy_mission_id"}
    }

    @mock.patch.object(
        GraphqlClient,
        "query",
        mock.Mock(return_value=add_task_response),
    )
    def test_add_task_to_mission_definition_no_index_success(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        received_mission_definition_id: str = api.add_task_to_mission_definition(
            task_id=self.task_id,
            mission_definition_id=self.mission_definition_id,
        )
        assert (
            received_mission_definition_id
            == self.add_task_response["addTaskToMissionDefinition"]["id"]
        )

    @mock.patch.object(
        GraphqlClient,
        "query",
        mock.Mock(return_value=add_task_response),
    )
    def test_add_task_to_mission_definition_specific_index_success(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        received_mission_definition_id: str = api.add_task_to_mission_definition(
            task_id=self.task_id,
            mission_definition_id=self.mission_definition_id,
            index=self.index,
        )
        assert (
            received_mission_definition_id
            == self.add_task_response["addTaskToMissionDefinition"]["id"]
        )

    @mock.patch.object(GraphqlClient, "query", mock.Mock(side_effect=Exception()))
    def test_add_task_to_mission_definition_error(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.add_task_to_mission_definition(
                task_id=self.task_id,
                mission_definition_id=self.mission_definition_id,
            )

    @mock.patch.object(
        GraphqlClient,
        "query",
        mock.Mock(return_value=remove_task_response),
    )
    def test_remove_task_from_mission_definition_success(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        received_mission_definition_id: str = api.remove_task_from_mission_definition(
            task_id=self.task_id,
            mission_definition_id=self.mission_definition_id,
        )
        assert (
            received_mission_definition_id
            == self.remove_task_response["removeTaskFromMissionDefinition"]["id"]
        )

    @mock.patch.object(GraphqlClient, "query", mock.Mock(side_effect=Exception()))
    def test_remove_task_from_mission_definition_error(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        with pytest.raises(expected_exception=RobotException):
            api.remove_task_from_mission_definition(
                task_id=self.task_id,
                mission_definition_id=self.mission_definition_id,
            )
