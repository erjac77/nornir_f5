import json
import os

import pytest

import responses
from nornir_f5.plugins.tasks import (
    f5_bigip_shared_file_transfer_uploads,
    f5_bigip_shared_iapp_lx_package,
)

from .conftest import assert_result, base_resp_dir, load_json


@pytest.mark.parametrize(
    ("kwargs", "resp", "expected"),
    [
        (
            {"local_file_path": "./tests/files/myfile.txt"},
            {"status_code": 200},
            {"result": "The file was uploaded successfully.", "changed": True},
        ),
        (
            {
                "local_file_path": "./tests/files/myfile.txt",
                "destination_file_name": "yourfile.txt",
            },
            {"status_code": 200},
            {"result": "The file was uploaded successfully.", "changed": True},
        ),
        (
            {"local_file_path": "./tests/files/myfile1.txt"},
            {"status_code": 200},
            {
                "result": "[Errno 2] No such file or directory: './tests/files/myfile1.txt'",  # noqa B950
                "failed": True,
            },
        ),
        (
            {"local_file_path": "./tests/files/myfile.txt"},
            {"status_code": 500},
            {
                "result": "500 Server Error: Internal Server Error for url: https://bigip1.localhost:443/mgmt/shared/file-transfer/uploads/myfile.txt",  # noqa B950
                "failed": True,
            },
        ),
    ],
)
@responses.activate
def test_upload_file(nornir, kwargs, resp, expected):
    if "destination_file_name" in kwargs:
        file_name = kwargs["destination_file_name"]
    else:
        file_name = os.path.basename(kwargs["local_file_path"])

    # Register mock responses
    responses.add(
        responses.POST,
        f"https://bigip1.localhost:443/mgmt/shared/file-transfer/uploads/{file_name}",
        content_type="application/octet-stream",
        status=resp["status_code"],
    )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(
        name="Upload file",
        task=f5_bigip_shared_file_transfer_uploads,
        **kwargs,
    )

    # Assert result
    assert_result(result, expected)


@pytest.mark.parametrize(
    ("kwargs", "version", "ls_resp", "task_resp", "task_statuses", "expected"),
    [
        (
            {"package": "./tests/files/mypackage.rpm"},
            "13.1.1.4",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_found.json",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/shared/iapp/task_created.json",
            },
            ["CREATED", "STARTED", "FINISHED"],
            {"result": "The LX package was successfully installed.", "changed": True},
        ),
        (
            {"package": "./tests/files/mypackage.rpm", "retain_package_file": True},
            "13.1.1.4",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_found.json",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/shared/iapp/task_created.json",
            },
            ["CREATED", "STARTED", "FINISHED"],
            {"result": "The LX package was successfully installed.", "changed": True},
        ),
        (
            {"package": "./tests/files/mypackage.rpm"},
            "13.1.1.4",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_not_found.json",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/shared/iapp/task_created.json",
            },
            ["CREATED", "STARTED", "FINISHED"],
            {"result": "The LX package was successfully installed.", "changed": True},
        ),
        (
            {"package": "./tests/files/mypackage.rpm"},
            "11.6.5.2",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_found.json",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/shared/iapp/task_created.json",
            },
            [],
            {"result": "BIG-IP version '11.6.5.2' is not supported.", "failed": True},
        ),
        (
            {"package": "mypackage.rpm", "state": "absent"},
            "13.1.1.4",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_found.json",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/shared/iapp/task_created.json",
            },
            ["CREATED", "STARTED", "FINISHED"],
            {"result": "The LX package was successfully uninstalled.", "changed": True},
        ),
        (
            {"package": "./tests/files/mypackage.rpm"},
            "13.1.1.4",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_found.json",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/shared/iapp/task_created.json",
            },
            ["CREATED", "STARTED", "FAILED"],
            {"result": "Package x version x.y.z is already installed.", "failed": True},
        ),
        (
            {"package": "./tests/files/mypackage.rpm"},
            "13.1.1.4",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_found.json",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/shared/iapp/task_created.json",
            },
            ["CREATED", "STARTED", "UNKNOWN"],
            {"result": "The task failed.", "failed": True},
        ),
        (
            {"package": "./tests/files/mypackage.rpm"},
            "13.1.1.4",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_found.json",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/shared/iapp/task_created.json",
            },
            ["CREATED", "STARTED"],
            {"result": "The task has reached maximum retries.", "failed": True},
        ),
    ],
)
@responses.activate
def test_lx_package(
    nornir, kwargs, version, ls_resp, task_resp, task_statuses, expected
):
    package_name = os.path.basename(kwargs["package"])
    task_id = "5eb601c4-7f06-4fd7-b8d5-947e7b206a38"

    # Callback to provide dynamic task status responses
    def get_task_callback(request):
        calls = [
            d
            for d in responses.calls
            if f"/mgmt/shared/iapp/package-management-tasks/{task_id}" in d.request.url
        ]

        if len(calls) == 0:
            current_task_status = task_statuses[0]
        elif len(calls) < len(task_statuses):
            current_task_status = task_statuses[len(calls)]
        else:
            current_task_status = task_statuses[len(task_statuses) - 1]

        return (
            200,
            {},
            json.dumps(
                load_json(
                    f"{base_resp_dir}/bigip/shared/iapp/task_{current_task_status.lower()}.json"  # noqa B950
                )
            ),
        )

    # Register mock responses
    responses.add(
        responses.GET,
        "https://bigip1.localhost:443/mgmt/tm/sys/version",
        json=load_json(f"{base_resp_dir}/bigip/sys/version_{version}.json"),
        status=200,
    )
    responses.add(
        responses.POST,
        "https://bigip1.localhost:443/mgmt/tm/util/unix-ls",
        json=load_json(ls_resp["data"]),
        status=ls_resp["status_code"],
    )
    responses.add(
        responses.POST,
        f"https://bigip1.localhost:443/mgmt/shared/file-transfer/uploads/{package_name}",  # noqa B950
        content_type="application/octet-stream",
        status=200,
    )
    responses.add(
        responses.POST,
        "https://bigip1.localhost:443/mgmt/shared/iapp/package-management-tasks",
        json=load_json(task_resp["data"]),
        status=task_resp["status_code"],
    )
    responses.add_callback(
        responses.GET,
        f"https://bigip1.localhost:443/mgmt/shared/iapp/package-management-tasks/{task_id}",  # noqa B950
        callback=get_task_callback,
    )
    responses.add(
        responses.POST,
        "https://bigip1.localhost:443/mgmt/tm/util/unix-rm",
        json={},
        status=200,
    )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(
        name="Manage LX package",
        task=f5_bigip_shared_iapp_lx_package,
        delay=0,
        retries=3,
        **kwargs,
    )

    # Assert result
    assert_result(result, expected)
