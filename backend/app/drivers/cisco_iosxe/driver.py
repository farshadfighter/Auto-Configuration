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


class CiscoIOSXEDriver(Driver):
    manifest = DriverManifest(
        name="cisco_iosxe",
        version="1.0.0",
        vendor="Cisco",
        supported_os=["IOS-XE"],
        capabilities={"interface": True, "vlan": True},
        rollback_strategy=RollbackStrategy.CONFIG_REPLACE,
    )

    def __init__(self) -> None:
        self._connection: Any = None

    # --- Offline ---------------------------------------------------------------------

    def validate_intent(self, object_type: str, parameters: dict) -> list[ValidationIssue]:
        self._require_capability(object_type)
        issues: list[ValidationIssue] = []
        if object_type == "vlan":
            vlan_id = parameters.get("vlan_id")
            if not isinstance(vlan_id, int) or not (1 <= vlan_id <= 4094):
                issues.append(ValidationIssue("INVALID_VLAN_ID", "critical", "vlan_id", "vlan_id must be 1-4094"))
            if not parameters.get("name"):
                issues.append(ValidationIssue("VLAN_NAME_REQUIRED", "high", "name", "VLAN name is required"))
        elif object_type == "interface":
            if not parameters.get("name"):
                issues.append(ValidationIssue("INTERFACE_NAME_REQUIRED", "critical", "name", "Interface name is required"))
            mode = parameters.get("mode", "access")
            if mode not in ("access", "trunk"):
                issues.append(ValidationIssue("INVALID_MODE", "high", "mode", "mode must be 'access' or 'trunk'"))
            if mode == "access" and not parameters.get("access_vlan"):
                issues.append(
                    ValidationIssue("ACCESS_VLAN_REQUIRED", "high", "access_vlan", "access_vlan is required in access mode")
                )
        return issues

    def generate_operations(
        self, object_type: str, change_type: ChangeType, parameters: dict, current_state: dict | None
    ) -> list[Operation]:
        self._require_capability(object_type)
        if object_type == "vlan":
            return self._generate_vlan_operations(change_type, parameters)
        if object_type == "interface":
            return self._generate_interface_operations(change_type, parameters)
        raise ValueError(f"Unhandled object_type: {object_type}")

    def _generate_vlan_operations(self, change_type: ChangeType, parameters: dict) -> list[Operation]:
        vlan_id = parameters["vlan_id"]
        if change_type == ChangeType.DELETE:
            return [Operation(1, "delete_vlan", f"no vlan {vlan_id}")]
        lines = [f"vlan {vlan_id}", f" name {parameters['name']}"]
        return [Operation(1, "create_or_update_vlan", "\n".join(lines))]

    def _generate_interface_operations(self, change_type: ChangeType, parameters: dict) -> list[Operation]:
        name = parameters["name"]
        if change_type == ChangeType.DELETE:
            return [Operation(1, "reset_interface", f"default interface {name}")]
        lines = [f"interface {name}"]
        if parameters.get("description"):
            lines.append(f" description {parameters['description']}")
        mode = parameters.get("mode", "access")
        lines.append(f" switchport mode {mode}")
        if mode == "access" and parameters.get("access_vlan"):
            lines.append(f" switchport access vlan {parameters['access_vlan']}")
        return [Operation(1, "configure_interface", "\n".join(lines))]

    # --- Online ------------------------------------------------------------------------

    def connect(self, *, host: str, port: int = 22, username: str, password: str | None = None, **kwargs) -> None:
        from netmiko import ConnectHandler

        self._connection = ConnectHandler(
            device_type="cisco_ios", host=host, port=port, username=username, password=password
        )

    def disconnect(self) -> None:
        if self._connection:
            self._connection.disconnect()
            self._connection = None

    def identify(self) -> dict:
        output = self._connection.send_command("show version")
        return {"raw": output}

    def get_current_state(self, object_type: str, parameters: dict) -> dict | None:
        if object_type == "vlan":
            output = self._connection.send_command(f"show vlan id {parameters['vlan_id']}")
            match = re.search(r"^\d+\s+(\S+)", output, re.MULTILINE)
            if not match:
                return None
            return {"vlan_id": parameters["vlan_id"], "name": match.group(1)}
        if object_type == "interface":
            output = self._connection.send_command(f"show running-config interface {parameters['name']}")
            if "% Invalid" in output or not output.strip():
                return None
            vlan_match = re.search(r"switchport access vlan (\d+)", output)
            return {
                "name": parameters["name"],
                "access_vlan": int(vlan_match.group(1)) if vlan_match else None,
                "raw": output,
            }
        raise ValueError(f"Unhandled object_type: {object_type}")

    def backup(self) -> str:
        return self._connection.send_command("show running-config")

    def deploy(self, operations: list[Operation]) -> DeployResult:
        try:
            commands = [line for op in operations for line in op.rendered_config.splitlines()]
            output = self._connection.send_config_set(commands)
            return DeployResult(success=True, output=output)
        except Exception as exc:  # pragma: no cover - requires a live/mock device
            return DeployResult(success=False, output="", error=str(exc))

    def verify(self, object_type: str, parameters: dict) -> VerifyResult:
        actual = self.get_current_state(object_type, parameters) or {}
        if object_type == "vlan":
            matches = actual.get("name") == parameters.get("name")
        elif object_type == "interface":
            matches = actual.get("access_vlan") == parameters.get("access_vlan")
        else:
            matches = False
        return VerifyResult(matches_expected=matches, actual_state=actual)

    def rollback(self, backup_content: str) -> DeployResult:
        try:
            output = self._connection.send_config_set(backup_content.splitlines())
            return DeployResult(success=True, output=output)
        except Exception as exc:  # pragma: no cover - requires a live/mock device
            return DeployResult(success=False, output="", error=str(exc))
