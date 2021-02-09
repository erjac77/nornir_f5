"""Nornir F5 Sync Status tasks."""

from nornir.core.task import Result, Task

from nornir_f5.plugins.connections import f5_rest_client


def bigip_cm_sync_status(task: Task) -> Result:
    """Task to get the synchronization status of the device.

    Args:
        task (Task): The Nornir task.

    Returns:
        Result: The result with the sync status.
    """
    resp = f5_rest_client(task).get(
        f"https://{task.host.hostname}:{task.host.port}/mgmt/tm/cm/sync-status",
    )
    return Result(
        host=task.host,
        result=resp.json()["entries"]["https://localhost/mgmt/tm/cm/sync-status/0"][
            "nestedStats"
        ]["entries"]["status"]["description"],
    )
