"""Nornir F5 Uploads tasks."""
import os

from nornir.core.task import Result, Task

from nornir_f5.plugins.connections import f5_rest_client

FILE_TRANSFER_OPTIONS = {
    "file": {
        "endpoints": {
            "uploads": {"uri": "/mgmt/shared/file-transfer/uploads"},
            "downloads": {"uri": "/mgmt/shared/file-transfer/uploads"},
        },
        "directory": "/var/config/rest/downloads",
    },
}


def _upload_file(
    task: Task,
    local_file_path: str,
    url: str,
    destination_file_name: str = None,
) -> Result:
    chunk_size = 1024 * 7168
    index = 0
    offset = 0

    file_size = os.stat(local_file_path).st_size

    if destination_file_name is None:
        destination_file_name = os.path.basename(local_file_path)
    url = f"{url.rstrip('/')}/{destination_file_name}"

    fb = open(local_file_path, "rb")

    while True:
        chunk = fb.read(chunk_size)
        if not chunk:
            break

        offset = index + len(chunk)
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Range": f"{index}-{offset - 1}/{file_size}",
        }
        f5_rest_client(task).post(url, data=chunk, headers=headers)

        index += offset

    return Result(host=task.host, result="The file was uploaded successfully.")


def bigip_shared_file_transfer_uploads(
    task: Task, local_file_path: str, destination_file_name: str = None
) -> Result:
    """Upload a file to a BIG-IP system using the iControl REST API.

    Args:
        task: (Task): The Nornir task.
        local_file_path (str): The full path of the file to be uploaded.
        destination_file_name (str): The name of the file to upload
            on the remote device.

    Returns:
        Result: The result of the task.
    """
    host = f"{task.host.hostname}:{task.host.port}"
    uri = f"{FILE_TRANSFER_OPTIONS['file']['endpoints']['uploads']['uri']}"
    task.run(
        name="Upload the file",
        task=_upload_file,
        destination_file_name=destination_file_name,
        local_file_path=local_file_path,
        url=f"https://{host}{uri}",
    )

    return Result(
        host=task.host, changed=True, result="The file was uploaded successfully."
    )
