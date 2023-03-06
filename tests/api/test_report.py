import json

from isar_exr.api.energy_robotics_api import Api
from isar_exr.models.mission import MissionReport, MissionReports


def test_return_latest_mission_report_id():
    file = open("tests/data/mission_report_response.json", "r")
    response_dict = json.load(file)
    api = Api()
    latest_report_id = api._return_latest_mission_report_id(
        response_dict["missionReports"]["page"]["edges"]
    )
    assert latest_report_id == "606dd56c023c8866b43f7f7e"


def test_return_inspection_uri_for_poi():
    file = open("tests/data/inspection_report_response.json", "r")
    response_dict = json.load(file)
    poi_name = "beds_1"
    expected_uri = "https://actual.png"
    actual_uri = Api()._get_inspection_uri_for_poi(response_dict, poi_name)
    assert expected_uri == actual_uri


def test_construct_mission_reports_type_from_json():
    file = open("tests/data/mission_report_response.json", "r")
    response_dict = json.load(file)["missionReports"]
    mission_reports = MissionReports().from_dict(response_dict["page"]["edges"])
    assert isinstance(mission_reports, MissionReports)


if __name__ == "__main__":
    test_construct_mission_reports_type_from_json()
