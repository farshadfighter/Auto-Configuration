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


class WindowsDHCPDriver(Driver):
    manifest = DriverManifest(
        name="windows_dhcp",
        version="1.0.0",
        vendor="Microsoft",
        supported_os=["Windows Server"],
        capabilities={"dhcp_scope": True},
        rollback_strategy=RollbackStrategy.COMPENSATING_ACTION,
    )

    def __init__(self) -> None:
        self._session: Any = None

    def validate_intent(self, object_type: str, parameters: dict) -> list[ValidationIssue]:
        self._require_capability(object_type)
        issues: list[ValidationIssue] = []
        for field_name in ("scope_id", "name", "start_range", "end_range", "subnet_mask"):
            if not parameters.get(field_name):
                issues.append(ValidationIssue("FIELD_REQUIRED", "critical", field_name, f"{field_name} is required"))
        if parameters.get("failover_enabled") and not parameters.get("failover_partner"):
            issues.append(
                ValidationIssue(
                    "FAILOVER_PARTNER_REQUIRED", "high", "failover_partner", "failover_partner is required when failover_enabled"
                )
            )
        return issues

    def generate_operations(
        self, object_type: str, change_type: ChangeType, parameters: dict, current_state: dict | None
    ) -> list[Operation]:
        self._require_capability(object_type)
        scope_id = parameters["scope_id"]
        if change_type == ChangeType.DELETE:
            return [Operation(1, "remove_dhcp_scope", f'Remove-DhcpServerv4Scope -ScopeId {scope_id} -Force')]

        ops = []
        if not current_state:
            ops.append(
                Operation(
                    1,
                    "create_dhcp_scope",
                    (
                        f'Add-DhcpServerv4Scope -Name "{parameters["name"]}" -StartRange {parameters["start_range"]} '
                        f'-EndRange {parameters["end_range"]} -SubnetMask {parameters["subnet_mask"]}'
                    ),
                )
            )
        if parameters.get("failover_enabled"):
            ops.append(
                Operation(
                    2,
                    "configure_dhcp_failover",
                    (
                        f'Add-DhcpServerv4Failover -Name "{parameters["name"]}-failover" -ScopeId {scope_id} '
                        f'-PartnerServer {parameters["failover_partner"]} -Force'
                    ),
                )
            )
        return ops

    # --- Online ------------------------------------------------------------------------

    def connect(self, *, host: str, port: int = 5985, username: str, password: str | None = None, **kwargs) -> None:
        import winrm

        self._session = winrm.Session(host, auth=(username, password), transport="ntlm")

    def disconnect(self) -> None:
        self._session = None

    def _run_ps(self, script: str) -> str:
        result = self._session.run_ps(script)
        if result.status_code != 0:
            raise RuntimeError(result.std_err.decode() if isinstance(result.std_err, bytes) else str(result.std_err))
        return result.std_out.decode() if isinstance(result.std_out, bytes) else str(result.std_out)

    def identify(self) -> dict:
        return {"raw": self._run_ps("Get-ComputerInfo | ConvertTo-Json")}

    def get_current_state(self, object_type: str, parameters: dict) -> dict | None:
        scope_id = parameters["scope_id"]
        output = self._run_ps(f"Get-DhcpServerv4Scope -ScopeId {scope_id} -ErrorAction SilentlyContinue | ConvertTo-Json")
        if not output.strip():
            return None
        return {"scope_id": scope_id, "raw": output}

    def backup(self) -> str:
        return self._run_ps("Get-DhcpServerv4Scope | ConvertTo-Json -Depth 5")

    def deploy(self, operations: list[Operation]) -> DeployResult:
        try:
            outputs = [self._run_ps(op.rendered_config) for op in operations]
            return DeployResult(success=True, output="\n".join(outputs))
        except Exception as exc:  # pragma: no cover - requires a live/mock server
            return DeployResult(success=False, output="", error=str(exc))

    def verify(self, object_type: str, parameters: dict) -> VerifyResult:
        actual = self.get_current_state(object_type, parameters) or {}
        return VerifyResult(matches_expected=bool(actual), actual_state=actual)

    def rollback(self, backup_content: str) -> DeployResult:
        return DeployResult(success=False, output="", error="DHCP rollback requires manual restore from backup")
