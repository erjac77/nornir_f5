import json

import pytest

import responses
from nornir_f5.plugins.tasks import (
    bigip_cm_config_sync,
    bigip_cm_failover_status,
    bigip_cm_sync_status,
)

from .conftest import assert_result, base_resp_dir, load_json


@pytest.mark.parametrize(
    ("resp", "expected"),
    [
        (
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/cm/failover_status_active.json",
            },
            {"result": "ACTIVE"},
        ),
    ],
)
@responses.activate
def test_get_failover_status(nornir, resp, expected):
    # Register mock responses
    responses.add(
        responses.GET,
        "https://bigip1.localhost:443/mgmt/tm/cm/failover-status",
        json=load_json(resp["data"]),
        status=resp["status_code"],
    )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(name="Failover status GET", task=bigip_cm_failover_status)

    # Assert result
    assert_result(result, expected)


@pytest.mark.parametrize(
    ("resp", "expected"),
    [
        (
            {
                "status_code": 200,
                "data": f"{base_resp_dir}/bigip/cm/sync_status_in_sync.json",
            },
            {"result": "In Sync"},
        ),
    ],
)
@responses.activate
def test_get_sync_status(nornir, resp, expected):
    # Register mock responses
    responses.add(
        responses.GET,
        "https://bigip1.localhost:443/mgmt/tm/cm/sync-status",
        json=load_json(resp["data"]),
        status=resp["status_code"],
    )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(name="Sync status GET", task=bigip_cm_sync_status)

    # Assert result
    assert_result(result, expected)


@pytest.mark.parametrize(
    ("kwargs", "sync_statuses", "expected"),
    [
        # Successful sync, direction 'to-group'
        (
            {"direction": "to-group"},
            ["Changes Pending", "Not All Devices Synced", "In Sync"],
            {"result": "In Sync", "changed": True},
        ),
        # Dry-run
        (
            {"direction": "to-group", "dry_run": True},
            ["Changes Pending"],
            {"result": "Changes Pending", "changed": False},
        ),
        # No sync, standalone
        (
            {},
            ["Standalone"],
            {"result": "Standalone"},
        ),
        # Fail sync, invalid direction
        (
            {"direction": "invalid"},
            ["Changes Pending"],
            {
                "result": "Direction 'invalid' is not valid.",
                "failed": True,
            },
        ),
        # Fail sync, disconnected
        (
            {},
            ["Disconnected"],
            {
                "result": "The configuration synchronization has failed (Disconnected).",  # noqa B950
                "failed": True,
            },
        ),
        # Fail sync, not all devices synced, max retries reached
        (
            {},
            ["Changes Pending", "Changes Pending", "Not All Devices Synced"],
            {
                "result": "The configuration synchronization has reached maximum retries (Not All Devices Synced).",  # noqa B950
                "failed": True,
            },
        ),
    ],
)
@responses.activate
def test_post_config_sync(nornir, kwargs, sync_statuses, expected):
    last_sync_status = sync_statuses[len(sync_statuses) - 1]

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
    responses.add_callback(
        responses.GET,
        "https://bigip1.localhost:443/mgmt/tm/cm/sync-status",
        callback=get_sync_status_callback,
    )
    responses.add(
        responses.POST,
        "https://bigip1.localhost:443/mgmt/tm/cm",
        status=200,
    )

    # Run task
    nornir = nornir.filter(name="bigip1.localhost")
    result = nornir.run(
        name="Sync config",
        task=bigip_cm_config_sync,
        delay=0,
        device_group="device_sync_group",
        retries=3,
        **kwargs,
    )

    # Assert result
    assert_result(result, expected)
