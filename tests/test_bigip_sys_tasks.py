import pytest

import responses
from nornir_f5.plugins.tasks import bigip_sys_version

from .conftest import assert_result, base_resp_dir, load_json


@pytest.mark.parametrize(
    ("resp", "expected"),
    [
        (
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/sys/version_13.1.1.4.json",
            },
            {"result": "13.1.1.4"},
        ),
    ],
)
@responses.activate
def test_get_version(nornir, resp, expected):
    # Register mock responses
    responses.add(
        responses.GET,
        "https://bigip1.localhost:443/mgmt/tm/sys/version",
        json=load_json(resp["data"]),
        status=resp["status_code"],
    )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(name="Systen version GET", task=bigip_sys_version)

    # Assert result
    assert_result(result, expected)
