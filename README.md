# nornir_f5

![Build Status](https://github.com/erjac77/nornir_f5/workflows/test/badge.svg)
[![codecov](https://codecov.io/gh/erjac77/nornir_f5/branch/master/graph/badge.svg?token=XXIASNEDFR)](https://codecov.io/gh/erjac77/nornir_f5)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub license](https://img.shields.io/github/license/erjac77/nornir_f5.svg)](https://github.com/erjac77/nornir_f5/blob/master/LICENSE)

Collection of Nornir plugins to interact with F5 systems and deploy declaratives to F5 Automation Toolchain (ATC) services like AS3, DO, and TS.

## Installation

### Pip

```bash
pip install nornir-f5
```

### Poetry

```bash
poetry add nornir-f5
```

## Usage

```python
from nornir import InitNornir
from nornir.core.task import Result, Task
from nornir_utils.plugins.functions import print_result

from nornir_f5.plugins.tasks import (
    atc,
    bigip_cm_config_sync,
    bigip_cm_failover_status,
)

def as3_post(task: Task, as3_tenant: str) -> Result:
    # Get the failover status of the device.
    failover_status = task.run(
        name="Get failover status", task=bigip_cm_failover_status
    ).result

    # If it's the ACTIVE device, send the declaration and perform a sync.
    if failover_status == "ACTIVE":
        task.run(
            name="POST AS3 Declaration from file",
            task=atc,
            atc_method="POST",
            atc_service="AS3",
            as3_tenant=as3_tenant,
            atc_declaration_file=task.host["appsvcs"][as3_tenant][
                "atc_declaration_file"
            ],
        )

        task.run(
            name="Synchronize the devices",
            task=bigip_cm_config_sync,
            device_group=task.host["device_group"],
        )

        return Result(
            host=task.host,
            result="ACTIVE device, AS3 declaration successfully deployed.",
        )
    # Else, do nothing...
    else:
        return Result(host=task.host, result="STANDBY device, skipped.")

nr = InitNornir(config_file="config.yml")
nr = nr.filter(platform="f5_bigip")

result = nr.run(
    name="AS3 POST",
    task=as3_post,
    as3_tenant="Simple_01",
)

print_result(result)
```

## Plugins

### Connections

* __f5__: Connects to an F5 REST server.

### Tasks

* __atc__: Deploys ATC declaratives on a BIG-IP/IQ system.
* __atc_info__: Returns the version and release information of the ATC service instance.
* __bigip_cm_config_sync__: Synchronizes the configuration between BIG-IP systems.
* __bigip_cm_failover_status__: Gets the failover status of the BIG-IP system.
* __bigip_cm_sync_status__: Gets the configuration synchronization status of the BIG-IP system.
* __bigip_shared_file_transfer_uploads__: Uploads a file to a BIG-IP system.
* __bigip_shared_iapp_lx_package__: Manages Javascript LX packages on a BIG-IP system.
* __bigip_sys_version__: Gets software version information for the BIG-IP system.
* __bigip_util_unix_ls__: Lists information about the file(s) or directory content on a BIG-IP system.
* __bigip_util_unix_rm__: Deletes a file on a BIG-IP system.

## Authors

* Eric Jacob (@erjac77)
