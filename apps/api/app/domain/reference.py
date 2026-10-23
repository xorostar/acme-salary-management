"""Reference data: the countries ACME operates in, departments, levels, roles.

Kept in code rather than tables because they change rarely and the seed,
validation, and UI all need the same list.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    code: str
    name: str
    currency_code: str


COUNTRIES: dict[str, Country] = {
    c.code: c
    for c in (
        Country("US", "United States", "USD"),
        Country("GB", "United Kingdom", "GBP"),
        Country("DE", "Germany", "EUR"),
        Country("IN", "India", "INR"),
        Country("JP", "Japan", "JPY"),
        Country("CA", "Canada", "CAD"),
        Country("AU", "Australia", "AUD"),
        Country("SG", "Singapore", "SGD"),
        Country("BR", "Brazil", "BRL"),
    )
}

DEPARTMENTS: tuple[str, ...] = (
    "Engineering",
    "Product",
    "Design",
    "Sales",
    "Marketing",
    "Finance",
    "Human Resources",
    "Operations",
    "Customer Support",
    "Legal",
)

# Individual contributor levels L1-L6, managers M1-M3, directors D1-D2, VP.
LEVELS: tuple[str, ...] = ("L1", "L2", "L3", "L4", "L5", "L6", "M1", "M2", "M3", "D1", "D2", "VP")

ROLE_ADMIN = "hr_admin"
ROLE_VIEWER = "hr_viewer"
ROLES: tuple[str, ...] = (ROLE_ADMIN, ROLE_VIEWER)

SALARY_CHANGE_REASONS: tuple[str, ...] = (
    "Hire",
    "Annual review",
    "Promotion",
    "Market adjustment",
    "Correction",
    "Role change",
    "Other",
)
