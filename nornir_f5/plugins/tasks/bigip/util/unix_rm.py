"""Nornir F5 Unix rm tasks."""

from typing import Optional

from nornir.core.task import Result, Task

from nornir_f5.plugins.connections import f5_rest_client


def bigip_util_unix_rm(
    task: Task, file_path: str, dry_run: Optional[bool] = None
) -> Result:
    """Task to delete a file from a BIG-IP system.

    Args:
        task (Task): The Nornir task.
        file_path (str): The file to be deleted.
        dry_run (Optional[bool]): Whether to apply changes or not.

    Returns:
        Result: The result of the command.
    """
    data = {"command": "run", "utilCmdArgs": file_path}

    dry_run = task.is_dry_run(dry_run)
    if dry_run:
        return Result(host=task.host, result=None)

    f5_rest_client(task).post(
        f"https://{task.host.hostname}:{task.host.port}/mgmt/tm/util/unix-rm",
        json=data,
    )

    return Result(
        host=task.host, changed=True, result="The file was successfully deleted."
    )
