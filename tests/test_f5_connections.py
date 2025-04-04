import re

from nornir.core.task import Result, Task

import responses
from nornir_f5.plugins.connections import CONNECTION_NAME, f5_rest_client

from .conftest import assert_result


@responses.activate
def test_connection(nornir):
    def test_conn(task: Task) -> Result:
        f5_rest_client(task).get(
            f"https://{task.host.hostname}:{task.host.port}/mgmt/toc"
        )
        f5_rest_client(task).get(
            f"https://{task.host.hostname}:{task.host.port}/mgmt/toc", timeout=2
        )
        task.host.close_connection(CONNECTION_NAME)
        return {}

    # Register mock responses
    responses.add(
        responses.GET,
        re.compile("https://bigip(1|2|3).localhost:443/mgmt/toc"),
        json={},
        status=200,
    )

    # Run task
    result = nornir.run(task=test_conn)

    # Assert result
    assert_result(result, {})


@responses.activate
def test_close_connection(nornir):
    def test_close_conn(task: Task) -> Result:
        task.host.get_connection(CONNECTION_NAME, task.nornir.config)
        task.host.close_connection(CONNECTION_NAME)
        return {}

    # Run task
    result = nornir.run(task=test_close_conn)

    # Assert result
    assert_result(result, {})
