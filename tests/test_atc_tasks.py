import json
import re

import pytest

import responses
from nornir_f5.plugins.tasks import atc

from .conftest import assert_result, base_decl_dir, base_resp_dir, load_json


@pytest.mark.parametrize(
    ("kwargs", "resp", "task_statuses", "expected"),
    [
        # GET AS3 declaration with show and show_hash
        (
            {"as3_show": "full", "as3_show_hash": True, "atc_service": "AS3"},
            {"status_code": 200, "data": f"{base_decl_dir}/atc/as3/simple_01.json"},
            [""],
            {"result_file": f"{base_decl_dir}/atc/as3/simple_01.json"},
        ),
        # Dry-run
        (
            {"atc_service": "AS3", "dry_run": True},
            {"status_code": 200, "data": f"{base_decl_dir}/atc/as3/simple_01.json"},
            [""],
            {"result": None},
        ),
        # GET declaration with invalid atc_service
        (
            {"atc_declaration": {"class": "AS2"}, "atc_service": "AS2"},
            {},
            [""],
            {"result": "ATC service 'AS2' is not valid.", "failed": True},
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
                "data": f"{base_resp_dir}/atc/as3/declaration_successfully_submitted.json",  # noqa B950
            },
            ["in progress", "success"],
            {"result": "ATC declaration successfully deployed.", "changed": True},
        ),
        # POST AS3 declaration without atc_service
        (
            {
                "atc_declaration": {"class": "AS3"},
                "atc_method": "POST",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/atc/as3/declaration_successfully_submitted.json",  # noqa B950
            },
            ["in progress", "success"],
            {"result": "ATC declaration successfully deployed.", "changed": True},
        ),
        # POST AS3 declaration from file
        (
            {
                "as3_tenant": "Simple_01",
                "atc_declaration_file": f"{base_decl_dir}/atc/as3/simple_01.json",
                "atc_method": "POST",
                "atc_service": "AS3",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/atc/as3/declaration_successfully_submitted.json",  # noqa B950
            },
            ["in progress", "success"],
            {"result": "ATC declaration successfully deployed.", "changed": True},
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
                "data": f"{base_resp_dir}/atc/as3/declaration_successfully_submitted.json",  # noqa B950
            },
            ["in progress", "no change"],
            {
                "result": "ATC declaration successfully submitted, but no change required.",  # noqa B950
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
                "data": f"{base_resp_dir}/atc/as3/declaration_failed.json",
            },
            [],
            {"result": "The declaration deployment failed.", "failed": True},
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
                "data": f"{base_resp_dir}/atc/as3/declaration_successfully_submitted.json",  # noqa B950
            },
            ["in progress"],
            {"result": "The task has reached maximum retries.", "failed": True},
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
                "data": f"{base_resp_dir}/atc/as3/declaration_successfully_submitted.json",  # noqa B950
            },
            ["in progress", "failed"],
            {"result": "The task failed.", "failed": True},
        ),
        # POST AS3 declaration, error message with response
        (
            {
                "atc_declaration": {"class": "AS3"},
                "atc_method": "POST",
                "atc_service": "AS3",
                "as3_tenant": "Simple_01",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/atc/as3/declaration_successfully_submitted.json",  # noqa B950
            },
            ["in progress", "declaration failed"],
            {"result": "Error on Virtual.", "failed": True},
        ),
        # POST AS3 declaration, invalid
        (
            {
                "atc_declaration": {"class": "AS3"},
                "atc_method": "POST",
                "atc_service": "AS3",
                "as3_tenant": "Simple_01",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/atc/as3/declaration_successfully_submitted.json",  # noqa B950
            },
            ["in progress", "declaration is invalid"],
            {
                "result": "['/Simple_01/A1/service/virtualAddresses: should NOT have fewer than 1 items']",  # noqa B950
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
                "data": f"{base_resp_dir}/atc/as3/declaration_successfully_submitted.json",  # noqa B950
            },
            ["in progress", "success"],
            {"result": "ATC declaration successfully deployed.", "changed": True},
        ),
        # PATCH AS3 declaration, invalid atc method
        (
            {
                "atc_declaration": {"class": "AS3"},
                "atc_method": "PATCH",
                "atc_service": "AS3",
            },
            {},
            [""],
            {"result": "ATC method 'PATCH' is not valid.", "failed": True},
        ),
    ],
)
@pytest.mark.parametrize("as3_version", ["3.4.0", "3.22.1"])
@responses.activate
def test_as3_deploy(nornir, kwargs, resp, task_statuses, expected, as3_version):
    task_id = "4eb601c4-7f06-4fd7-b8d5-947e7b206a37"

    # Callback to provide dynamic task status responses
    def get_task_callback(request):
        calls = [
            d
            for d in responses.calls
            if f"/mgmt/shared/appsvcs/task/{task_id}" in d.request.url
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
                    f"{base_resp_dir}/atc/as3/task_{current_task_status.replace(' ', '_').lower()}.json"  # noqa B950
                )
            ),
        )

    # Register mock responses
    # GET AS3 declaration from url
    responses.add(
        responses.GET,
        "https://test.com/simple_01.json",
        json=load_json(f"{base_decl_dir}/atc/as3/simple_01.json"),
        status=200,
    )
    # GET AS3 info
    responses.add(
        responses.GET,
        "https://bigip1.localhost:443/mgmt/shared/appsvcs/info",
        json=load_json(f"{base_resp_dir}/atc/as3/version_{as3_version}.json"),
        status=200,
    )
    # GET AS3 task
    responses.add_callback(
        responses.GET,
        f"https://bigip1.localhost:443/mgmt/shared/appsvcs/task/{task_id}",
        callback=get_task_callback,
    )

    if resp:
        responses_data = load_json(resp["data"])
        responses.add(
            kwargs["atc_method"] if "atc_method" in kwargs else "GET",
            re.compile(
                "https://bigip1.localhost:443/mgmt/shared/appsvcs/declare(/Simple_01)?"
            ),
            json=responses_data,
            status=resp["status_code"],
        )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(
        name="Deploy AS3 Declaration",
        task=atc,
        atc_delay=0,
        atc_retries=3,
        **kwargs,
    )

    # Assert result
    assert_result(result, expected)


@pytest.mark.parametrize(
    ("kwargs", "resp", "task_statuses", "expected"),
    [
        # POST DO declaration from file
        (
            {
                "atc_declaration_file": f"{base_decl_dir}/atc/device/basic.json",
                "atc_method": "POST",
                "atc_service": "Device",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/atc/device/task_processing.json",
            },
            ["processing", "success"],
            {"result": "ATC declaration successfully deployed.", "changed": True},
        ),
    ],
)
@responses.activate
def test_do_deploy(nornir, kwargs, resp, task_statuses, expected):
    task_id = "5eb601c4-7f06-4fd7-b8d5-947e7b206a38"

    # Callback to provide dynamic task status responses
    def get_task_callback(request):
        calls = [
            d
            for d in responses.calls
            if f"/mgmt/shared/declarative-onboarding/task/{task_id}" in d.request.url
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
                    f"{base_resp_dir}/atc/device/task_{current_task_status.replace(' ', '_').lower()}.json"  # noqa B950
                )
            ),
        )

    # Register mock responses
    # GET DO info
    responses.add(
        responses.GET,
        "https://bigip1.localhost:443/mgmt/shared/declarative-onboarding/info",
        json=load_json(f"{base_resp_dir}/atc/device/version_3.22.1.json"),
        status=200,
    )
    # GET DO task
    responses.add_callback(
        responses.GET,
        f"https://bigip1.localhost:443/mgmt/shared/declarative-onboarding/task/{task_id}",  # noqa B950
        callback=get_task_callback,
    )

    if resp:
        responses_data = load_json(resp["data"])
        responses.add(
            kwargs["atc_method"] if "atc_method" in kwargs else "GET",
            "https://bigip1.localhost:443/mgmt/shared/declarative-onboarding",
            json=responses_data,
            status=resp["status_code"],
        )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(
        name="Deploy DO Declaration",
        task=atc,
        atc_delay=0,
        atc_retries=3,
        **kwargs,
    )

    # Assert result
    assert_result(result, expected)


@pytest.mark.parametrize(
    ("kwargs", "resp", "expected"),
    [
        # POST TS declaration from file
        (
            {
                "atc_declaration_file": f"{base_decl_dir}/atc/telemetry/default_pull_consumer.json",  # noqa B950
                "atc_method": "POST",
                "atc_service": "Telemetry",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/atc/telemetry/success.json",
            },
            {
                "result_file": f"{base_resp_dir}/atc/telemetry/success.json",
            },
        ),
        # POST TS declaration, failed
        (
            {
                "atc_declaration": {"class": "Telemetry"},
                "atc_method": "POST",
                "atc_service": "Telemetry",
            },
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/atc/telemetry/failed.json",
            },
            {"result": "The declaration deployment failed.", "failed": True},
        ),
    ],
)
@responses.activate
def test_ts_deploy(nornir, kwargs, resp, expected):
    # Register mock responses
    # GET TS info
    responses.add(
        responses.GET,
        "https://bigip1.localhost:443/mgmt/shared/telemetry/info",
        json=load_json(f"{base_resp_dir}/atc/telemetry/version_1.17.0.json"),
        status=200,
    )

    if resp:
        responses_data = load_json(resp["data"])
        responses.add(
            kwargs["atc_method"] if "atc_method" in kwargs else "GET",
            "https://bigip1.localhost:443/mgmt/shared/telemetry/declare",
            json=responses_data,
            status=resp["status_code"],
        )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(
        name="Deploy TS Declaration",
        task=atc,
        atc_delay=0,
        atc_retries=3,
        **kwargs,
    )

    # Assert result
    assert_result(result, expected)
