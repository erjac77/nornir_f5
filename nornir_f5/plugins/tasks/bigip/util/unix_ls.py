"""Nornir F5 Unix ls tasks."""

from nornir.core.task import Result, Task

from nornir_f5.plugins.connections import f5_rest_client


def bigip_util_unix_ls(task: Task, file_path: str) -> Result:
    """Task to list information about the FILEs.

    Args:
        task (Task): The Nornir task.
        file_path (str): The file or directory to be listed.

    Returns:
        Result: The result of the command.

    Raises:
        Exception: The raised exception when the task had an error.
    """
    data = {"command": "run", "utilCmdArgs": file_path}
    resp = (
        f5_rest_client(task)
        .post(
            f"https://{task.host.hostname}:{task.host.port}/mgmt/tm/util/unix-ls",
            json=data,
        )
        .json()
    )

    if "commandResult" in resp:
        return Result(host=task.host, result=resp["commandResult"])

    raise Exception("Error while excuting the command.")
