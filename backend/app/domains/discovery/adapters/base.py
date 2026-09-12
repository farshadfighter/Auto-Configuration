from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DiscoveredRecord:
    """One normalized record ready to be reconciled against the asset table."""

    target: str
    raw_data: dict
    normalized_data: dict | None = None
    error: str | None = None


@dataclass
class DiscoveryOutcome:
    records: list[DiscoveredRecord] = field(default_factory=list)


class DiscoveryAdapter(ABC):
    """Interface every discovery method implements (spec section 12)."""

    @abstractmethod
    def discover(self, scope: dict) -> DiscoveryOutcome:
        """Enumerate raw targets/records for the given scope."""

    def identify(self, record: DiscoveredRecord) -> DiscoveredRecord:
        """Best-effort identity resolution (vendor/model/serial). Default: no-op."""
        return record

    def collect_facts(self, record: DiscoveredRecord) -> DiscoveredRecord:
        """Best-effort deeper fact collection. Default: no-op."""
        return record

    @abstractmethod
    def normalize(self, record: DiscoveredRecord) -> DiscoveredRecord:
        """Map raw_data into the asset schema shape (normalized_data)."""


class NotImplementedAdapter(DiscoveryAdapter):
    """Placeholder for methods not yet implemented in this phase (SNMP/SSH/NETCONF/...)."""

    def __init__(self, method_name: str):
        self.method_name = method_name

    def discover(self, scope: dict) -> DiscoveryOutcome:
        raise NotImplementedError(f"Discovery method '{self.method_name}' is not implemented yet")

    def normalize(self, record: DiscoveredRecord) -> DiscoveredRecord:
        raise NotImplementedError
