import pytest

import responses
from nornir_f5.plugins.tasks import bigip_util_unix_ls, bigip_util_unix_rm

from .conftest import assert_result, base_resp_dir, load_json


@pytest.mark.parametrize(
    ("file", "resp", "expected"),
    [
        (
            "mypackage.rpm",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_found.json",
            },
            {"result": ["mypackage.rpm"]},
        ),
        (
            "mypackage.rpm",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_not_found.json",
            },
            {"result": "No such file or directory"},
        ),
        (
            "mypackage.rpm",
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/util/list_error.json",
            },
            {"result": "Error while excuting the command.", "failed": True},
        ),
    ],
)
@responses.activate
def test_list_files(nornir, file, resp, expected):
    # Register mock responses
    responses.add(
        responses.POST,
        "https://bigip1.localhost:443/mgmt/tm/util/unix-ls",
        json=load_json(resp["data"]),
        status=resp["status_code"],
    )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(name="List files", task=bigip_util_unix_ls, file_path=file)

    # Assert result
    assert_result(result, expected)


@pytest.mark.parametrize(
    ("kwargs", "resp", "expected"),
    [
        (
            {"file_path": "mypackage.rpm"},
            {"status_code": 200},
            {"result": "The file was successfully deleted.", "changed": True},
        ),
        # Dry-run
        (
            {"file_path": "mypackage.rpm", "dry_run": True},
            {"status_code": 200},
            {"result": None, "changed": False},
        ),
    ],
)
@responses.activate
def test_remove_file(nornir, kwargs, resp, expected):
    # Register mock responses
    responses.add(
        responses.POST,
        "https://bigip1.localhost:443/mgmt/tm/util/unix-rm",
        json={},
        status=resp["status_code"],
    )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(name="Remove file", task=bigip_util_unix_rm, **kwargs)

    # Assert result
    assert_result(result, expected)
