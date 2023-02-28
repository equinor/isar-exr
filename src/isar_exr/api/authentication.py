import json
from typing import Any
import requests
from requests.auth import HTTPBasicAuth
from requests import Response
from isar_exr.config.settings import settings


def get_access_token() -> str:
    username: str = settings.ROBOT_API_USERNAME
    password: str = settings.ROBOT_API_PASSWORD
    auth_url: str = settings.ROBOT_AUTH_URL
    response: Response = requests.post(
        auth_url,
        auth=HTTPBasicAuth(username=username, password=password),
    )

    response.raise_for_status()

    json_object: Any = json.loads(response.content.decode("utf-8"))
    token: str = json_object["access_token"]

    return token
