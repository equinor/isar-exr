import json

from isar_exr.api.energy_robotics_api import Api

def test_return_latest_mission_report_id():
    file = open("tests/data/mission_report_response.json", "r")
    response_dict = json.load(file)
    api = Api()
    latest_report_id = api._return_latest_mission_report_id(response_dict)
    assert latest_report_id == "606dd56c023c8866b43f7f7e"

def test_return_latest_mission_report():
    assert 1 == 2
