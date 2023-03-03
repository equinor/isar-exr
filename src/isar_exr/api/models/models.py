from pydantic import BaseModel
from enum import Enum


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


class PointOfInterestTypeEnum(BaseModel, Enum):
    MANOMETER: str
    FIRE_EXTINGUISHER: str
    GENERIC: str


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
    type: PointOfInterestTypeEnum
    pose: Pose3DInput
    photoAction: PointOfInterestActionPhotoInput
    videoAction: PointOfInterestActionVideoInput
