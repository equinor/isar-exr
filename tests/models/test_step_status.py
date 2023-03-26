from unittest import mock

import pytest
from robot_interface.models.mission.status import StepStatus

from isar_exr.api.energy_robotics_api import EnergyRoboticsApi
from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.config.settings import settings
from isar_exr.models.exceptions import NoMissionRunningException
from isar_exr.models.step_status import ExrMissionStatus


def test_to_step_status():
    mocked_response = "IN_PROGRESS"
    expected_status: StepStatus = StepStatus.InProgress

    status = ExrMissionStatus(mocked_response).to_mission_status()
    assert expected_status == status


@mock.patch.object(
    EnergyRoboticsApi, "is_mission_running", mock.Mock(return_value=True)
)
@mock.patch.object(
    GraphqlClient,
    "query",
    mock.Mock(return_value={"currentMissionExecution": {"status": "PAUSE_REQUESTED"}}),
)
@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
def test_get_step_status_success():
    expected_status: StepStatus = StepStatus.InProgress
    api = EnergyRoboticsApi()
    status = api.get_mission_status(settings.ROBOT_EXR_ID)

    assert expected_status == status


@mock.patch.object(
    EnergyRoboticsApi, "is_mission_running", mock.Mock(return_value=False)
)
@mock.patch(
    "isar_exr.api.graphql_client.get_access_token",
    mock.Mock(return_value="test_token"),
)
def test_get_step_status_error_mission_is_not_running():
    api = EnergyRoboticsApi()
    with pytest.raises(NoMissionRunningException):
        api.get_mission_status(settings.ROBOT_EXR_ID)

    api.is_mission_running.assert_called_once()
