"""Nornir F5 connection plugin.

Allows to interact with F5 devices.
"""

from typing import Any, Dict, Optional

import requests
import urllib3
from nornir.core import Task
from nornir.core.configuration import Config
from requests import Response
from requests.adapters import HTTPAdapter
from requests_toolbelt.utils import dump
from urllib3.util import Retry

urllib3.disable_warnings()

CONNECTION_NAME = "f5"
DEFAULT_RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
DEFAULT_TIMEOUT = 5  # seconds
LOGIN_URI = "/mgmt/shared/authn/login"
LOGOUT_URI = "/mgmt/shared/authz/tokens"


class _TimeoutHTTPAdapter(HTTPAdapter):
    """Custom `Transport Adapter` with a default timeout.

    This class allows to set a default timeout for all HTTP calls.
    """

    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs) -> Response:
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


def _assert_status_hook(response: Response, *args, **kwargs) -> None:
    response.raise_for_status()


def _logging_hook(response: Response, *args, **kwargs) -> None:
    data = dump.dump_all(response)
    print(data.decode("utf-8"))


class F5RestClient:
    """Connection plugin for F5 BIG-IP systems.

    This plugin allows to make calls to an F5 REST server.

    Authentication is handled automatically.
    """

    def open(  # noqa A003
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        """Gets a token and opens the connection.

        Uses a custom `Transport Adapter` to provide default timeout and retry strategy.

        Args:
            hostname (Optional[str]): The hostname of the device.
            username (Optional[str]): The username used to access the device.
            password (Optional[str]): The password used to access the device.
            port (Optional[int]): The service port.
            platform (Optional[str]): The device family platform.
            extras (Optional[Dict[str, Any]): The extra variables.
            configuration (Optional[Config]): The configuration.
        """
        connection = requests.Session()
        connection.verify = extras.get("validate_certs", False)

        hooks = [_assert_status_hook]
        if extras.get("debug"):
            hooks.append(_logging_hook)
        connection.hooks["response"] = hooks

        kwargs = {
            "max_retries": DEFAULT_RETRY_STRATEGY,
            "timeout": extras.get("timeout", None),
        }
        adapter = _TimeoutHTTPAdapter(
            **{k: v for k, v in kwargs.items() if v is not None}
        )
        connection.mount("https://", adapter)
        connection.mount("http://", adapter)

        # Set the host. This is used by the close method to delete the token.
        self.host = f"{hostname}:{port}"

        data = {
            "username": username,
            "password": password,
            "loginProviderName": extras.get("login_provider_name", "tmos"),
        }
        resp = connection.post(f"https://{self.host}{LOGIN_URI}", json=data)
        connection.headers["X-F5-Auth-Token"] = resp.json()["token"]["token"]

        self.connection = connection

    def close(self) -> None:
        """Deletes the token and closes the connection."""
        token = self.connection.headers.get("X-F5-Auth-Token", None)
        if token:
            self.connection.delete(f"https://{self.host}{LOGOUT_URI}/{token}")
        self.connection.close()


def f5_rest_client(task: Task) -> F5RestClient:
    """Returns a REST client to interact with F5 devices.

    Args:
        task (Task): The Nornir task.

    Returns:
        F5RestClient: The F5 REST client.
    """
    return task.host.get_connection(CONNECTION_NAME, task.nornir.config)
