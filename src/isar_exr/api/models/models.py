from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


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
    photoAction: Optional[PointOfInterestActionPhotoInput]
    videoAction: Optional[PointOfInterestActionVideoInput]
