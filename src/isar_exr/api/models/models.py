from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Point3DInput(BaseModel):
    x: float
    y: float
    z: float


class QuaternionInput(BaseModel):
    x: float
    y: float
    z: float
    w: float


class Pose3DInput(BaseModel):
    position: Point3DInput
    orientation: QuaternionInput


class Pose3DStampedInput(BaseModel):
    timestamp: int
    frameID: str
    position: Point3DInput
    orientation: QuaternionInput


class PointOfInterestTypeEnum(str, Enum):
    MANOMETER: str = "MANOMETER"
    FIRE_EXTINGUISHER: str = "FIRE_EXTINGUISHER"
    GENERIC: str = "GENERIC"


class PointOfInterestActionPhotoInput(BaseModel):
    robotPose: Pose3DInput
    sensor: str


class PointOfInterestActionVideoInput(BaseModel):
    robotPose: Pose3DInput
    sensor: str
    duration: float


class AddPointOfInterestInput(BaseModel):
    name: str
    site: str
    frame: str
    type: PointOfInterestTypeEnum = Field(default=PointOfInterestTypeEnum.GENERIC)
    pose: Pose3DInput
    photoAction: Optional[PointOfInterestActionPhotoInput] = None
    videoAction: Optional[PointOfInterestActionVideoInput] = None


class RobotTypeEnum(str, Enum):
    SPOT: str = "SPOT"
    EXR2: str = "EXR2"
    ROVER: str = "ROVER"
    DJI_DRONE: str = "DJI_DRONE"


class PointOfInterestProducerTypeEnum(str, Enum):
    ROBOT_TEACHING: str = "ROBOT_TEACHING"
    VISUAL_MARKER: str = "VISUAL_MARKER"
    MANUAL_IMPORT: str = "MANUAL_IMPORT"


class PointOfInterestProducerInput(BaseModel):
    type: PointOfInterestProducerTypeEnum = Field(
        default=PointOfInterestProducerTypeEnum.MANUAL_IMPORT
    )
    robotNumber: int
    robotType: RobotTypeEnum = Field(default=RobotTypeEnum.EXR2)


class UpsertPointOfInterestInput(BaseModel):
    key: str
    name: str
    type: PointOfInterestTypeEnum = Field(default=PointOfInterestTypeEnum.GENERIC)
    siteId: str
    pose: Pose3DStampedInput
    producer: PointOfInterestProducerInput
    inspectionParameters: dict
