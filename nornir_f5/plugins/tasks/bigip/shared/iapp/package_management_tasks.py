"""Nornir F5 Package Management tasks."""
import os
import time

from nornir.core.task import Result, Task
from packaging.version import Version

from nornir_f5.plugins.connections import f5_rest_client
from nornir_f5.plugins.tasks.bigip.shared.file_transfer.uploads import (
    FILE_TRANSFER_OPTIONS,
    bigip_shared_file_transfer_uploads,
)
from nornir_f5.plugins.tasks.bigip.sys.version import bigip_sys_version
from nornir_f5.plugins.tasks.bigip.util.unix_ls import bigip_util_unix_ls
from nornir_f5.plugins.tasks.bigip.util.unix_rm import bigip_util_unix_rm


def _wait_task(
    task: Task,
    task_id: str,
    delay: int = 3,
    retries: int = 60,
) -> Result:
    client = f5_rest_client(task)
    host = f"{task.host.hostname}:{task.host.port}"

    for _i in range(0, retries):
        task_resp = client.get(
            f"https://{host}/mgmt/shared/iapp/package-management-tasks/{task_id}"
        )
        task_status = task_resp.json()["status"]
        print("*** task_status", task_status)
        if task_status in ["CREATED", "STARTED"]:
            pass
        elif task_status == "FINISHED":
            return Result(host=task.host, changed=True, result=task_status)
        elif task_status == "FAILED":
            raise Exception(task_resp.json()["errorMessage"])
        else:
            raise Exception("The task failed.")
        time.sleep(delay)

    raise Exception("The task has reached maximum retries.")


def bigip_shared_iapp_lx_package(
    task: Task,
    package: str,
    delay: int = 3,
    retain_package_file: bool = False,
    retries: int = 60,
    state: str = "present",
) -> Result:
    """Task to manage Javascript LX packages on a BIG-IP.

    Args:
        task (Task): The Nornir task.
        delay (int): The delay (in seconds) between retries
            when checking if async call is complete.
        package (str): The RPM package to installed/uninstall.
        retain_package_file (bool): The flag that specifies whether the install file
            should be deleted on successful installation of the package.
        retries (int): The number of times the task will check for a finished task
            before failing.
        state (str): The state of the package.

    Returns:
        Result: The result of the task.

    Raises:
        Exception: The raised exception when the task had an error.
    """
    client = f5_rest_client(task)

    # Check if LX is supported on the BIG-IP
    version = task.run(name="Get system version", task=bigip_sys_version).result
    if Version(version) < Version("12.0.0"):
        raise Exception(f"BIG-IP version '{version}' is not supported.")

    package_name = os.path.basename(package)
    remote_package_path = f"{FILE_TRANSFER_OPTIONS['file']['directory']}/{package_name}"

    if state == "present":
        # Check if the file exists on the device
        content = task.run(
            name="List content",
            task=bigip_util_unix_ls,
            file_path=remote_package_path,
        ).result
        if "No such file or directory" in content:
            # Upload the RPM on the BIG-IP
            task.run(
                name="Upload the RPM on the BIG-IP",
                task=bigip_shared_file_transfer_uploads,
                local_file_path=package,
            )

    # Install/unistall the package
    host = f"{task.host.hostname}:{task.host.port}"
    data = {
        "operation": "INSTALL",
        "packageFilePath": remote_package_path,
    }
    if state == "absent":
        package_name = os.path.splitext(package_name)[0]
        data = {
            "operation": "UNINSTALL",
            "packageName": package_name,
        }
    task_id = client.post(
        f"https://{host}/mgmt/shared/iapp/package-management-tasks",
        json=data,
    ).json()["id"]

    # Get the task status
    task.run(
        name="Wait for task to complete",
        task=_wait_task,
        delay=delay,
        retries=retries,
        task_id=task_id,
    )

    # Absent
    if state == "absent":
        return Result(
            host=task.host,
            changed=True,
            result="The LX package was successfully uninstalled.",
        )

    # Present
    if not retain_package_file:
        task.run(
            name="Remove LX package",
            task=bigip_util_unix_rm,
            file_path=remote_package_path,
        )
    return Result(
        host=task.host,
        changed=True,
        result="The LX package was successfully installed.",
    )
