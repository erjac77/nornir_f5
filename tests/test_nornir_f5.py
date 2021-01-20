import re

from nornir.core.task import Result, Task

import responses
from nornir_f5 import __version__
from nornir_f5.plugins.connections import CONNECTION_NAME, f5_rest_client
from tests.conftest import assert_result


def test_version():
    assert __version__ == "0.1.0"


@responses.activate
def test_connection(nornir):
    def get_toc(task: Task) -> Result:
        f5_rest_client(task).get(
            f"https://{task.host.hostname}:{task.host.port}/mgmt/toc"
        )
        f5_rest_client(task).get(
            f"https://{task.host.hostname}:{task.host.port}/mgmt/tm/ltm/virtual",
            timeout=2,
        )
        task.host.close_connection(CONNECTION_NAME)
        return {}

    # Register mock responses
    responses.add(
        responses.GET,
        re.compile("https://bigip(1|2).localhost:443/mgmt/toc"),
        json={},
        status=200,
    )
    responses.add(
        responses.GET,
        re.compile("https://bigip(1|2).localhost:443/mgmt/tm/ltm/virtual"),
        json={},
        status=200,
    )

    # Run task
    result = nornir.run(task=get_toc)

    # Assert result
    assert_result(result, {"result": {}, "failed": False})
