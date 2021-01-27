"""Nornir F5 tasks."""

from nornir_f5.plugins.tasks.atc import f5_atc
from nornir_f5.plugins.tasks.bigip.cm import (
    f5_bigip_cm_failover_status,
    f5_bigip_cm_sync_config,
    f5_bigip_cm_sync_status,
)
from nornir_f5.plugins.tasks.bigip.shared.file_transfer.upload import (
    f5_bigip_shared_file_transfer_upload,
)
from nornir_f5.plugins.tasks.bigip.shared.iapp.package_management_tasks import (
    f5_bigip_shared_iapp_lx_package,
)
from nornir_f5.plugins.tasks.bigip.sys import f5_bigip_sys_version
from nornir_f5.plugins.tasks.bigip.util import (
    f5_bigip_util_unix_ls,
    f5_bigip_util_unix_rm,
)

__all__ = (
    "f5_atc",
    "f5_bigip_cm_failover_status",
    "f5_bigip_cm_sync_config",
    "f5_bigip_cm_sync_status",
    "f5_bigip_shared_file_transfer_upload",
    "f5_bigip_shared_iapp_lx_package",
    "f5_bigip_sys_version",
    "f5_bigip_util_unix_ls",
    "f5_bigip_util_unix_rm",
)
