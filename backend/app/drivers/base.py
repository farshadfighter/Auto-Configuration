"""Driver interface every technology plugin implements (spec sections 32-35, 118). Core
application code must never branch on vendor - it only calls this interface. Vendor-specific
logic lives exclusively in drivers, templates, and rule YAML (spec section 117)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChangeType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NO_CHANGE = "no_change"


class RollbackStrategy(str, Enum):
    CONFIG_REPLACE = "config_replace"
    COMPENSATING_ACTION = "compensating_action"
    UNSUPPORTED = "unsupported"


@dataclass
class DriverManifest:
    name: str
    version: str
    vendor: str
    supported_os: list[str]
    capabilities: dict[str, bool] = field(default_factory=dict)
    rollback_strategy: RollbackStrategy = RollbackStrategy.UNSUPPORTED


@dataclass
class ValidationIssue:
    code: str
    severity: str  # pass | warning | high | critical
    field: str | None
    message: str


@dataclass
class Operation:
    sequence: int
    operation_type: str
    rendered_config: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeployResult:
    success: bool
    output: str
    error: str | None = None


@dataclass
class VerifyResult:
    matches_expected: bool
    actual_state: dict[str, Any]
    details: str = ""


class UnsupportedCapabilityError(Exception):
    pass


class Driver(ABC):
    manifest: DriverManifest

    def get_capabilities(self) -> dict[str, bool]:
        return self.manifest.capabilities

    def supports(self, object_type: str) -> bool:
        return self.manifest.capabilities.get(object_type, False)

    def _require_capability(self, object_type: str) -> None:
        if not self.supports(object_type):
            raise UnsupportedCapabilityError(
                f"{self.manifest.name} does not support object type '{object_type}'"
            )

    # --- Offline (no live connection required) -----------------------------------------

    @abstractmethod
    def validate_intent(self, object_type: str, parameters: dict) -> list[ValidationIssue]:
        """Structural/schema validation of desired parameters. No device I/O."""

    @abstractmethod
    def generate_operations(
        self, object_type: str, change_type: ChangeType, parameters: dict, current_state: dict | None
    ) -> list[Operation]:
        """Renders the concrete commands/config for a change. No device I/O."""

    # --- Online (require connect() first) -----------------------------------------------

    def connect(self, *, host: str, port: int, username: str, password: str | None = None, **kwargs) -> None:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError

    def identify(self) -> dict:
        raise NotImplementedError

    def get_current_state(self, object_type: str, parameters: dict) -> dict | None:
        raise NotImplementedError

    def precheck(self) -> list[ValidationIssue]:
        return []

    def backup(self) -> str:
        raise NotImplementedError

    def deploy(self, operations: list[Operation]) -> DeployResult:
        raise NotImplementedError

    def verify(self, object_type: str, parameters: dict) -> VerifyResult:
        raise NotImplementedError

    def rollback(self, backup_content: str) -> DeployResult:
        raise NotImplementedError
