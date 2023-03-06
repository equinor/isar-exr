from enum import Enum
from pydantic import BaseModel
from typing import Union, Optional, Any
from datetime import datetime


class MissionReport:
    # TODO: fill in types?
    def __init__(
        self,
        id=None,
        key=None,
        startTimestamp=None,
        endTimestamp: datetime = None,
        robot=None,
        diagnostics: list = None,
        trajectory: list = None,
        distance=None,
        duration=None,
        missionDefinition: list = None,
        data_payloads: list = None,
    ):
        self.id = id
        self.key = key
        self.start_time_stamp = startTimestamp
        self.end_time_stamp = endTimestamp
        self.robot = robot
        self.diagnostics = diagnostics
        self.trajectory = trajectory
        self.distance = distance
        self.duration = duration
        self.misssionDefinition = missionDefinition
        self.dataPayloads = data_payloads


class MissionReports:
    reports: list[MissionReport] = []

    def from_dict(self, reports_dict):
        if not isinstance(reports_dict, list) or len(reports_dict) == 0:
            raise TypeError("No inspections in report")

        for report_dict in reports_dict:
            report = MissionReport(**report_dict["node"])
            self.append_to_report_list(report)
        return self

    def append_to_report_list(self, report: MissionReport):
        self.reports.append(report)


class AbstractDataPayloadType:
    id: Union[str, int, float]
    key: str
    parentPayloadKey: str
    dataType: DataPayload
    producer: Any
    dataLabel: str
    regionOfInterest: Any
    poiName: str
    isSynced: bool
    pass


class DataPayload(Enum):
    Photo = "PHOTO"
    Video = "VIDEO"
    Audio = "AUDIO"
    TimeSeries1D = "TIME_SERIES_1D"
    PhotoOverlay = "PHOTO_OVERLAY"
    JsonData = "JSON_DATA"
    Group = "GROUP"
