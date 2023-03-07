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
    awake_status_awake: Dict[str, Any] = {"awakeStatus": AwakeStatus.Awake}
    awake_status_waking_up: Dict[str, Any] = {"awakeStatus": AwakeStatus.WakingUp}
    awake_status_asleep: Dict[str, Any] = {"awakeStatus": AwakeStatus.Asleep}
    awake_status_going_to_sleep: Dict[str, Any] = {
        "awakeStatus": AwakeStatus.GoingToSleep
    }

    @mock.patch.object(Client, "execute", mock.Mock(return_value=awake_status_awake))
    def test_returns_true_if_robot_is_awake(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        assert api.is_robot_awake("test_exr_robot_id") == True

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=awake_status_waking_up)
    )
    def test_returns_false_if_robot_is_waking_up(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        assert api.is_robot_awake("test_exr_robot_id") == False

    @mock.patch.object(Client, "execute", mock.Mock(return_value=awake_status_asleep))
    def test_returns_false_if_robot_is_asleep(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        assert api.is_robot_awake("test_exr_robot_id") == False

    @mock.patch.object(
        Client, "execute", mock.Mock(return_value=awake_status_going_to_sleep)
    )
    def test_returns_false_if_robot_is_going_toawake_status_going_to_sleep(self):
        api: EnergyRoboticsApi = EnergyRoboticsApi()
        assert api.is_robot_awake("test_exr_robot_id") == False
