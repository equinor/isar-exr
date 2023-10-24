import importlib.resources as pkg_resources
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # The ID of the robot in the EXR database
    ROBOT_EXR_ID: str = Field(default="628787246cc0c0205c56e88e")

    # The ID of the docking station in the EXR database
    DOCKING_STATION_ID: str = Field(default="needs_correct_id")

    # The ID of the relevant site in the EXR database (default=KAA)
    ROBOT_EXR_SITE_ID: str = Field(default="6287873b6cc0c0205c56ea58")

    # Map to be used for creation of alitra transformation
    MAP: str = Field(default="exr_default")

    # URL for Ex-Robotics API
    ROBOT_API_URL: str = Field(default="https://developer.energy-robotics.com/graphql/")

    # Maximum amount of seconds to wait for the robot to wake up after sent wakeup call
    MAX_TIME_FOR_WAKEUP: int = 120

    # Authentication
    ROBOT_API_USERNAME: str = Field(default="example_user@email.com")
    ROBOT_API_PASSWORD: str = Field(default="example_password")
    ROBOT_AUTH_URL: str = Field(
        default="https://login.energy-robotics.com/api/loginApi"
    )

    PATH_TO_GRAPHQL_SCHEMA: Path = Path(__file__).parent.joinpath(
        "../../../docs/schema.graphql"
    )

    class Config:
        with pkg_resources.path("isar_exr.config", "settings.env") as path:
            package_path = path

        env_prefix = "EXR_"
        env_file = package_path
        env_file_encoding = "utf-8"
        case_sensitive = True


load_dotenv()
settings = Settings()
