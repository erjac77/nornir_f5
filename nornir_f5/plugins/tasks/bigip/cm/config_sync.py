"""Nornir F5 Configuration Synchronization tasks."""

import logging
import time

from nornir.core.task import Result, Task

from nornir_f5.plugins.connections import f5_rest_client
from nornir_f5.plugins.tasks.bigip.cm.sync_status import bigip_cm_sync_status

SYNC_DIRECTION_OPTIONS = ["to-group", "from-group"]


def bigip_cm_config_sync(
    task: Task,
    device_group: str,
    delay: int = 6,
    direction: str = "to-group",
    force_full_load_push: bool = False,
    retries: int = 50,
) -> Result:
    """Task to synchronize the configuration between devices.

    Args:
        task (Task): The Nornir task.
        device_group (str): The device group on which to perform the config-sync action.
        delay (int): The delay (in seconds) between retries when checking
            if the sync-config is complete.
        direction (str): The direction when performing the config-sync action.
            Accepted values include [to-group, from-group].
            `from-group` updates the configuration of the local device with the
            configuration of the remote device in the specified device group that has
            the newest configuration.
            `to-group` updates the configurations of the remote devices in the specified
            device group with the configuration of the local device.
        force_full_load_push (bool): It forces all other devices to pull
            all synchronizable configuration from this device.
        retries (int): The number of times the task will check for a finished
            config-sync action before failing.

    Returns:
        Result: The result of the config-sync action.

    Raises:
        Exception: The raised exception when the task had an error.
    """
    sync_status = task.run(
        name="Get the sync status",
        task=bigip_cm_sync_status,
        severity_level=logging.DEBUG,
    ).result

    if direction not in SYNC_DIRECTION_OPTIONS:
        raise Exception(f"Direction '{direction}' is not valid.")

    if sync_status not in ["In Sync", "Standalone"]:
        data = {
            "command": "run",
            "utilCmdArgs": f"config-sync {direction} {device_group}{' force-full-load-push' if force_full_load_push else ''}",  # noqa B950
        }
        f5_rest_client(task).post(
            f"https://{task.host.hostname}:{task.host.port}/mgmt/tm/cm", json=data
        )

        for retry in range(1, retries + 1):
            time.sleep(delay)
            sync_status = task.run(
                name=f"Get the sync status (attempt {retry}/{retries})",
                task=bigip_cm_sync_status,
                severity_level=logging.DEBUG,
            ).result

            if sync_status == "Changes Pending":
                # TODO: Validate pending state (yellow or red)
                pass
            elif sync_status in [
                "Awaiting Initial Sync",
                "Not All Devices Synced",
                "Syncing",
            ]:
                pass
            elif sync_status == "In Sync":
                return Result(host=task.host, result=sync_status, changed=True)
            else:
                raise Exception(
                    f"The configuration synchronization has failed ({sync_status})."
                )

        raise Exception(
            f"The configuration synchronization has reached maximum retries ({sync_status})."  # noqa B950
        )

    return Result(host=task.host, result=sync_status)
