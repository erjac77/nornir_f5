import json
import re

import pytest
from nornir import InitNornir
from nornir.core.task import Result

import responses

base_decl_dir = "./tests/declarations"
base_resp_dir = "./tests/responses"


def load_json(file: str) -> dict:
    with open(file, "r") as f:
        return json.loads(f.read())


def assert_result(result: Result, expected: dict):
    for _h, r in result.items():
        if r.exception:
            assert str(r.exception) == expected["result"]
        else:
            if "result_file" in expected:
                assert r.result == load_json(expected["result_file"])
            else:
                assert r.result == expected["result"]
        assert r.changed == expected.get("changed", False)
        assert r.failed == expected.get("failed", False)


# Nornir


@pytest.fixture(scope="session", autouse=True)
def nornir():
    return InitNornir(config_file="tests/config.yml")


@pytest.fixture(autouse=True)
def _reset_data(nornir):
    # Reset all failed host for next test
    nornir.data.reset_failed_hosts()


# AUTHN


@pytest.fixture(autouse=True)
def _login_responses():
    responses.add(
        responses.POST,
        re.compile("https://bigip(1|2).localhost:443/mgmt/shared/authn/login"),
        json=load_json(f"{base_resp_dir}/bigip/shared/authn/login_success.json"),
        status=200,
    )
