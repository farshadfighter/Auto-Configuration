import re
from typing import Any

from app.drivers.base import (
    ChangeType,
    DeployResult,
    Driver,
    DriverManifest,
    Operation,
    RollbackStrategy,
    ValidationIssue,
    VerifyResult,
)


class FortiOSDriver(Driver):
    manifest = DriverManifest(
        name="fortios",
        version="1.0.0",
        vendor="Fortinet",
        supported_os=["FortiOS"],
        capabilities={"firewall_policy": True},
        rollback_strategy=RollbackStrategy.CONFIG_REPLACE,
    )

    def __init__(self) -> None:
        self._connection: Any = None

    def validate_intent(self, object_type: str, parameters: dict) -> list[ValidationIssue]:
        self._require_capability(object_type)
        issues: list[ValidationIssue] = []
        for field_name in ("name", "srcintf", "dstintf", "srcaddr", "dstaddr", "action"):
            if not parameters.get(field_name):
                issues.append(ValidationIssue("FIELD_REQUIRED", "critical", field_name, f"{field_name} is required"))
        if parameters.get("action") not in (None, "accept", "deny"):
            issues.append(ValidationIssue("INVALID_ACTION", "high", "action", "action must be 'accept' or 'deny'"))
        return issues

    def generate_operations(
        self, object_type: str, change_type: ChangeType, parameters: dict, current_state: dict | None
    ) -> list[Operation]:
        self._require_capability(object_type)
        policy_id = parameters.get("policy_id") or (current_state or {}).get("policy_id", 0)
        if change_type == ChangeType.DELETE:
            return [
                Operation(
                    1,
                    "delete_firewall_policy",
                    f"config firewall policy\n    delete {policy_id}\nend",
                )
            ]
        lines = [
            "config firewall policy",
            f"    edit {policy_id}" if policy_id else "    edit 0",
            f"        set name \"{parameters['name']}\"",
            f"        set srcintf \"{parameters['srcintf']}\"",
            f"        set dstintf \"{parameters['dstintf']}\"",
            f"        set srcaddr \"{parameters['srcaddr']}\"",
            f"        set dstaddr \"{parameters['dstaddr']}\"",
            f"        set action {parameters.get('action', 'accept')}",
            f"        set schedule \"{parameters.get('schedule', 'always')}\"",
            f"        set service \"{parameters.get('service', 'ALL')}\"",
            "    next",
            "end",
        ]
        return [Operation(1, "configure_firewall_policy", "\n".join(lines))]

    # --- Online ------------------------------------------------------------------------

    def connect(self, *, host: str, port: int = 22, username: str, password: str | None = None, **kwargs) -> None:
        from netmiko import ConnectHandler

        self._connection = ConnectHandler(
            device_type="fortinet", host=host, port=port, username=username, password=password
        )

    def disconnect(self) -> None:
        if self._connection:
            self._connection.disconnect()
            self._connection = None

    def identify(self) -> dict:
        return {"raw": self._connection.send_command("get system status")}

    def get_current_state(self, object_type: str, parameters: dict) -> dict | None:
        policy_id = parameters.get("policy_id")
        if not policy_id:
            return None
        output = self._connection.send_command(f"show firewall policy {policy_id}")
        if not output.strip():
            return None
        name_match = re.search(r'set name "([^"]+)"', output)
        return {"policy_id": policy_id, "name": name_match.group(1) if name_match else None, "raw": output}

    def backup(self) -> str:
        return self._connection.send_command("show full-configuration")

    def deploy(self, operations: list[Operation]) -> DeployResult:
        try:
            commands = [line for op in operations for line in op.rendered_config.splitlines()]
            output = self._connection.send_config_set(commands)
            return DeployResult(success=True, output=output)
        except Exception as exc:  # pragma: no cover - requires a live/mock device
            return DeployResult(success=False, output="", error=str(exc))

    def verify(self, object_type: str, parameters: dict) -> VerifyResult:
        actual = self.get_current_state(object_type, parameters) or {}
        matches = actual.get("name") == parameters.get("name")
        return VerifyResult(matches_expected=matches, actual_state=actual)

    def rollback(self, backup_content: str) -> DeployResult:
        try:
            output = self._connection.send_config_set(backup_content.splitlines())
            return DeployResult(success=True, output=output)
        except Exception as exc:  # pragma: no cover - requires a live/mock device
            return DeployResult(success=False, output="", error=str(exc))
