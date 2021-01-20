import json
import re

import pytest

import responses
from nornir_f5.plugins.tasks import f5_deploy_atc
from tests.conftest import assert_result, base_decl_dir, base_resp_dir, load_json


@pytest.mark.parametrize(
    "kwargs,resp,task_id,task_statuses,expected",
    [
        # GET declaration with show and show_hash
        (
            {
                "as3_show": "full",
                "as3_show_hash": True,
                "atc_service": "AS3",
            },
            {"status_code": 200, "data": "./tests/declarations/atc/as3/simple_01.json"},
            "",
            [""],
            {
                "result_file": "./tests/declarations/atc/as3/simple_01.json",
                "changed": False,
                "failed": False,
            },
        ),
        # GET declaration with invalid atc_service
        (
            {
                "atc_declaration": {"class": "AS2"},
                "atc_service": "AS2",
            },
            {},
            "",
            [""],
            {
                "result": "ATC service 'AS2' is not valid.",
                "changed": False,
                "failed": True,
            },
        ),
        # POST AS3 declaration without atc_service
        (
            {
                "as3_tenant": "Simple_01",
                "atc_declaration": {"class": "AS3"},
                "atc_method": "POST",
            },
            {
                "status_code": 200,
                "data": "./tests/responses/atc/as3/declaration_successfully_submitted.json",
            },
            "4eb601c4-7f06-4fd7-b8d5-947e7b206a37",
            ["in progress", "success"],
            {
                "result_file": "./tests/responses/atc/as3/task_success.json",
                "changed": True,
                "failed": False,
            },
        ),
        # POST AS3 declaration from file
        (
            {
                "as3_tenant": "Simple_01",
                "atc_declaration_file": "./tests/declarations/atc/as3/simple_01.json",
                "atc_method": "POST",
                "atc_service": "AS3",
            },
            {
                "status_code": 200,
                "data": "./tests/responses/atc/as3/declaration_successfully_submitted.json",
            },
            "4eb601c4-7f06-4fd7-b8d5-947e7b206a37",
            ["in progress", "success"],
            {
                "result_file": "./tests/responses/atc/as3/task_success.json",
                "changed": True,
                "failed": False,
            },
        ),
        # POST AS3 declaration from url
        (
            {
                "as3_tenant": "Simple_01",
                "atc_declaration_url": "https://test.com/simple_01.json",
                "atc_method": "POST",
                "atc_service": "AS3",
            },
            {
                "status_code": 200,
                "data": "./tests/responses/atc/as3/declaration_successfully_submitted.json",
            },
            "4eb601c4-7f06-4fd7-b8d5-947e7b206a37",
            ["in progress", "no change"],
            {
                "result_file": "./tests/responses/atc/as3/task_no_change.json",
                "changed": False,
                "failed": False,
            },
        ),
        # POST AS3 declaration, failed
        (
            {
                "atc_declaration": {"class": "AS3"},
                "atc_method": "POST",
                "atc_service": "AS3",
                "as3_tenant": "Simple_01",
            },
            {
                "status_code": 200,
                "data": "./tests/responses/atc/as3/declaration_failed.json",
            },
            "",
            [],
            {
                "result": "Declaration failed.",
                "changed": False,
                "failed": True,
            },
        ),
        # POST AS3 declaration, timeout
        (
            {
                "atc_declaration": {"class": "AS3"},
                "atc_method": "POST",
                "atc_service": "AS3",
                "as3_tenant": "Simple_01",
            },
            {
                "status_code": 200,
                "data": "./tests/responses/atc/as3/declaration_successfully_submitted.json",
            },
            "4eb601c4-7f06-4fd7-b8d5-947e7b206a37",
            ["in progress"],
            {
                "result": "The declaration deployment has reached maximum retries.",
                "changed": False,
                "failed": True,
            },
        ),
        # POST AS3 declaration, error message
        (
            {
                "atc_declaration": {"class": "AS3"},
                "atc_method": "POST",
                "atc_service": "AS3",
                "as3_tenant": "Simple_01",
            },
            {
                "status_code": 200,
                "data": "./tests/responses/atc/as3/declaration_successfully_submitted.json",
            },
            "4eb601c4-7f06-4fd7-b8d5-947e7b206a37",
            ["in progress", "failed"],
            {
                "result": "Declaration failed.",
                "changed": False,
                "failed": True,
            },
        ),
        # DELETE AS3 declaration
        (
            {
                "as3_tenant": "Simple_01",
                "atc_declaration": {"class": "AS3"},
                "atc_method": "DELETE",
            },
            {
                "status_code": 200,
                "data": "./tests/responses/atc/as3/declaration_successfully_submitted.json",
            },
            "4eb601c4-7f06-4fd7-b8d5-947e7b206a37",
            ["in progress", "success"],
            {
                "result_file": "./tests/responses/atc/as3/task_success.json",
                "changed": True,
                "failed": False,
            },
        ),
        # PATCH AS3 declaration, invalid atc method
        (
            {
                "atc_declaration": {"class": "AS3"},
                "atc_method": "PATCH",
                "atc_service": "AS3",
            },
            {},
            "",
            [""],
            {
                "result": "ATC method 'PATCH' is not valid.",
                "changed": False,
                "failed": True,
            },
        ),
    ],
)
@pytest.mark.parametrize("as3_version", ["3.4.0", "3.22.1"])
@responses.activate
def test_as3_deploy(
    nornir, kwargs, task_id, task_statuses, resp, expected, as3_version
):
    # Callback to provide dynamic task status responses
    def get_task_callback(request):
        calls = [
            d
            for d in responses.calls
            if f"/mgmt/shared/appsvcs/task/{task_id}" in d.request.url
        ]

        if len(calls) == 0:
            current_task_status = task_statuses[0]
        elif len(calls) > len(task_statuses):
            current_task_status = task_statuses[len(task_statuses) - 1]
        else:
            current_task_status = task_statuses[len(calls) - 1]

        return (
            200,
            {},
            json.dumps(
                load_json(
                    f"{base_resp_dir}/atc/as3/task_{current_task_status.replace(' ', '_').lower()}.json"  # noqa B950
                )
            ),
        )

    # Register mock responses
    # GET declaration from url
    responses.add(
        responses.GET,
        "https://test.com/simple_01.json",
        json=load_json(f"{base_decl_dir}/atc/as3/simple_01.json"),
        status=200,
    )
    # GET info
    responses.add(
        responses.GET,
        re.compile("https://bigip(1|2).localhost:443/mgmt/shared/appsvcs/info"),
        json=load_json(f"{base_resp_dir}/atc/as3/version_{as3_version}.json"),
        status=200,
    )
    # GET task
    responses.add_callback(
        responses.GET,
        re.compile(
            "https://bigip(1|2).localhost:443/mgmt/shared/appsvcs/task/4eb601c4-7f06-4fd7-b8d5-947e7b206a37"  # noqa B950
        ),
        callback=get_task_callback,
    )

    if resp:
        responses_data = load_json(resp["data"])
        responses.add(
            kwargs["atc_method"] if "atc_method" in kwargs else "GET",
            re.compile(
                "https://bigip(1|2).localhost:443/mgmt/shared/appsvcs/declare(/Simple_01)?"
            ),
            match_querystring=False,
            json=responses_data,
            status=resp["status_code"],
        )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(
        name="Deploy ATC Declaration",
        task=f5_deploy_atc,
        atc_delay=0,
        atc_retries=3,
        **kwargs,
    )

    # Assert result
    assert_result(result, expected)
