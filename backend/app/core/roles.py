"""Role names (rows of dcp.roles)."""

SYSTEM_ADMIN = "System Administrator"  # platform owners: all companies + dealer uploads
COMPANY_ADMIN = "Company Administrator"  # manages the users of their own company

# Roles a Company Administrator may give to the users of their company.
COMPANY_ROLES = ("Company Administrator", "Sales Manager", "Sales Representative", "Viewer")
