from typing import Any, Dict
from unittest import mock

import pytest
from gql import Client

from isar_exr.api.energy_robotics_api import EnergyRoboticsApi


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
