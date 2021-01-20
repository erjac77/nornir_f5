# nornir_f5

![Build Status](https://github.com/erjac77/nornir_f5/workflows/test/badge.svg)
[![codecov](https://codecov.io/gh/erjac77/nornir_f5/branch/master/graph/badge.svg?token=XXIASNEDFR)](https://codecov.io/gh/erjac77/nornir_f5)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub license](https://img.shields.io/github/license/erjac77/nornir_f5.svg)](https://github.com/erjac77/nornir_f5/blob/master/LICENSE)

F5 plugins for Nornir.

## Installation

### Pip

```bash
pip install nornir_f5
```

### Poetry

```bash
poetry add nornir_f5
```

## Usage

```python
from nornir import InitNornir
from nornir.core.task import Result, Task
from nornir_utils.plugins.functions import print_result

from nornir_f5.plugins.tasks import (
    f5_deploy_atc,
    f5_get_failover_status,
    f5_sync_config,
)

def as3_post(task: Task, as3_tenant: str) -> Result:
    # Get the failover status of the device.
    failover_status = task.run(
        name="Get failover status", task=f5_get_failover_status
    ).result

    # If ACTIVE, send the declaration and perform a sync.
    if failover_status == "ACTIVE":
        task.run(
            name="AS3 POST",
            task=f5_deploy_atc,
            atc_method="POST",
            atc_service="AS3",
            as3_tenant=as3_tenant,
            atc_declaration_file=task.host["appsvcs"][as3_tenant][
                "atc_declaration_file"
            ],
        )

        task.run(
            name="Synchronize the devices",
            task=f5_sync_config,
            device_group=task.host["device_group"],
        )

        return Result(
            host=task.host,
            result="ACTIVE device, AS3 declaration successfully deployed",
        )
    # Else, do nothing...
    else:
        return Result(host=task.host, result="STANDBY device, skipped")

nr = InitNornir(config_file="config.yml")
nr = nr.filter(platform="f5_bigip")

result = nr.run(
    name="POST AS3 Declaration from file",
    task=as3_post,
    as3_tenant="Simple_01",
)

print_result(result)
```

## Plugins

### Connections

* __f5__: Connect to F5 BIG-IP systems using iControl REST.

### Tasks

* __f5_deploy_atc__: Deploy F5 Automation Tool Chain (ATC) declaration (only AS3 for now) on BIG-IP systems.
* __f5_get_failover_status__: Get the failover status of the device.
* __f5_get_sync_status__: Get the configuration synchronization status of the device.
* __f5_sync_config__: Synchronize the configuration between devices.

## Roadmap

* Device (DO)
* Telemetry (TS)

## Authors

* Eric Jacob (@erjac77)
