from unittest import mock

import pytest
from robot_interface.models.exceptions import RobotException
from robot_interface.test_robot_interface import interface_test

from isar_exr.api.energy_robotics_api import EnergyRoboticsApi
from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.robotinterface import ExrRobot


@mock.patch("isar_exr.api.energy_robotics_api.GraphqlClient")
def test_robotinterface(MockedGraphQlClient):
    interface_test(ExrRobot())


@mock.patch("isar_exr.api.energy_robotics_api.GraphqlClient")
@mock.patch.object(
    EnergyRoboticsApi, "pause_current_mission", mock.Mock(side_effect=Exception)
)
def test_stop_raises_RobotException_if_pause_fails(MockedGraphqlClient):
    robot: ExrRobot = ExrRobot()
    with pytest.raises(expected_exception=RobotException):
        robot.stop()
