import json
import re

import pytest
from nornir.core.task import Result, Task
from nornir_utils.plugins.functions import print_result

import responses
from nornir_f5.plugins.tasks import atc, bigip_cm_config_sync, bigip_cm_failover_status

from .conftest import base_resp_dir, load_json


def as3_post(task: Task, as3_tenant: str) -> Result:
    failover_status = task.run(
        name="Get failover status", task=bigip_cm_failover_status
    ).result

    if failover_status == "ACTIVE":
        task.run(
            name="AS3 POST",
            task=atc,
            atc_delay=0,
            atc_method="POST",
            atc_retries=3,
            atc_service="AS3",
            as3_tenant=as3_tenant,
            atc_declaration_file=task.host["appsvcs"][as3_tenant][
                "atc_declaration_file"
            ],
        )

        task.run(
            name="Synchronize the devices",
            task=bigip_cm_config_sync,
            delay=0,
            device_group=task.host["device_group"],
            retries=3,
        )

        return Result(
            host=task.host,
            result="ACTIVE device, AS3 declaration successfully deployed.",
        )
    else:
        return Result(host=task.host, result="STANDBY device, skipped.")


@pytest.mark.parametrize(
    ("resp", "task_id", "task_statuses", "sync_statuses"),
    [
        (
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/atc/as3/declaration_successfully_submitted.json",  # noqa B950
            },
            "4eb601c4-7f06-4fd7-b8d5-947e7b206a37",
            ["in progress", "success"],
            ["Changes Pending", "Not All Devices Synced", "In Sync"],
        ),
    ],
)
@responses.activate
def test_as3_post(nornir, resp, task_id, task_statuses, sync_statuses):
    last_sync_status = sync_statuses[len(sync_statuses) - 1]

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

    # Callback to provide dynamic sync status responses
    def get_sync_status_callback(request):
        calls = [
            d for d in responses.calls if "/mgmt/tm/cm/sync-status" in d.request.url
        ]

        if len(calls) == 0:
            current_sync_status = sync_statuses[0]
        elif len(calls) > len(sync_statuses):
            current_sync_status = last_sync_status
        else:
            current_sync_status = sync_statuses[len(calls) - 1]

        current_sync_status = current_sync_status.replace(" ", "_").lower()
        return (
            200,
            {},
            json.dumps(
                load_json(
                    f"{base_resp_dir}/bigip/cm/sync_status_{current_sync_status}.json"
                )
            ),
        )

    # Register mock responses
    responses.add(
        responses.GET,
        re.compile("https://bigip1.localhost:443/mgmt/tm/cm/failover-status"),
        json=load_json(f"{base_resp_dir}/bigip/cm/failover_status_active.json"),
        status=200,
    )
    responses.add(
        responses.GET,
        re.compile("https://bigip2.localhost:443/mgmt/tm/cm/failover-status"),
        json=load_json(f"{base_resp_dir}/bigip/cm/failover_status_standby.json"),
        status=200,
    )
    responses.add(
        responses.GET,
        re.compile("https://bigip(1|2).localhost:443/mgmt/shared/appsvcs/info"),
        json=load_json(f"{base_resp_dir}/atc/as3/version_3.22.1.json"),
        status=200,
    )
    responses.add(
        responses.POST,
        "https://bigip1.localhost:443/mgmt/shared/appsvcs/declare/Simple_01",
        match_querystring=False,
        json=load_json(resp["data"]),
        status=resp["status_code"],
    )
    responses.add_callback(
        responses.GET,
        "https://bigip1.localhost:443/mgmt/shared/appsvcs/task/4eb601c4-7f06-4fd7-b8d5-947e7b206a37",  # noqa B950
        callback=get_task_callback,
    )
    responses.add(responses.POST, "https://bigip1.localhost:443/mgmt/tm/cm", status=200)
    responses.add_callback(
        responses.GET,
        "https://bigip1.localhost:443/mgmt/tm/cm/sync-status",
        callback=get_sync_status_callback,
    )

    # Run task
    nornir = nornir.filter(platform="f5_bigip")

    result = nornir.run(
        name="POST AS3 Declaration from file",
        task=as3_post,
        as3_tenant="Simple_01",
    )

    print_result(result)

    # Assert result
    assert not result.failed
    assert (
        result["bigip1.localhost"].result
        == "ACTIVE device, AS3 declaration successfully deployed."
    )
    assert result["bigip1.localhost"].changed
    assert result["bigip2.localhost"].result == "STANDBY device, skipped."
    assert not result["bigip2.localhost"].changed
