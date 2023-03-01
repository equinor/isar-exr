from robot_interface.test_robot_interface import interface_test

from isar_exr.robotinterface import ExrRobot


def test_robotinterface():
    interface_test(ExrRobot())
