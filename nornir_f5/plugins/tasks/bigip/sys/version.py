"""Nornir F5 Version tasks."""

from nornir.core.task import Result, Task

from nornir_f5.plugins.connections import f5_rest_client


def bigip_sys_version(task: Task) -> Result:
    """Gets the system version of the BIG-IP.

    Args:
        task: (Task): The Nornir task.

    Returns:
        Result: The system version of the BIG-IP.
    """
    resp = f5_rest_client(task).get(
        f"https://{task.host.hostname}:{task.host.port}/mgmt/tm/sys/version"
    )
    return resp.json()["entries"]["https://localhost/mgmt/tm/sys/version/0"][
        "nestedStats"
    ]["entries"]["Version"]["description"]
