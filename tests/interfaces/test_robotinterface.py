from unittest import mock

from robot_interface.test_robot_interface import interface_test

from isar_exr.api.graphql_client import GraphqlClient
from isar_exr.robotinterface import ExrRobot


@mock.patch.object(GraphqlClient, "__init__", mock.Mock(return_value=None))
def test_robotinterface():
    interface_test(ExrRobot())
