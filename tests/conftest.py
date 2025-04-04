import json
import re

import pytest
from nornir import InitNornir
from nornir.core.task import AggregatedResult, MultiResult, Result

import responses

base_decl_dir = "./tests/declarations"
base_resp_dir = "./tests/responses"


def load_json(file: str) -> dict:
    with open(file, "r") as f:
        return json.loads(f.read())


def assert_result(result: Result, expected: dict):
    if isinstance(result, AggregatedResult):
        for _h, r in result.items():
            assert r.changed == expected.get("changed", False)
            assert r.failed == expected.get("failed", False)
            if r.exception:
                assert_result(r, expected)
            else:
                if "result_file" in expected:
                    assert r.result == load_json(expected["result_file"])
                else:
                    assert r.result == expected.get("result", {})
    elif isinstance(result, MultiResult):
        for r in result[1:]:
            if r.exception:
                assert str(r.exception) == expected.get("result", {})


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
def _login_response():
    responses.add(
        responses.POST,
        re.compile("https://bigip(1|2|3).localhost:443/mgmt/shared/authn/login"),
        json=load_json(f"{base_resp_dir}/bigip/shared/authn/login_success.json"),
        status=200,
    )


@pytest.fixture(autouse=True)
def _tokens_response():
    responses.add(
        responses.DELETE,
        re.compile("https://bigip(1|2|3).localhost:443/mgmt/shared/authz/tokens"),
        json={},
        status=200,
    )
    responses.add(
        responses.PATCH,
        re.compile("https://bigip(1|2|3).localhost:443/mgmt/shared/authz/tokens"),
        json={},
        status=200,
    )
