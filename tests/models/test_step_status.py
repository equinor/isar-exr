from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.models.step_status import ExrMissionStatus
from robot_interface.models.mission.status import StepStatus

from unittest import mock
import pytest
from isar_exr.config.settings import settings
from isar_exr.api.energy_robotics_api import Api
from isar_exr.models.exceptions import NoMissionRunningException


def test_to_step_status():
    mocked_response = "IN_PROGRESS"
    expected_status: StepStatus = StepStatus.InProgress

    status = ExrMissionStatus(mocked_response).to_step_status()
    assert expected_status == status


@mock.patch.object(Api, "is_mission_running", mock.Mock(return_value=True))
@mock.patch.object(
    GraphqlClient,
    "query",
    mock.Mock(return_value={"currentMissionExecution": {"status": "PAUSE_REQUESTED"}}),
)
@mock.patch.object(GraphqlClient, "__init__", mock.Mock(return_value=None))
def test_get_step_status_success():
    expected_status: StepStatus = StepStatus.InProgress
    api = Api()
    status = api.get_step_status(settings.ROBOT_EXR_ID)

    assert expected_status == status


@mock.patch.object(Api, "is_mission_running", mock.Mock(return_value=False))
@mock.patch.object(Api, "__init__", mock.Mock(return_value=None))
def test_get_step_status_error_mission_is_not_running():
    with pytest.raises(NoMissionRunningException):
        api = Api()
        api.get_step_status(settings.ROBOT_EXR_ID)

    api.is_mission_running.assert_called_once()
