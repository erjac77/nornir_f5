"""Nornir F5 tasks."""

from nornir_f5.plugins.tasks.atc import atc
from nornir_f5.plugins.tasks.bigip.cm.config_sync import bigip_cm_config_sync
from nornir_f5.plugins.tasks.bigip.cm.failover_status import bigip_cm_failover_status
from nornir_f5.plugins.tasks.bigip.cm.sync_status import bigip_cm_sync_status
from nornir_f5.plugins.tasks.bigip.shared.file_transfer.uploads import (
    bigip_shared_file_transfer_uploads,
)
from nornir_f5.plugins.tasks.bigip.shared.iapp.package_management_tasks import (
    bigip_shared_iapp_lx_package,
)
from nornir_f5.plugins.tasks.bigip.sys.version import bigip_sys_version
from nornir_f5.plugins.tasks.bigip.util.unix_ls import bigip_util_unix_ls
from nornir_f5.plugins.tasks.bigip.util.unix_rm import bigip_util_unix_rm

__all__ = (
    "atc",
    "bigip_cm_config_sync",
    "bigip_cm_failover_status",
    "bigip_cm_sync_status",
    "bigip_shared_file_transfer_uploads",
    "bigip_shared_iapp_lx_package",
    "bigip_sys_version",
    "bigip_util_unix_ls",
    "bigip_util_unix_rm",
)
