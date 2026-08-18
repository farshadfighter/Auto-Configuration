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

_DYNAMIC_UPDATE_MAP = {"none": "None", "insecure": "NonsecureAndSecure", "secure": "Secure"}


class WindowsDNSDriver(Driver):
    manifest = DriverManifest(
        name="windows_dns",
        version="1.0.0",
        vendor="Microsoft",
        supported_os=["Windows Server"],
        capabilities={"dns_zone": True},
        rollback_strategy=RollbackStrategy.COMPENSATING_ACTION,
    )

    def __init__(self) -> None:
        self._session: Any = None

    def validate_intent(self, object_type: str, parameters: dict) -> list[ValidationIssue]:
        self._require_capability(object_type)
        issues: list[ValidationIssue] = []
        if not parameters.get("zone_name"):
            issues.append(ValidationIssue("ZONE_NAME_REQUIRED", "critical", "zone_name", "zone_name is required"))
        dynamic_update = parameters.get("dynamic_update", "secure")
        if dynamic_update not in _DYNAMIC_UPDATE_MAP:
            issues.append(
                ValidationIssue(
                    "INVALID_DYNAMIC_UPDATE", "high", "dynamic_update", "dynamic_update must be none/insecure/secure"
                )
            )
        return issues

    def generate_operations(
        self, object_type: str, change_type: ChangeType, parameters: dict, current_state: dict | None
    ) -> list[Operation]:
        self._require_capability(object_type)
        zone_name = parameters["zone_name"]
        if change_type == ChangeType.DELETE:
            return [Operation(1, "remove_dns_zone", f'Remove-DnsServerZone -Name "{zone_name}" -Force')]

        dynamic_update = _DYNAMIC_UPDATE_MAP[parameters.get("dynamic_update", "secure")]
        ops = []
        if not current_state:
            ops.append(
                Operation(
                    1,
                    "create_dns_zone",
                    f'Add-DnsServerPrimaryZone -Name "{zone_name}" -ReplicationScope "Domain" -DynamicUpdate {dynamic_update}',
                )
            )
        else:
            ops.append(
                Operation(
                    1,
                    "update_dns_zone",
                    f'Set-DnsServerPrimaryZone -Name "{zone_name}" -DynamicUpdate {dynamic_update}',
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
        zone_name = parameters["zone_name"]
        output = self._run_ps(
            f'Get-DnsServerZone -Name "{zone_name}" -ErrorAction SilentlyContinue | ConvertTo-Json'
        )
        if not output.strip():
            return None
        return {"zone_name": zone_name, "raw": output}

    def backup(self) -> str:
        return self._run_ps("Get-DnsServerZone | ConvertTo-Json -Depth 5")

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
        # DNS has no config-replace primitive; compensating action is out of scope for
        # automatic rollback and must be handled by a human via the Backup restore flow.
        return DeployResult(success=False, output="", error="DNS rollback requires manual restore from backup")
