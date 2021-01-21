"""Nornir F5 ATC tasks.

Allows to deploy F5 Automation Tool Chain (ATC) declaration (AS3, DO, TS)
on BIG-IP systems.

Todo:
    * Device
    * Telemetry
"""

import json

# import subprocess
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
    # "Device": {
    #     "endpoints": {
    #         "configure": {
    #             "uri": "/mgmt/shared/declarative-onboarding",
    #             "methods": ["GET", "POST"],
    #         },
    #         "info": {
    #             "uri": "/mgmt/shared/declarative-onboarding/info",
    #             "methods": ["GET"],
    #         },
    #     }
    # },
    # "Telemetry": {
    #     "endpoints": {
    #         "configure": {
    #             "uri": "/mgmt/shared/telemetry/declare",
    #             "methods": ["GET", "POST"],
    #         },
    #         "info": {"uri": "/mgmt/shared/telemetry/info", "methods": ["GET"]},
    #     }
    # },
}
ATC_SERVICE_OPTIONS = ["AS3"]  # , "Device", "Telemetry"]


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


def _declare(
    atc_config_endpoint: str,
    atc_declaration: str,
    atc_method: str,
    atc_service: str,
    task: Task,
) -> dict:
    url = f"https://{task.host.hostname}:{task.host.port}{atc_config_endpoint}"

    # AS3
    if atc_service == "AS3" and atc_method in ["POST", "DELETE"]:
        if atc_method == "POST":
            resp = f5_rest_client(task).post(url, json=atc_declaration)
        if atc_method == "DELETE":
            resp = f5_rest_client(task).delete(url)

        message = resp.json()["results"][0]["message"]
        if message != "Declaration successfully submitted":
            raise Exception("Declaration failed.")

    # GET
    if atc_method == "GET":
        resp = f5_rest_client(task).get(url)

    return resp.json()


def _check_task_bigip(
    atc_method: str,
    atc_service: str,
    atc_task_endpoint: str,
    atc_task_id: str,
    task: Task,
    atc_delay: int = 10,
    atc_retries: int = 30,
    retry: int = 0,
) -> dict:
    # AS3
    # if atc_service == "AS3" and atc_method in ["POST", "DELETE"]:
    resp = f5_rest_client(task).get(
        f"https://{task.host.name}:{task.host.port}{atc_task_endpoint}/{atc_task_id}"
    )
    message = resp.json()["results"][0]["message"]

    if message in ["in progress"]:
        if retry < atc_retries:
            time.sleep(atc_delay)
            retry += 1
            return _check_task_bigip(
                atc_delay=atc_delay,
                atc_method=atc_method,
                atc_retries=atc_retries,
                atc_service=atc_service,
                atc_task_endpoint=atc_task_endpoint,
                atc_task_id=atc_task_id,
                retry=retry,
                task=task,
            )
        else:
            raise Exception("The declaration deployment has reached maximum retries.")
    else:
        if message in ["success", "no change"]:
            return resp.json()
        raise Exception("Declaration failed.")


# def check_rpm_tool(task: Task) -> Result:
#     command = ["rpm", "--version", "warn=False"]
#     sp = subprocess.Popen(command)
#     sp.wait()

#     if sp.returncode == 0:
#         return Result(host=task.host, result="RPM is installed.")
#     else:
#         raise Exception("RPM is not installed!")


def f5_deploy_atc(
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
    if (
        atc_method
        not in ATC_COMPONENTS[atc_service]["endpoints"]["configure"]["methods"]
    ):
        raise Exception(f"ATC method '{atc_method}' is not valid.")

    # Set ATC endpoints
    atc_config_endpoint = ATC_COMPONENTS[atc_service]["endpoints"]["configure"]["uri"]
    atc_info_endpoint = ATC_COMPONENTS[atc_service]["endpoints"]["info"]["uri"]
    atc_task_endpoint = ATC_COMPONENTS[atc_service]["endpoints"]["task"]["uri"]

    # Verify ATC service is available, and collect service info
    atc_service_info = (
        f5_rest_client(task)
        .get(f"https://{task.host.hostname}:{task.host.port}{atc_info_endpoint}")
        .json()
    )

    # Build AS3 endpoint
    # if atc_service == "AS3":
    atc_config_endpoint = _build_as3_endpoint(
        as3_tenant=as3_tenant,
        as3_version=atc_service_info["version"],
        as3_show=as3_show,
        as3_show_hash=as3_show_hash,
        atc_config_endpoint=atc_config_endpoint,
        atc_method=atc_method,
    )

    # Send the declaration
    atc_declare_resp = _declare(
        atc_config_endpoint=atc_config_endpoint,
        atc_declaration=atc_declaration,
        atc_method=atc_method,
        atc_service=atc_service,
        task=task,
    )

    # If 'atc_method' is 'GET', return the declaration
    if atc_method == "GET":
        return Result(host=task.host, result=atc_declare_resp)

    # Wait for task to complete
    atc_task_resp = _check_task_bigip(
        atc_delay=atc_delay,
        atc_method=atc_method,
        atc_retries=atc_retries,
        atc_service=atc_service,
        atc_task_endpoint=atc_task_endpoint,
        atc_task_id=atc_declare_resp["id"],
        task=task,
    )

    if atc_task_resp["results"][0]["message"] == "no change":
        return Result(host=task.host, result=atc_task_resp)
    return Result(host=task.host, changed=True, result=atc_task_resp)
