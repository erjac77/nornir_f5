"""Nornir tasks plugins."""

from nornir_f5.plugins.tasks.atc import f5_deploy_atc
from nornir_f5.plugins.tasks.cm import (
    f5_get_failover_status,
    f5_get_sync_status,
    f5_sync_config,
)

__all__ = (
    "f5_deploy_atc",
    "f5_get_failover_status",
    "f5_get_sync_status",
    "f5_sync_config",
)
