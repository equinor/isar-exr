import importlib.resources as pkg_resources
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    def __init__(self) -> None:
        try:
            with pkg_resources.path(f"isar_exr.config", "settings.env") as path:
                env_file_path = path
        except ModuleNotFoundError:
            env_file_path = None
        super().__init__(_env_file=env_file_path)

    # The ID of the robot in the EXR database
    ROBOT_EXR_ID: str = Field(default="61a09ebc5f71911c10b463ce")

    # The ID of the docking station in the EXR database
    DOCKING_STATION_ID: str = Field(default="65153c6893a0ba5b7b487b6e")

    # The ID of the relevant site in the EXR database (default=KAA)
    ROBOT_EXR_SITE_ID: str = Field(default="61a0a1f45f71913ebbb4657d")

    # Map to be used for creation of alitra transformation
    MAP: str = Field(default="exr_klab_sst")

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

    # API sleep time
    API_SLEEP_TIME: int = Field(default=1)

    model_config = SettingsConfigDict(
        env_prefix="EXR_",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


load_dotenv()
settings = Settings()
