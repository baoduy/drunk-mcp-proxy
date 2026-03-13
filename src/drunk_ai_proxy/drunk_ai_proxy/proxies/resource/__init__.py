"""Resource proxy providers package.

Exports on-demand remote resource service for skills, agents, and prompts.
"""

from .on_demand_remote_resource_service import (
    OnDemandRemoteResourceService,
    RemoteResourceEntry,
)

__all__ = [
    "OnDemandRemoteResourceService",
    "RemoteResourceEntry",
]
