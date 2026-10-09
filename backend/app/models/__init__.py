"""SQLAlchemy models mirroring database/02_schema.sql (the SQL script is the source of truth)."""

from app.models.base import AuditMixin, Base
from app.models.communication import Communication, CommunicationAttachment
from app.models.company import Company, PasswordResetToken, User, UserSession, UserSettings
from app.models.dealer import Dealer, DealerProduct, DealerSource, Product, ProductSubSector
from app.models.lookups import (
    CommunicationStatus,
    CommunicationType,
    Country,
    Currency,
    DealerStatus,
    DealerType,
    Region,
    Role,
    Sector,
    SubSector,
)
from app.models.sales import (
    ExchangeRate,
    SalesRecord,
    SalesUpload,
    SalesUploadColumn,
    SalesUploadIssue,
    SalesUploadRow,
)

__all__ = [
    "AuditMixin",
    "Base",
    "Communication",
    "CommunicationAttachment",
    "CommunicationStatus",
    "CommunicationType",
    "Company",
    "Country",
    "Currency",
    "Dealer",
    "DealerProduct",
    "DealerSource",
    "DealerStatus",
    "DealerType",
    "ExchangeRate",
    "PasswordResetToken",
    "Product",
    "ProductSubSector",
    "Region",
    "Role",
    "SalesRecord",
    "SalesUpload",
    "SalesUploadColumn",
    "SalesUploadIssue",
    "SalesUploadRow",
    "Sector",
    "SubSector",
    "User",
    "UserSession",
    "UserSettings",
]
