"""Imports every domain's models so Base.metadata is fully populated for Alembic autogenerate."""

from app.domains.assets import models as _assets_models  # noqa: F401
from app.domains.audit import models as _audit_models  # noqa: F401
from app.domains.best_practice import models as _best_practice_models  # noqa: F401
from app.domains.configuration import models as _configuration_models  # noqa: F401
from app.domains.credentials import models as _credentials_models  # noqa: F401
from app.domains.design import models as _design_models  # noqa: F401
from app.domains.discovery import models as _discovery_models  # noqa: F401
from app.domains.identity import models as _identity_models  # noqa: F401
from app.domains.topology import models as _topology_models  # noqa: F401
