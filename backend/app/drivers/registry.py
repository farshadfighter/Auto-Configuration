from app.core.errors import NotFoundError
from app.drivers.base import Driver

_REGISTRY: dict[str, type[Driver]] = {}


def register_driver(technology: str, driver_cls: type[Driver]) -> None:
    _REGISTRY[technology] = driver_cls


def get_driver(technology: str) -> Driver:
    driver_cls = _REGISTRY.get(technology)
    if not driver_cls:
        raise NotFoundError("DRIVER_NOT_FOUND", f"No driver registered for technology '{technology}'")
    return driver_cls()


def list_technologies() -> list[str]:
    return sorted(_REGISTRY.keys())


def _bootstrap() -> None:
    """Imports every driver module so it self-registers. Called once at app/worker startup."""
    from app.drivers.cisco_iosxe.driver import CiscoIOSXEDriver
    from app.drivers.fortios.driver import FortiOSDriver
    from app.drivers.windows_dhcp.driver import WindowsDHCPDriver
    from app.drivers.windows_dns.driver import WindowsDNSDriver

    register_driver("cisco_iosxe", CiscoIOSXEDriver)
    register_driver("fortios", FortiOSDriver)
    register_driver("windows_dns", WindowsDNSDriver)
    register_driver("windows_dhcp", WindowsDHCPDriver)


_bootstrap()
