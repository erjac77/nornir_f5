"""Nornir F5 Automation Toolchain (ATC) tasks.

Allows to deploy F5 ATC declarations (AS3, DO, TS) on BIG-IP systems.

Todo:
    * Telemetry
"""

import json
import time
from urllib.parse import urlencode

from nornir.core.task import Result, Task
from packaging import version

from nornir_f5.plugins.connections import f5_rest_client

AS3_SHOW_OPTIONS = ["base", "full", "expanded"]
ATC_COMPONENTS = {
    "AS3": {
        "endpoints": {
            "configure": {
                "uri": "/mgmt/shared/appsvcs/declare",
                "methods": ["GET", "POST", "DELETE"],
            },
            "info": {"uri": "/mgmt/shared/appsvcs/info", "methods": ["GET"]},
            "task": {"uri": "/mgmt/shared/appsvcs/task", "methods": ["GET"]},
        },
    },
    "Device": {
        "endpoints": {
            "configure": {
                "uri": "/mgmt/shared/declarative-onboarding",
                "methods": ["GET", "POST"],
            },
            "info": {
                "uri": "/mgmt/shared/declarative-onboarding/info",
                "methods": ["GET"],
            },
            "task": {
                "uri": "/mgmt/shared/declarative-onboarding/task",
                "methods": ["GET"],
            },
        }
    },
    "Telemetry": {
        "endpoints": {
            "configure": {
                "uri": "/mgmt/shared/telemetry/declare",
                "methods": ["GET", "POST"],
            },
            "info": {"uri": "/mgmt/shared/telemetry/info", "methods": ["GET"]},
        }
    },
}
ATC_SERVICE_OPTIONS = ["AS3", "Device", "Telemetry"]


def _build_as3_endpoint(
    atc_config_endpoint: str,
    atc_method: str,
    as3_version: str,
    as3_show: str = "",
    as3_show_hash: bool = False,
    as3_tenant: str = "",
) -> str:
    # Setup AS3 endpoint with specified tenant when tenant specified
    if as3_tenant and (
        version.parse(as3_version) >= version.parse("3.14.0") or atc_method == "DELETE"
    ):
        atc_config_endpoint = f"{atc_config_endpoint}/{as3_tenant}"

    params = {}

    # Setup URL query 'show' when using GET, POST, or DELETE with AS3
    if (
        as3_show
        and version.parse(as3_version) >= version.parse("3.6.0")
        and as3_show in AS3_SHOW_OPTIONS
    ):
        params.update({"show": as3_show})

    # Setup optional URL query 'showHash' when using POST with AS3
    if (
        version.parse(as3_version) >= version.parse("3.14.0")
        and as3_show_hash
        and atc_method in ["POST", "GET"]
    ):
        params.update({"showHash": "true"})

    # Setup URL query 'async' when using POST with AS3
    if version.parse(as3_version) >= version.parse("3.5.0") and atc_method in [
        "POST",
        "DELETE",
    ]:
        params.update({"async": "true"})

    if params:
        atc_config_endpoint = f"{atc_config_endpoint}?{urlencode(params)}"

    return atc_config_endpoint


def _send(
    task: Task,
    atc_config_endpoint: str,
    atc_method: str,
    atc_service: str,
    atc_declaration: str,
) -> Result:
    client = f5_rest_client(task)
    host = f"{task.host.hostname}:{task.host.port}"
    url = f"https://{host}{atc_config_endpoint}"

    # AS3
    if atc_service == "AS3" and atc_method in ["POST", "DELETE"]:
        if atc_method == "POST":
            resp = client.post(url, json=atc_declaration)
        if atc_method == "DELETE":
            resp = client.delete(url)

        message = resp.json()["results"][0]["message"]
        if message != "Declaration successfully submitted":
            raise Exception("The declaration deployment failed.")

    # Device
    if atc_service == "Device" and atc_method == "POST":
        resp = client.post(url, json=atc_declaration)

    # Telemetry
    if atc_service == "Telemetry" and atc_method == "POST":
        resp = client.post(url, json=atc_declaration)

        message = resp.json()["message"]
        if message != "success":
            raise Exception("The declaration deployment failed.")

    # GET
    if atc_method == "GET":
        resp = client.get(url)

    return Result(host=task.host, result=resp.json())


def _wait_task(
    task: Task,
    atc_task_endpoint: str,
    atc_task_id: str,
    atc_delay: int = 10,
    atc_retries: int = 30,
) -> Result:
    client = f5_rest_client(task)
    host = f"{task.host.hostname}:{task.host.port}"

    for _i in range(0, atc_retries):
        atc_task_resp = client.get(
            f"https://{host}{atc_task_endpoint}/{atc_task_id}"
        ).json()

        if "results" in atc_task_resp:
            message = atc_task_resp["results"][0]["message"]
        else:
            message = atc_task_resp["result"]["message"]

        if message in ["in progress", "processing"]:
            pass
        elif message == "success":
            return Result(host=task.host, changed=True, result=message)
        elif message == "no change":
            return Result(host=task.host, result=message)
        else:
            raise Exception("The task failed.")
        time.sleep(atc_delay)

    raise Exception("The task has reached maximum retries.")


def atc(
    task: Task,
    as3_show: str = "base",
    as3_show_hash: bool = False,
    as3_tenant: str = "",
    atc_declaration: str = "",
    atc_declaration_file: str = "",
    atc_declaration_url: str = "",
    atc_delay: int = 30,
    atc_method: str = "GET",
    atc_retries: int = 10,
    atc_service: str = "",
) -> Result:
    """Task to deploy declaratives on F5 devices.

    Args:
        task (Task): The Nornir task.
        as3_show (str): The AS3 `show` value.
            Accepted values include [base, full, expanded].
            `base` means system returns the declaration as originally deployed
            (but with secrets like passphrases encrypted).
            `full` returns the declaration with all default schema properties populated.
            `expanded` includes all URLs, base64s, and other references expanded to
            their final static values.
        as3_show_hash (bool): The AS3 `showHash` value that is used as protection
            mechanism for tenants in a declaration. If set to `True`, the result returns
            an `optimisticLockKey` for each tenant.
        as3_tenant: The AS3 tenant filter. This only updates the tenant specified,
            even if there are other tenants in the declaration.
        atc_declaration (str): The ATC declaration.
            Mutually exclusive with `atc_declaration_file` and `atc_declaration_url`.
        atc_declaration_file (str): The path of the ATC declaration.
            Mutually exclusive with `atc_declaration` and `atc_declaration_url`.
        atc_declaration_url (str): The URL of the ATC declaration.
            Mutually exclusive with `atc_declaration` and `atc_declaration_file`.
        atc_delay (int): The delay (in seconds) between retries
            when checking if async call is complete.
        atc_method (str): The HTTP method. Accepted values include [POST, GET]
            for all services, and [DELETE] for AS3.
        atc_retries (int): The number of times the task will check for a finished task
            before failing.
        atc_service (str): The ATC service.
            Accepted values include [AS3, Device, Telemetry].
            If not provided, this will auto select from the declaration.

    Returns:
        Result: The result.

    Raises:
        Exception: The raised exception when the task had an error.
    """
    # Get ATC declaration from file
    if atc_declaration_file:
        with open(atc_declaration_file, "r") as f:
            atc_declaration = json.loads(f.read())
    # Get ATC declaration from url
    if atc_declaration_url:
        atc_declaration = f5_rest_client(task).get(atc_declaration_url).json()

    # Get ATC service from declaration
    if atc_declaration and not atc_service:
        atc_service = atc_declaration["class"]
    # Validate ATC service
    if atc_service not in ATC_SERVICE_OPTIONS:
        raise Exception(f"ATC service '{atc_service}' is not valid.")

    # Validate ATC method
    atc_methods = ATC_COMPONENTS[atc_service]["endpoints"]["configure"]["methods"]
    if atc_method not in atc_methods:
        raise Exception(f"ATC method '{atc_method}' is not valid.")

    # Set host
    host = f"{task.host.hostname}:{task.host.port}"

    # Verify ATC service is available, and collect service info
    atc_service_info = (
        f5_rest_client(task)
        .get(f"https://{host}{ATC_COMPONENTS[atc_service]['endpoints']['info']['uri']}")
        .json()
    )

    # Set ATC config endpoint
    atc_config_endpoint = ATC_COMPONENTS[atc_service]["endpoints"]["configure"]["uri"]

    # Build AS3 endpoint
    if atc_service == "AS3":
        atc_config_endpoint = _build_as3_endpoint(
            as3_tenant=as3_tenant,
            as3_version=atc_service_info["version"],
            as3_show=as3_show,
            as3_show_hash=as3_show_hash,
            atc_config_endpoint=atc_config_endpoint,
            atc_method=atc_method,
        )

    # Send the declaration
    atc_send_result = task.run(
        name=f"{atc_method} the declaration",
        task=_send,
        atc_config_endpoint=atc_config_endpoint,
        atc_declaration=atc_declaration,
        atc_method=atc_method,
        atc_service=atc_service,
    ).result

    # If 'Telemetry' or 'GET', return the declaration
    if atc_service == "Telemetry" or atc_method == "GET":
        return Result(host=task.host, result=atc_send_result)

    # Wait for task to complete
    task_result = task.run(
        name="Wait for task to complete",
        task=_wait_task,
        atc_delay=atc_delay,
        atc_retries=atc_retries,
        atc_task_endpoint=ATC_COMPONENTS[atc_service]["endpoints"]["task"]["uri"],
        atc_task_id=atc_send_result["id"],
    ).result

    if task_result == "no change":
        return Result(
            host=task.host,
            result="ATC declaration successfully submitted, but no change required.",
        )

    return Result(
        host=task.host, changed=True, result="ATC declaration successfully deployed."
    )
