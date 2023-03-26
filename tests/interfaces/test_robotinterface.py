from unittest import mock

import pytest
from isar_exr.api.energy_robotics_api import EnergyRoboticsApi
from isar_exr.robotinterface import Robot
from robot_interface.models.exceptions import RobotException
from robot_interface.test_robot_interface import interface_test


@mock.patch("isar_exr.api.energy_robotics_api.GraphqlClient")
def test_robotinterface(MockedGraphQlClient):
    interface_test(Robot())


@mock.patch("isar_exr.api.energy_robotics_api.GraphqlClient")
@mock.patch.object(
    EnergyRoboticsApi, "pause_current_mission", mock.Mock(side_effect=Exception)
)
def test_stop_raises_RobotException_if_pause_fails(MockedGraphqlClient):
    robot: Robot = Robot()
    with pytest.raises(expected_exception=RobotException):
        robot.stop()
