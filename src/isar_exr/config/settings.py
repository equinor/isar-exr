import importlib.resources as pkg_resources
from dotenv import load_dotenv
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # URL for Ex-Robotics API
    ROBOT_API_URL: str = Field(default="https://developer.energy-robotics.com/graphql/")

    # Authentication
    ROBOT_API_USERNAME: str = Field(default="example_user@email.com")
    ROBOT_API_PASSWORD: str = Field(default="example_password")
    ROBOT_AUTH_URL: str = Field(
        default="https://login.energy-robotics.com/api/loginApi"
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
