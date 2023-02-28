from isar_exr.models.step_status import ExrMissionStatus
from robot_interface.models.mission.status import StepStatus

def test_step_status():
    mocked_response = "IN_PROGRESS"
    expected_result: StepStatus = StepStatus.InProgress

    result = ExrMissionStatus(mocked_response).to_step_status()
    assert expected_result == result
    